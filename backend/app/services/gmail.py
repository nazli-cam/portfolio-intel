"""
Gmail SMTP service for signal alerts and monthly reports.
Uses smtplib with SSL on port 465 and a Gmail App Password.

Setup:
1. Enable 2-Step Verification on the Gmail account.
2. Go to Google Account → Security → App Passwords.
3. Generate a password for "Mail" → copy the 16-char string.
4. Set GMAIL_USER and GMAIL_APP_PASSWORD in .env.
"""
import logging
import smtplib
import ssl
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..config import settings

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


def _smtp_configured() -> bool:
    return bool(settings.GMAIL_USER and settings.GMAIL_APP_PASSWORD)


def _send(subject: str, html_body: str, recipients: list[str]) -> bool:
    """Send a single HTML email via Gmail SMTP SSL (port 465)."""
    if not recipients:
        logger.info("No alert recipients configured — skipping email")
        return False
    if not _smtp_configured():
        logger.warning("GMAIL_USER / GMAIL_APP_PASSWORD not set — skipping email send")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.GMAIL_USER
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
            smtp.login(settings.GMAIL_USER, settings.GMAIL_APP_PASSWORD.replace(" ", ""))
            smtp.sendmail(settings.GMAIL_USER, recipients, msg.as_string())
        logger.info(f"Email sent to {recipients}: {subject}")
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("Gmail SMTP authentication failed — check GMAIL_USER and GMAIL_APP_PASSWORD")
    except Exception as e:
        logger.error(f"Gmail SMTP error: {e}")
    return False


async def send_daily_digest(company_signals: dict[str, list[dict]]) -> bool:
    """
    Send a single digest email after the daily job, grouped by company.
    `company_signals`: {company_name: [signal dicts]} — only medium/high signals.
    Skips send if the dict is empty.
    """
    if not company_signals:
        logger.info("No signals for digest — skipping email")
        return False

    recipients = settings.alert_recipients_list
    if not recipients:
        logger.info("No alert recipients — skipping digest")
        return False

    total = sum(len(v) for v in company_signals.values())
    template = _jinja_env.get_template("daily_digest.html")
    html_body = template.render(
        company_signals=company_signals,
        total_signals=total,
        company_count=len(company_signals),
        run_date=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )

    subject = (
        f"[Portfolio Digest] {total} new signal{'s' if total != 1 else ''} "
        f"across {len(company_signals)} compan{'ies' if len(company_signals) != 1 else 'y'} "
        f"— {datetime.now(timezone.utc).strftime('%b %d')}"
    )
    return _send(subject, html_body, recipients)


async def send_signal_alert(signals: list[dict], company_name: str) -> bool:
    """
    Send a per-company signal alert (used by manual /refresh endpoint, not the daily job).
    The daily job uses send_daily_digest instead.
    """
    if not signals:
        return False

    recipients = settings.alert_recipients_list
    if not recipients:
        logger.info("No alert recipients — skipping signal alert")
        return False

    template = _jinja_env.get_template("signal_alert.html")
    html_body = template.render(
        company_name=company_name,
        signal_count=len(signals),
        signals=signals,
        run_date=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )

    subject = (
        f"[Portfolio Alert] {len(signals)} new signal"
        f"{'s' if len(signals) != 1 else ''} — {company_name}"
    )
    return _send(subject, html_body, recipients)


async def send_monthly_report(
    claude_html: str,
    month_name: str,
    year: int,
    total_signals: int,
    high_count: int,
    medium_count: int,
    company_count: int,
    company_signals: dict,  # {company_name: [signal dicts]}
) -> bool:
    """Send the monthly portfolio intelligence report as an HTML digest."""
    recipients = settings.alert_recipients_list
    if not recipients:
        logger.info("No alert recipients — skipping report email")
        return False

    template = _jinja_env.get_template("monthly_report.html")
    html_body = template.render(
        month_name=month_name,
        year=year,
        total_signals=total_signals,
        high_count=high_count,
        medium_count=medium_count,
        company_count=company_count,
        company_signals=company_signals,
        claude_html=claude_html,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )

    subject = f"[Portfolio Report] {month_name} {year} Intelligence Summary"
    return _send(subject, html_body, recipients)
