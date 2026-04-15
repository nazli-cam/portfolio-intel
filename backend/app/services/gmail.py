"""
Gmail API integration for sending signal alerts and monthly reports.
Uses OAuth2 with a stored refresh token (no user consent flow at runtime).

Setup:
1. Go to https://console.cloud.google.com/
2. Create OAuth2 credentials (Desktop application type)
3. Enable Gmail API
4. Run the setup script to get refresh token: python scripts/gmail_setup.py
5. Set GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN in .env
"""
import base64
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from ..config import settings

logger = logging.getLogger(__name__)


def _build_gmail_service():
    """Build Gmail API service using stored OAuth2 credentials."""
    if not all([settings.GMAIL_CLIENT_ID, settings.GMAIL_CLIENT_SECRET, settings.GMAIL_REFRESH_TOKEN]):
        logger.warning("Gmail credentials not fully configured")
        return None

    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials(
            token=None,
            refresh_token=settings.GMAIL_REFRESH_TOKEN,
            client_id=settings.GMAIL_CLIENT_ID,
            client_secret=settings.GMAIL_CLIENT_SECRET,
            token_uri="https://oauth2.googleapis.com/token",
            scopes=["https://www.googleapis.com/auth/gmail.send"],
        )
        return build("gmail", "v1", credentials=creds)
    except Exception as e:
        logger.error(f"Failed to build Gmail service: {e}")
        return None


def _create_message(
    sender: str,
    recipients: list[str],
    subject: str,
    html_body: str,
) -> dict:
    """Create a Gmail API message dict."""
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message.attach(MIMEText(html_body, "html"))

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {"raw": raw}


def _send_message(service, message: dict) -> bool:
    try:
        service.users().messages().send(userId="me", body=message).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to send Gmail message: {e}")
        return False


async def send_signal_alert(signals: list[dict], company_name: str) -> bool:
    """Send an email alert for new signals detected for a company."""
    if not settings.alert_recipients_list:
        logger.info("No alert recipients configured — skipping email")
        return False

    service = _build_gmail_service()
    if not service:
        logger.warning("Gmail service unavailable — skipping signal alert")
        return False

    signal_rows = ""
    for s in signals:
        importance_color = {"high": "#dc2626", "medium": "#d97706", "low": "#6b7280"}.get(
            s.get("importance", "medium"), "#6b7280"
        )
        signal_rows += f"""
        <tr>
          <td style="padding:8px;border-bottom:1px solid #e5e7eb;">
            <span style="color:{importance_color};font-weight:600;text-transform:uppercase;font-size:11px;">
              {s.get("importance","medium")}
            </span>
          </td>
          <td style="padding:8px;border-bottom:1px solid #e5e7eb;">
            <strong>{s.get("signal_type","").replace("_"," ").title()}</strong>
          </td>
          <td style="padding:8px;border-bottom:1px solid #e5e7eb;">{s.get("title","")}</td>
          <td style="padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-size:13px;">{s.get("description","")}</td>
        </tr>"""

    html_body = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f9fafb;margin:0;padding:20px;">
  <div style="max-width:700px;margin:0 auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1);">
    <div style="background:#1e3a5f;padding:24px 32px;">
      <h1 style="color:#fff;margin:0;font-size:20px;">Portfolio Intelligence Alert</h1>
      <p style="color:#93c5fd;margin:4px 0 0;font-size:14px;">{len(signals)} new signal{"s" if len(signals) > 1 else ""} detected</p>
    </div>
    <div style="padding:24px 32px;">
      <h2 style="margin:0 0 16px;font-size:16px;color:#111827;">{company_name}</h2>
      <table style="width:100%;border-collapse:collapse;font-size:14px;">
        <thead>
          <tr style="background:#f3f4f6;">
            <th style="padding:8px;text-align:left;font-size:12px;color:#6b7280;font-weight:600;">PRIORITY</th>
            <th style="padding:8px;text-align:left;font-size:12px;color:#6b7280;font-weight:600;">TYPE</th>
            <th style="padding:8px;text-align:left;font-size:12px;color:#6b7280;font-weight:600;">SIGNAL</th>
            <th style="padding:8px;text-align:left;font-size:12px;color:#6b7280;font-weight:600;">DETAILS</th>
          </tr>
        </thead>
        <tbody>{signal_rows}</tbody>
      </table>
    </div>
    <div style="padding:16px 32px;background:#f9fafb;border-top:1px solid #e5e7eb;">
      <p style="margin:0;font-size:12px;color:#9ca3af;">
        Portfolio Intelligence Platform — <a href="#" style="color:#3b82f6;">View all signals</a>
      </p>
    </div>
  </div>
</body>
</html>"""

    message = _create_message(
        sender=settings.GMAIL_SENDER_EMAIL,
        recipients=settings.alert_recipients_list,
        subject=f"[Portfolio Alert] {len(signals)} new signal{'s' if len(signals)>1 else ''} — {company_name}",
        html_body=html_body,
    )
    return _send_message(service, message)


async def send_monthly_report(
    report_html: str,
    month_name: str,
    year: int,
    signal_count: int,
) -> bool:
    """Send the monthly portfolio intelligence report via email."""
    if not settings.alert_recipients_list:
        logger.info("No alert recipients configured — skipping report email")
        return False

    service = _build_gmail_service()
    if not service:
        logger.warning("Gmail service unavailable — skipping report email")
        return False

    html_body = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f9fafb;margin:0;padding:20px;">
  <div style="max-width:800px;margin:0 auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1);">
    <div style="background:#1e3a5f;padding:24px 32px;">
      <h1 style="color:#fff;margin:0;font-size:22px;">Monthly Portfolio Intelligence Report</h1>
      <p style="color:#93c5fd;margin:6px 0 0;font-size:15px;">{month_name} {year} — {signal_count} signals detected</p>
    </div>
    <div style="padding:32px;">
      {report_html}
    </div>
    <div style="padding:16px 32px;background:#f9fafb;border-top:1px solid #e5e7eb;">
      <p style="margin:0;font-size:12px;color:#9ca3af;">Portfolio Intelligence Platform — Automated Monthly Report</p>
    </div>
  </div>
</body>
</html>"""

    message = _create_message(
        sender=settings.GMAIL_SENDER_EMAIL,
        recipients=settings.alert_recipients_list,
        subject=f"[Portfolio Report] {month_name} {year} Intelligence Summary",
        html_body=html_body,
    )
    return _send_message(service, message)
