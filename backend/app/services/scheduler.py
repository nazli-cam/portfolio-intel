"""
APScheduler-based daily intelligence gathering job.

Runs every day at the configured time (default 8:00 AM).
For each active portfolio company:
1. Fetches data from Apollo.io
2. Sends to Claude for signal extraction
3. Saves new signals to the database
4. Sends Gmail alerts for high/medium importance signals
"""
import json
import logging
from datetime import datetime, timezone
from urllib.parse import urlparse
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ..config import settings
from ..database import SessionLocal

logger = logging.getLogger(__name__)

_scheduler: Optional[AsyncIOScheduler] = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


def _extract_domain(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    try:
        parsed = urlparse(url if url.startswith("http") else f"https://{url}")
        return parsed.netloc.lstrip("www.")
    except Exception:
        return None


async def process_single_company(company_id: int) -> None:
    """Process a single company: fetch data, extract signals, save, alert."""
    from ..models.company import Company
    from ..models.signal import Signal, SignalType, SignalImportance
    from ..services.apollo import search_people_at_company, enrich_organization
    from ..services.claude_service import extract_signals
    from ..services.gmail import send_signal_alert

    db = SessionLocal()
    try:
        company = db.query(Company).filter(Company.id == company_id, Company.is_active == True).first()
        if not company:
            logger.warning(f"Company {company_id} not found or inactive")
            return

        logger.info(f"Processing company: {company.name}")
        domain = _extract_domain(company.website)

        # Gather data from Apollo
        raw_data: dict = {"company_name": company.name, "people": [], "organization": {}}

        org_data = await enrich_organization(domain) if domain else None
        if org_data:
            raw_data["organization"] = org_data
            # Update employee count from Apollo
            if org_data.get("estimated_num_employees"):
                company.employee_count = org_data["estimated_num_employees"]
            if org_data.get("id"):
                company.apollo_org_id = org_data["id"]

        people_data = await search_people_at_company(company.name, domain)
        if people_data:
            raw_data["people"] = people_data.get("people", [])[:30]  # limit to top 30

        # Extract signals via Claude
        signals_raw = await extract_signals(
            company_name=company.name,
            raw_data=raw_data,
            context=company.description,
        )

        if not signals_raw:
            logger.info(f"No signals found for {company.name}")
            company.last_synced_at = datetime.now(timezone.utc)
            db.commit()
            return

        from ..models.signal import compute_dedup_hash

        # Map Claude's signal type values to SignalType enum
        _TYPE_MAP = {
            "hire": SignalType.NEW_HIRE,
            "new_hire": SignalType.NEW_HIRE,
            "departure": SignalType.DEPARTURE,
            "founder_post": SignalType.FOUNDER_POST,
            "press": SignalType.OTHER,      # stored as OTHER; headline distinguishes it
            "funding": SignalType.FUNDING,
            "product": SignalType.PRODUCT_LAUNCH,
            "product_launch": SignalType.PRODUCT_LAUNCH,
            "partnership": SignalType.PARTNERSHIP,
            "other": SignalType.OTHER,
        }

        new_signals = []
        for s in signals_raw:
            # Claude returns "headline"; model stores as "title"
            title = s.get("headline", s.get("title", ""))[:200]
            if not title:
                continue

            signal_type = _TYPE_MAP.get(s.get("type", "other").lower(), SignalType.OTHER)

            importance_raw = s.get("importance", "medium").lower()
            try:
                importance = SignalImportance(importance_raw)
            except ValueError:
                importance = SignalImportance.MEDIUM

            dedup_hash = compute_dedup_hash(company.id, signal_type.value, title)
            if db.query(Signal).filter(Signal.dedup_hash == dedup_hash).first():
                continue

            # Claude returns "detail" and "source"; model stores as "description"/"source_url"
            confidence = s.get("confidence")
            if confidence is not None:
                confidence = max(0.0, min(1.0, float(confidence)))

            signal = Signal(
                company_id=company.id,
                signal_type=signal_type,
                importance=importance,
                title=title,
                description=s.get("detail", s.get("description", ""))[:500],
                source_url=s.get("source") or s.get("source_url"),
                raw_data=json.dumps(raw_data)[:5000],
                dedup_hash=dedup_hash,
                confidence=confidence,
                person_name=s.get("person_name"),
            )
            db.add(signal)
            new_signals.append(s)

        company.last_synced_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(f"Saved {len(new_signals)} new signals for {company.name}")

        # Alert on medium/high importance signals only
        alertable = [s for s in new_signals if s.get("importance") in ("medium", "high")]
        if alertable:
            await send_signal_alert(alertable, company.name)

    except Exception as e:
        logger.error(f"Error processing company {company_id}: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


async def run_daily_job() -> None:
    """Daily job: process all active portfolio companies."""
    from ..models.company import Company

    logger.info("Daily portfolio intelligence job starting...")
    db = SessionLocal()
    try:
        companies = db.query(Company).filter(Company.is_active == True).all()
        company_ids = [c.id for c in companies]
        logger.info(f"Processing {len(company_ids)} companies")
    finally:
        db.close()

    for company_id in company_ids:
        await process_single_company(company_id)

    logger.info("Daily portfolio intelligence job complete.")


def start_scheduler() -> None:
    """Start the APScheduler with the daily job."""
    scheduler = get_scheduler()
    if scheduler.running:
        return

    scheduler.add_job(
        run_daily_job,
        trigger=CronTrigger(
            hour=settings.DAILY_SCHEDULER_HOUR,
            minute=settings.DAILY_SCHEDULER_MINUTE,
            timezone="UTC",
        ),
        id="daily_portfolio_intelligence",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.start()
    logger.info(
        f"Scheduler started. Daily job runs at "
        f"{settings.DAILY_SCHEDULER_HOUR:02d}:{settings.DAILY_SCHEDULER_MINUTE:02d} UTC"
    )


def stop_scheduler() -> None:
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")
