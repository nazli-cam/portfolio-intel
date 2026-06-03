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
    "exit":         "exit",
    "other":        "other",
    # safety net for future Claude output variations
    "acquisition":  "exit",
    "ipo":          "exit",
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

def _save_key_people(db, company_id: int, people: list[dict]) -> None:
    """Upsert Apollo-sourced key people; also create Founder records for founders/CEOs."""
    from ..models.founder import Founder
    from ..models.key_person import KeyPerson

    FOUNDER_CEO_KW = frozenset({"founder", "co-founder", "cofounder", "ceo"})

    existing_kp = {
        kp.name.lower(): kp
        for kp in db.query(KeyPerson).filter(KeyPerson.company_id == company_id).all()
    }
    existing_founder_names = {
        f.name.lower()
        for f in db.query(Founder).filter(Founder.company_id == company_id).all()
    }

    for p in people:
        name = p.get("name", "").strip()
        if not name:
            continue
        title = p.get("title") or ""
        is_founder = any(kw in title.lower() for kw in FOUNDER_CEO_KW)
        name_lower = name.lower()

        if name_lower in existing_kp:
            kp = existing_kp[name_lower]
            kp.title = title
            kp.linkedin_url = p.get("linkedin_url")
            kp.is_founder = is_founder
        else:
            db.add(KeyPerson(
                company_id=company_id,
                name=name,
                title=title,
                linkedin_url=p.get("linkedin_url"),
                is_founder=is_founder,
                apollo_id=p.get("apollo_id"),
            ))

        if is_founder and name_lower not in existing_founder_names:
            db.add(Founder(
                company_id=company_id,
                name=name,
                linkedin_url=p.get("linkedin_url"),
                notes=title,
            ))
            existing_founder_names.add(name_lower)

    db.commit()


async def process_single_company(company_id: int) -> list[dict]:
    """
    Run the Apollo → Claude → save pipeline for one company.
    Returns the list of raw signal dicts that were newly saved (not deduped).
    Caller is responsible for sending alerts.
    """
    from ..models.company import Company
    from ..models.founder import Founder
    from ..models.signal import Signal, SignalImportance, SignalType, compute_dedup_hash
    from ..services.apollo import enrich_organization, fetch_key_people, search_people_at_company
    from ..services.claude_service import extract_signals

    db = SessionLocal()
    try:
        company = (
            db.query(Company)
            .filter(Company.id == company_id, Company.is_active)
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

        # --- Fetch and save Apollo key people (founders/C-suite) ---
        apollo_key_people = await fetch_key_people(company.name, domain)
        if apollo_key_people:
            _save_key_people(db, company.id, apollo_key_people)

        # --- Build key people context for Claude ---
        # Combine Apollo key people (name+title) with manually-added founders (name only)
        kp_names = {p["name"].lower() for p in apollo_key_people}
        manual_founders = db.query(Founder).filter(
            Founder.company_id == company.id, Founder.is_active
        ).all()
        extra = [f.name for f in manual_founders if f.name.lower() not in kp_names]
        key_people_ctx: list = list(apollo_key_people) + extra if (apollo_key_people or extra) else None  # type: ignore[assignment]

        # --- Claude signal extraction ---
        signals_raw = await extract_signals(
            company_name=company.name,
            raw_data=raw_data,
            context=company.description,
            key_people=key_people_ctx,
        )

        company.last_synced_at = datetime.now(timezone.utc)

        if not signals_raw:
            logger.info(f"[scheduler] No signals for {company.name}")
            db.commit()
            return []

        # --- Dedup + persist ---
        new_signals: list[dict] = []
        raw_data_json = json.dumps(raw_data, default=str)[:5000]

        from datetime import timedelta
        from difflib import SequenceMatcher

        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        recent_titles = [
            r[0] for r in db.query(Signal.title)
            .filter(Signal.company_id == company.id, Signal.created_at >= cutoff)
            .all()
        ]

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
                continue  # exact dedup

            confidence = s.get("confidence")
            if confidence is not None:
                confidence = max(0.0, min(1.0, float(confidence)))

            # Fuzzy duplicate detection against recent 30-day signals
            title_lower = title.lower()
            is_dup = any(
                SequenceMatcher(None, title_lower, t.lower()).ratio() > 0.8
                for t in recent_titles
            )

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
                is_duplicate=is_dup if is_dup else None,
            )
            db.add(signal)
            new_signals.append(s)
            recent_titles.append(title)  # include in window for subsequent signals this batch

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
            companies = db.query(Company).filter(Company.is_active).all()
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
