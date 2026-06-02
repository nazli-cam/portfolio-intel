"""
APScheduler daily intelligence job.

Flow per run:
  for each active company:
    1. Apollo.io  — enrich org + search people
    2. Claude     — extract signals from enrichment data
    3. SQLite     — dedup + save new signals
  after all companies:
    4. Gmail      — one digest email grouped by company (skip if zero new signals)
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ..config import settings
from ..database import SessionLocal

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

_TYPE_MAP = {
    "hire":         "new_hire",
    "new_hire":     "new_hire",
    "departure":    "departure",
    "founder_post": "founder_post",
    "press":        "other",
    "funding":      "funding",
    "product":      "product_launch",
    "product_launch": "product_launch",
    "partnership":  "partnership",
    "other":        "other",
    # safety net for future Claude output variations
    "acquisition":  "other",
    "regulatory":   "other",
    "award":        "other",
}

# ---------------------------------------------------------------------------
# Job state — updated by run_daily_job, read by /admin/scheduler/status
# ---------------------------------------------------------------------------

_job_state: dict = {
    "is_running": False,
    "last_run_at": None,             # ISO string UTC
    "last_run_duration_s": None,     # float seconds
    "last_run_companies": 0,
    "last_run_new_signals": 0,
    "last_run_status": None,         # "success" | "partial" | "error"
    "last_error": None,
    "next_run_at": None,             # filled by start_scheduler
}

_scheduler: Optional[AsyncIOScheduler] = None

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_domain(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    try:
        parsed = urlparse(url if url.startswith("http") else f"https://{url}")
        return parsed.netloc.lstrip("www.") or None
    except Exception:
        return None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


def get_job_state() -> dict:
    """Return a copy of the current job state dict (safe to serialise to JSON)."""
    state = dict(_job_state)
    scheduler = get_scheduler()
    if scheduler.running:
        job = scheduler.get_job("daily_portfolio_intelligence")
        if job and job.next_run_time:
            state["next_run_at"] = job.next_run_time.isoformat()
    return state

# ---------------------------------------------------------------------------
# Core: process one company
# ---------------------------------------------------------------------------

async def process_single_company(company_id: int) -> list[dict]:
    """
    Run the Apollo → Claude → save pipeline for one company.
    Returns the list of raw signal dicts that were newly saved (not deduped).
    Caller is responsible for sending alerts.
    """
    from ..models.company import Company
    from ..models.signal import Signal, SignalType, SignalImportance, compute_dedup_hash
    from ..services.apollo import search_people_at_company, enrich_organization
    from ..services.claude_service import extract_signals

    db = SessionLocal()
    try:
        company = (
            db.query(Company)
            .filter(Company.id == company_id, Company.is_active == True)
            .first()
        )
        if not company:
            logger.warning(f"Company {company_id} not found or inactive — skipping")
            return []

        logger.info(f"[scheduler] Processing: {company.name}")
        domain = _extract_domain(company.website)

        # --- Apollo enrichment ---
        raw_data: dict = {"company_name": company.name, "people": [], "organization": {}}

        if domain:
            org_data = await enrich_organization(domain)
            if org_data:
                raw_data["organization"] = org_data
                if org_data.get("estimated_num_employees"):
                    company.employee_count = org_data["estimated_num_employees"]
                if org_data.get("id"):
                    company.apollo_org_id = org_data["id"]

        people_data = await search_people_at_company(company.name, domain)
        if people_data:
            raw_data["people"] = people_data.get("people", [])[:30]

        # --- Claude signal extraction ---
        signals_raw = await extract_signals(
            company_name=company.name,
            raw_data=raw_data,
            context=company.description,
        )

        company.last_synced_at = datetime.now(timezone.utc)

        if not signals_raw:
            logger.info(f"[scheduler] No signals for {company.name}")
            db.commit()
            return []

        # --- Dedup + persist ---
        new_signals: list[dict] = []
        raw_data_json = json.dumps(raw_data, default=str)[:5000]

        for s in signals_raw:
            title = s.get("headline", s.get("title", ""))[:200].strip()
            if not title:
                continue

            signal_type_str = _TYPE_MAP.get(s.get("type", "other").lower(), "other")
            try:
                signal_type = SignalType(signal_type_str)
            except ValueError:
                signal_type = SignalType.OTHER

            importance_raw = s.get("importance", "medium").lower()
            try:
                importance = SignalImportance(importance_raw)
            except ValueError:
                importance = SignalImportance.MEDIUM

            dedup_hash = compute_dedup_hash(company.id, signal_type.value, title)
            if db.query(Signal).filter(Signal.dedup_hash == dedup_hash).first():
                continue  # already stored

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
                raw_data=raw_data_json,
                dedup_hash=dedup_hash,
                confidence=confidence,
                person_name=s.get("person_name"),
            )
            db.add(signal)
            new_signals.append(s)

        db.commit()
        logger.info(f"[scheduler] {company.name}: saved {len(new_signals)} new signals")
        return new_signals

    except Exception as e:
        logger.error(f"[scheduler] Error processing company {company_id}: {e}", exc_info=True)
        db.rollback()
        return []
    finally:
        db.close()

# ---------------------------------------------------------------------------
# Core: daily run
# ---------------------------------------------------------------------------

async def run_daily_job() -> None:
    """
    Daily intelligence job.
    Loops all active companies, then sends ONE digest email at the end.
    Skips the email if no new signals were found across the entire run.
    """
    from ..models.company import Company
    from ..services.gmail import send_daily_digest

    if _job_state["is_running"]:
        logger.warning("[scheduler] Daily job already running — skipping duplicate trigger")
        return

    _job_state["is_running"] = True
    _job_state["last_run_status"] = None
    _job_state["last_error"] = None
    started_at = datetime.now(timezone.utc)
    logger.info("[scheduler] Daily portfolio intelligence job starting")

    try:
        db = SessionLocal()
        try:
            companies = db.query(Company).filter(Company.is_active == True).all()
            company_ids = [(c.id, c.name) for c in companies]
        finally:
            db.close()

        logger.info(f"[scheduler] {len(company_ids)} active companies to process")

        # company_name → list of new signal dicts (only medium/high for digest)
        digest_signals: dict[str, list[dict]] = {}
        total_new = 0
        errors = 0

        for company_id, company_name in company_ids:
            try:
                new_signals = await process_single_company(company_id)
                total_new += len(new_signals)

                alertable = [
                    s for s in new_signals
                    if s.get("importance") in ("medium", "high")
                ]
                if alertable:
                    digest_signals[company_name] = alertable

            except Exception as e:
                # Log + continue — one bad company should not abort the rest
                err_msg = f"{company_name}: {e}"
                logger.error(f"[scheduler] Unhandled error on {err_msg}", exc_info=True)
                errors += 1
                _job_state["last_error"] = err_msg  # surface most-recent error

            # Polite pause between companies — AsyncIOScheduler runs async def
            # coroutines directly on the event loop, so await asyncio.sleep is correct.
            await asyncio.sleep(2)

        # --- Always send a digest so the team knows the scheduler is alive.
        # If no medium/high signals, send a lightweight heartbeat instead of silence.
        try:
            await send_daily_digest(
                company_signals=digest_signals,
                total_new=total_new,
                companies_checked=len(company_ids),
            )
        except Exception as e:
            logger.error(f"[scheduler] Failed to send digest email: {e}", exc_info=True)

        duration = (datetime.now(timezone.utc) - started_at).total_seconds()
        _job_state.update(
            last_run_at=started_at.isoformat(),
            last_run_duration_s=round(duration, 1),
            last_run_companies=len(company_ids),
            last_run_new_signals=total_new,
            last_run_status="partial" if errors else "success",
        )
        logger.info(
            f"[scheduler] Job complete — {total_new} new signals across "
            f"{len(company_ids)} companies in {duration:.1f}s"
        )

    except Exception as e:
        _job_state["last_run_status"] = "error"
        _job_state["last_error"] = str(e)
        logger.error(f"[scheduler] Job failed: {e}", exc_info=True)
    finally:
        _job_state["is_running"] = False

# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

def start_scheduler() -> None:
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
        misfire_grace_time=3600,  # run within 1h if server was down at fire time
    )
    scheduler.start()

    job = scheduler.get_job("daily_portfolio_intelligence")
    if job and job.next_run_time:
        _job_state["next_run_at"] = job.next_run_time.isoformat()

    logger.info(
        f"[scheduler] Started — daily job fires at "
        f"{settings.DAILY_SCHEDULER_HOUR:02d}:{settings.DAILY_SCHEDULER_MINUTE:02d} UTC"
    )


def stop_scheduler() -> None:
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[scheduler] Stopped")
