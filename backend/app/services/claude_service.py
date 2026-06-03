"""
Claude API integration for signal extraction from company data.
Uses prompt caching on the system prompt to reduce cost on repeated calls.
"""
import json
import logging
import re
from typing import Optional

from ..config import settings

logger = logging.getLogger(__name__)

# Prompt caching requires ≥1,024 tokens on the cached block.
# English prose runs ~3.5–4 chars/token, so this prompt must be ≥4,096 chars.
# Current length is verified in tests; do not shorten without re-checking.
SYSTEM_PROMPT = """You are an expert investment analyst at a venture capital firm. Your job is to analyze raw enrichment data about portfolio companies and extract meaningful business intelligence signals that matter to the investment team.  # noqa: E501

## Signal Types

### hire
A notable person joining the company. Prioritise:
- C-suite appointments (CEO, CTO, CFO, COO, CPO, CRO, CLO, CMO)
- VP and Director-level hires, especially in engineering, product, sales, or finance
- Domain experts whose background directly strengthens the investment thesis
- Hires from well-known companies (FAANG, top-tier startups, competitor firms)

Indicators in data: employment_history entries where current=true and the start date is recent, LinkedIn headline changes, press releases announcing appointments.  # noqa: E501

### departure
A key person leaving the company. Prioritise:
- Co-founder exits or transitions to advisor/board roles
- C-suite departures, especially unplanned or with no named successor
- Long-tenured (3+ year) senior employees leaving
- Multiple senior departures within a short window (potential talent exodus signal)

Indicators: employment_history entries where a current=false entry was previously current, LinkedIn "former" language, absence from leadership page.  # noqa: E501

### founder_post
A significant public statement by a founder or C-suite executive. Prioritise:
- Product vision or strategic pivot announcements
- Fundraising hints or closing announcements
- Public commentary on market conditions affecting the company
- Milestone achievements (revenue, customers, product GA)

Not worth flagging: generic motivational posts, conference speaking announcements, holiday messages.

### press
Coverage in publications that reaches the company's target customers or investors. Prioritise:
- Tier-1 outlets: TechCrunch, The Information, Bloomberg, WSJ, Forbes, FT, Reuters
- Vertical trade press relevant to the company's sector
- Analyst reports (Gartner, Forrester, IDC)

Not worth flagging: syndicated press releases, low-DA blogs, awards lists without editorial coverage.

### funding
Any capital event. Includes:
- Equity rounds (seed, Series A–F, growth, pre-IPO)
- Debt facilities, revenue-based financing, venture debt
- Strategic investments from corporates
- Secondary transactions that reveal valuation

Always capture: round size, lead investor, total raised to date if mentioned, post-money valuation if disclosed.

### product
A material product or go-to-market event. Includes:
- General availability launch of a new product line
- Major version releases with significant new capability
- Entry into a new geographic market or vertical
- Platform partnerships that expand distribution
- API launches that enable ecosystem development

Not worth flagging: minor bug fixes, incremental feature updates, UI refreshes.

### exit
Signals that a portfolio company may be approaching a liquidity event. Prioritise:
- M&A rumours or acquisition announcements (company as target or acquirer)
- IPO filings (S-1, F-1), IPO rumours, or public market preparation activity
- Secondary market transactions indicating investor exit activity or valuation signals
- Acquihire signals: talent acquisition framed as a product acquisition
- Strategic buyer interest: inbound from a named corporate

Always flag exit signals as **high** importance regardless of confidence level.

### other
Catch-all for signals that don't fit above categories but are clearly material:
- Regulatory approvals or investigations
- Key customer wins or losses (named accounts)
- Leadership team reorganisations
- Office openings or closures that signal growth/contraction

## Importance Calibration

**high** — Partner should be aware before the next weekly meeting. Examples: funding round, co-founder departure, acquisition announcement, C-suite hire from a tier-1 company, product entering a major new market.  # noqa: E501

**medium** — Worth including in the weekly digest. Examples: VP-level hire or departure, tier-1 press mention, product GA launch, strategic partnership with a named Fortune 500 company.  # noqa: E501

**low** — Background signal, good to track over time. Examples: individual contributor hires, minor product updates, general industry mentions, conference appearances.  # noqa: E501

## Confidence Scoring

Score 0.0–1.0 based on evidence quality in the provided data:
- **0.90–1.00**: Directly and explicitly stated with specific names, dates, amounts. Multiple corroborating data points.
- **0.70–0.89**: Clearly implied with at least one concrete data point (e.g., employment record shows new role, LinkedIn bio updated).  # noqa: E501
- **0.50–0.69**: Inferred from indirect signals. Include only if the signal would be high or medium importance.
- **Below 0.50**: Speculative. Omit unless no higher-confidence signals exist and the potential importance is high.

## Output Rules

1. Return ONLY a valid JSON array. No markdown, no commentary, no code fences.
2. If no signals meet the threshold, return an empty array: []
3. Each element must have exactly these seven fields: type, headline, detail, source, confidence, person_name, importance  # noqa: E501
4. headline: max 120 characters, present tense, factual (not sensationalised)
5. detail: 1–2 sentences, max 400 characters, include specific names/titles/numbers where available
6. source: URL string if present in the data, otherwise null (never fabricate URLs)
7. person_name: full name of the most relevant individual, or null if not applicable
8. Do not hallucinate data that is not present in the input. If uncertain, lower the confidence score rather than inventing detail."""  # noqa: E501


def _parse_json_array(text: str) -> list:
    """Extract a JSON array from Claude's response, tolerating markdown fences."""
    text = text.strip()
    # Strip ```json ... ``` or ``` ... ``` fences
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()
    # If response starts with an object instead of array, wrap it
    if text.startswith("{"):
        text = f"[{text}]"
    return json.loads(text)


async def extract_signals(
    company_name: str,
    raw_data: dict,
    context: Optional[str] = None,
    key_people: Optional[list[str]] = None,
) -> list[dict]:
    """
    Use Claude to extract signals from raw Apollo enrichment data.

    Returns a list of signal dicts with keys:
      type, headline, detail, source, confidence, person_name, importance
    """
    if not settings.ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY not configured — skipping signal extraction")
        return []

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        context_line = f"\nContext: {context}" if context else ""
        if key_people:
            def _fmt(p: object) -> str:
                if isinstance(p, dict):
                    return f"{p['name']} ({p['title']})" if p.get('title') else p['name']
                return str(p)
            people_str = ", ".join(_fmt(p) for p in key_people)
            people_line = f"\nKey people at this company: {people_str}"
        else:
            people_line = ""
        user_content = f"""Analyze the following data for **{company_name}** and extract all notable signals.

Company: {company_name}{context_line}{people_line}

Raw Data (Apollo.io enrichment):
```json
{json.dumps(raw_data, indent=2, default=str)[:8000]}
```

Return a JSON array. Each element must have exactly these fields:
- "type": one of [hire, departure, founder_post, press, funding, product, exit, other]
- "headline": concise title, max 120 chars
- "detail": 1–2 sentence description with specific names, titles, and context (max 400 chars)
- "source": URL string if available, otherwise null
- "confidence": float 0.0–1.0
- "person_name": full name of the relevant person if applicable, otherwise null
- "importance": one of [low, medium, high]

Example output:
[
  {{
    "type": "hire",
    "headline": "Sarah Chen joins as VP Engineering",
    "detail": "Sarah Chen, formerly VP Engineering at Stripe (200-person org), joins to lead technical"
    " infrastructure. Deep payments expertise aligns with the company's enterprise roadmap.",
    "source": "https://linkedin.com/in/sarahchen",
    "confidence": 0.92,
    "person_name": "Sarah Chen",
    "importance": "high"
  }}
]

Return ONLY the JSON array with no surrounding text."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_content}],
        )

        raw_text = response.content[0].text
        signals = _parse_json_array(raw_text)

        if not isinstance(signals, list):
            logger.error(f"Claude returned non-list for {company_name}: {type(signals)}")
            return []

        # Normalise: keep only expected keys, clamp confidence
        cleaned = []
        for s in signals:
            if not isinstance(s, dict):
                continue
            cleaned.append({
                "type": str(s.get("type", "other")),
                "headline": str(s.get("headline", ""))[:120],
                "detail": str(s.get("detail", ""))[:400],
                "source": s.get("source") or None,
                "confidence": max(0.0, min(1.0, float(s.get("confidence", 0.7)))),
                "person_name": s.get("person_name") or None,
                "importance": str(s.get("importance", "medium")),
            })

        logger.info(f"Claude extracted {len(cleaned)} signals for {company_name}")
        return cleaned

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Claude JSON for {company_name}: {e}")
        return []
    except Exception as e:
        logger.error(f"Claude API error for {company_name}: {e}", exc_info=True)
        return []


async def generate_monthly_summary(
    month: int,
    year: int,
    signals_data: list[dict],
    companies: list[dict],
) -> str:
    """Generate an HTML executive summary for the monthly report."""
    if not settings.ANTHROPIC_API_KEY:
        return "<p><em>Claude API not configured (ANTHROPIC_API_KEY missing).</em></p>"

    try:
        from calendar import month_name as _month_name

        import anthropic
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        month_str = f"{_month_name[month]} {year}"
        company_list = ", ".join(c["name"] for c in companies)
        signal_json = json.dumps(signals_data[:120], indent=2, default=str)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": f"""Write an executive intelligence summary for {month_str}.

Portfolio companies: {company_list}

Signals this month:
{signal_json}

Write a professional HTML summary with these sections:
1. Executive Summary — 3–4 sentence overview of the month's key themes
2. High-Priority Items — bullet list of signals requiring partner attention
3. Hiring Trends — patterns in senior hires across the portfolio
4. Recommended Actions — 2–3 specific follow-up items for the team

Format as clean HTML fragments (no <html>/<body> tags). Use inline CSS only.
Professional aesthetic: dark headings (#0f172a), clean paragraphs, styled bullet lists.
Return ONLY the HTML, no markdown, no code fences.""",
                }
            ],
        )

        return response.content[0].text.strip()

    except Exception as e:
        logger.error(f"Claude monthly summary error: {e}", exc_info=True)
        return f"<p><em>Error generating summary: {e}</em></p>"
