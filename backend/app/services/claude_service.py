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

# Cached at the API level via cache_control: ephemeral.
# Token count must stay above 1024 for caching to activate.
SYSTEM_PROMPT = """You are an expert investment analyst at a venture capital firm. Your job is to analyze raw data about portfolio companies and extract meaningful business intelligence signals.

When analyzing data, focus on:
1. **New Hires** (hire): Notable people joining the company — especially senior hires (C-suite, VP, Directors), technical leads, or domain experts that signal growth or strategic shifts.
2. **Departures** (departure): Key people leaving — especially co-founders, C-suite, or long-tenured employees that could indicate instability or pivots.
3. **Founder Posts** (founder_post): Significant LinkedIn posts, tweets, or public statements from founders/executives about company direction, milestones, or challenges.
4. **Press Mentions** (press): Coverage in notable publications, analyst reports, or industry newsletters.
5. **Funding** (funding): Any funding-related news — rounds closed, investor announcements, valuations, debt facilities.
6. **Product Launches** (product): New product launches, major feature releases, or market expansions.
7. **Other** (other): Any other notable signal worth flagging to the investment team.

Importance levels:
- **high**: C-suite changes, funding rounds, major pivots, or events that materially affect the investment thesis
- **medium**: Director/VP hires, notable partnerships, product launches, press in tier-1 outlets
- **low**: Individual contributor hires, minor updates, general company news

Confidence score (0.0–1.0): How certain are you that this signal is real and material?
- 0.9+: Directly stated in the data with specific names/dates
- 0.7–0.9: Strongly implied with corroborating evidence
- 0.5–0.7: Inferred from indirect signals
- Below 0.5: Speculative — only include if clearly notable

Always return valid JSON. If no signals are found, return an empty array [].
Never include commentary outside the JSON."""


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
        user_content = f"""Analyze the following data for **{company_name}** and extract all notable signals.

Company: {company_name}{context_line}

Raw Data (Apollo.io enrichment):
```json
{json.dumps(raw_data, indent=2, default=str)[:8000]}
```

Return a JSON array. Each element must have exactly these fields:
- "type": one of [hire, departure, founder_post, press, funding, product, other]
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
    "detail": "Sarah Chen, formerly VP Engineering at Stripe (200-person org), joins to lead technical infrastructure. Deep payments expertise aligns with the company's enterprise roadmap.",
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
        import anthropic
        from calendar import month_name as _month_name
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
