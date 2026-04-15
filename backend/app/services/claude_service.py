"""
Claude API integration for signal extraction from company data.
Uses prompt caching for the system prompt to reduce costs on repeated calls.
"""
import json
import logging
from typing import Optional
from ..config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert investment analyst at a venture capital firm. Your job is to analyze raw data about portfolio companies and extract meaningful business intelligence signals.

When analyzing data, focus on:
1. **New Hires** (new_hire): Notable people joining the company — especially senior hires (C-suite, VP, Directors), technical leads, or domain experts that signal growth or strategic shifts.
2. **Departures** (departure): Key people leaving — especially co-founders, C-suite, or long-tenured employees that could indicate instability or pivots.
3. **Founder Posts** (founder_post): Significant LinkedIn posts, tweets, or public statements from founders/executives about company direction, milestones, or challenges.
4. **Funding** (funding): Any funding-related news — rounds closed, investor announcements, valuations.
5. **Partnerships** (partnership): New strategic partnerships, enterprise deals, or integrations.
6. **Product Launches** (product_launch): New product launches, major feature releases, or market expansions.
7. **Other** (other): Any other notable signal worth flagging to the investment team.

Importance levels:
- **high**: C-suite changes, funding rounds, major product pivots, or events that materially affect the investment thesis
- **medium**: Director/VP hires, notable partnerships, product launches
- **low**: Individual contributor hires, minor updates, general company news

Always return valid JSON. If no signals are found, return an empty array."""


async def extract_signals(
    company_name: str,
    raw_data: dict,
    context: Optional[str] = None,
) -> list[dict]:
    """
    Use Claude to extract signals from raw company data.

    Args:
        company_name: Name of the portfolio company
        raw_data: Raw data dict (from Apollo, LinkedIn scrape, etc.)
        context: Optional additional context about the company

    Returns:
        List of signal dicts with keys: type, title, description, source_url, importance
    """
    if not settings.ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY not configured — skipping signal extraction")
        return []

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        user_content = f"""Analyze the following data for **{company_name}** and extract all notable signals.

Company: {company_name}
{f"Context: {context}" if context else ""}

Raw Data:
```json
{json.dumps(raw_data, indent=2, default=str)[:8000]}
```

Return a JSON array of signals. Each signal must have these fields:
- type: one of [new_hire, departure, founder_post, funding, partnership, product_launch, other]
- title: concise title (max 120 characters)
- description: detailed description with specific names, titles, and context (max 500 characters)
- source_url: URL if available, otherwise null
- importance: one of [low, medium, high]

Example:
[
  {{
    "type": "new_hire",
    "title": "Sarah Chen joins as VP of Engineering",
    "description": "Sarah Chen, formerly VP Engineering at Stripe, joins as VP of Engineering. She previously led a 200-person engineering org and has deep payments infrastructure expertise.",
    "source_url": "https://linkedin.com/in/sarahchen",
    "importance": "high"
  }}
]

Return ONLY the JSON array, no other text."""

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},  # prompt caching
                }
            ],
            messages=[{"role": "user", "content": user_content}],
        )

        content = response.content[0].text.strip()

        # Strip markdown code fences if present
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        signals = json.loads(content)
        if not isinstance(signals, list):
            logger.error(f"Claude returned non-list response for {company_name}")
            return []

        return signals

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Claude JSON response for {company_name}: {e}")
        return []
    except Exception as e:
        logger.error(f"Claude API error for {company_name}: {e}")
        return []


async def generate_monthly_summary(
    month: int,
    year: int,
    signals_data: list[dict],
    companies: list[dict],
) -> str:
    """Generate a monthly portfolio intelligence summary using Claude."""
    if not settings.ANTHROPIC_API_KEY:
        return "<p>Claude API not configured. Please set ANTHROPIC_API_KEY.</p>"

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        from calendar import month_name
        month_str = f"{month_name[month]} {year}"

        signal_summary = json.dumps(signals_data[:100], indent=2, default=str)
        company_list = ", ".join(c["name"] for c in companies)

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4000,
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
                    "content": f"""Generate a professional monthly portfolio intelligence report for {month_str}.

Portfolio Companies: {company_list}

Signals Detected This Month:
{signal_summary}

Write a comprehensive HTML report with:
1. Executive Summary (key themes and highlights)
2. High-Priority Signals (requires partner attention)
3. Company-by-Company Summary
4. Hiring Trends Analysis
5. Recommended Actions

Format as clean HTML with inline CSS using a professional VC firm aesthetic (dark header, clean typography, data tables). Use Bootstrap-like classes for styling. Make it email-friendly.

Return ONLY the HTML content starting with a <div> tag.""",
                }
            ],
        )

        return response.content[0].text.strip()

    except Exception as e:
        logger.error(f"Claude report generation error: {e}")
        return f"<p>Error generating report: {e}</p>"
