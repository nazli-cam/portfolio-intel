"""Monthly report generation service."""
import logging
from calendar import month_name
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..models.company import Company
from ..models.report import Report
from ..models.signal import Signal, SignalImportance, SignalType
from ..services.claude_service import generate_monthly_summary

logger = logging.getLogger(__name__)


async def generate_monthly_report(month: int, year: int, db: Session) -> Report:
    """Generate a monthly intelligence report for the given month/year."""
    # Gather signals for the month
    from datetime import date
    import calendar

    _, days_in_month = calendar.monthrange(year, month)
    start_dt = datetime(year, month, 1, tzinfo=timezone.utc)
    end_dt = datetime(year, month, days_in_month, 23, 59, 59, tzinfo=timezone.utc)

    signals = (
        db.query(Signal)
        .filter(Signal.created_at >= start_dt, Signal.created_at <= end_dt)
        .order_by(Signal.company_id, Signal.importance.desc())
        .all()
    )

    companies = db.query(Company).filter(Company.is_active == True).all()
    company_map = {c.id: c for c in companies}

    # Build signal summary grouped by company
    company_signals: dict[int, list] = {}
    for s in signals:
        company_signals.setdefault(s.company_id, []).append(s)

    active_companies = [c for c in companies if c.id in company_signals]

    # Prepare data for Claude
    signals_data = [
        {
            "company": company_map.get(s.company_id, Company(name="Unknown")).name,
            "type": s.signal_type.value,
            "importance": s.importance.value,
            "title": s.title,
            "description": s.description,
        }
        for s in signals
    ]
    companies_data = [{"name": c.name, "industry": c.industry} for c in companies]

    # Generate HTML summary via Claude
    html_content = await generate_monthly_summary(month, year, signals_data, companies_data)

    # Count breakdown
    high_count = sum(1 for s in signals if s.importance == SignalImportance.HIGH)
    med_count = sum(1 for s in signals if s.importance == SignalImportance.MEDIUM)
    low_count = sum(1 for s in signals if s.importance == SignalImportance.LOW)

    summary = (
        f"{len(signals)} signals across {len(active_companies)} companies. "
        f"High: {high_count}, Medium: {med_count}, Low: {low_count}."
    )

    report = Report(
        title=f"Portfolio Intelligence Report — {month_name[month]} {year}",
        month=month,
        year=year,
        html_content=html_content,
        summary=summary,
        signal_count=len(signals),
        company_count=len(active_companies),
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    # Email the report
    from ..services.gmail import send_monthly_report
    await send_monthly_report(html_content, month_name[month], year, len(signals))

    logger.info(f"Monthly report generated: {report.title}")
    return report
