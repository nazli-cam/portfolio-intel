"""Monthly report generation service."""
import calendar
import logging
from calendar import month_name
from datetime import datetime, timezone

from sqlalchemy.orm import Session, joinedload

from ..models.company import Company
from ..models.report import Report
from ..models.signal import Signal, SignalImportance
from ..services.claude_service import generate_monthly_summary

logger = logging.getLogger(__name__)


async def generate_monthly_report(month: int, year: int, db: Session) -> Report:
    """Aggregate signals for the given month/year, run Claude summary, save and email."""
    _, days_in_month = calendar.monthrange(year, month)
    start_dt = datetime(year, month, 1, tzinfo=timezone.utc)
    end_dt = datetime(year, month, days_in_month, 23, 59, 59, tzinfo=timezone.utc)

    signals = (
        db.query(Signal)
        .options(joinedload(Signal.company))
        .filter(Signal.created_at >= start_dt, Signal.created_at <= end_dt)
        .order_by(Signal.company_id, Signal.importance.desc())
        .all()
    )

    companies = db.query(Company).filter(Company.is_active == True).all()
    company_map = {c.id: c for c in companies}

    # Group signals by company name for the email template
    company_signals_by_name: dict[str, list] = {}
    for s in signals:
        cname = company_map.get(s.company_id, Company(name="Unknown")).name
        company_signals_by_name.setdefault(cname, []).append({
            "title": s.title,
            "signal_type": s.signal_type.value,
            "importance": s.importance.value,
            "person_name": s.person_name,
        })

    active_companies = [c for c in companies if c.id in {s.company_id for s in signals}]

    high_count = sum(1 for s in signals if s.importance == SignalImportance.HIGH)
    med_count = sum(1 for s in signals if s.importance == SignalImportance.MEDIUM)
    low_count = sum(1 for s in signals if s.importance == SignalImportance.LOW)

    # Prepare compact data for Claude (cap at 120 signals to stay within token budget)
    signals_data = [
        {
            "company": company_map.get(s.company_id, Company(name="Unknown")).name,
            "type": s.signal_type.value,
            "importance": s.importance.value,
            "headline": s.title,
            "detail": s.description,
            "person_name": s.person_name,
        }
        for s in signals[:120]
    ]
    companies_data = [{"name": c.name, "industry": c.industry} for c in companies]

    claude_html = await generate_monthly_summary(month, year, signals_data, companies_data)

    summary = (
        f"{len(signals)} signals across {len(active_companies)} companies. "
        f"High: {high_count}, Medium: {med_count}, Low: {low_count}."
    )

    report = Report(
        title=f"Portfolio Intelligence Report — {month_name[month]} {year}",
        month=month,
        year=year,
        html_content=claude_html,
        summary=summary,
        signal_count=len(signals),
        company_count=len(active_companies),
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    # Email digest — fire and forget (failure doesn't break report generation)
    try:
        from ..services.gmail import send_monthly_report
        await send_monthly_report(
            claude_html=claude_html,
            month_name=month_name[month],
            year=year,
            total_signals=len(signals),
            high_count=high_count,
            medium_count=med_count,
            company_count=len(active_companies),
            company_signals=company_signals_by_name,
        )
    except Exception as e:
        logger.error(f"Failed to email monthly report: {e}")

    logger.info(f"Monthly report generated: {report.title}")
    return report
