import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import create_tables
from .models.user import User
from .routers import auth, companies, signals, reports
from .routers.auth import get_current_user
from .services.scheduler import start_scheduler, stop_scheduler, get_job_state

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Portfolio Intelligence API...")
    create_tables()
    _seed_demo_user()
    start_scheduler()
    yield
    stop_scheduler()
    logger.info("Portfolio Intelligence API stopped.")


def _seed_demo_user():
    """Create a default admin user if no users exist."""
    from .database import SessionLocal
    from .routers.auth import hash_password

    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            admin = User(
                email="admin@portfoliointel.com",
                name="Admin User",
                hashed_password=hash_password("changeme123"),
                role="admin",
            )
            db.add(admin)
            db.commit()
            logger.info("Seeded default admin: admin@portfoliointel.com / changeme123")
    finally:
        db.close()


def _require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return current_user


app = FastAPI(
    title="Portfolio Intelligence API",
    description="VC Portfolio Intelligence Platform — signal extraction, alerts, and reporting",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — dev allows localhost origins, production locks to FRONTEND_URL
_dev_origins = ["http://localhost:5173", "http://localhost:3000"]
allowed_origins = (
    [settings.FRONTEND_URL]
    if settings.ENVIRONMENT == "production"
    else [settings.FRONTEND_URL] + _dev_origins
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(companies.router)
app.include_router(signals.router)
app.include_router(reports.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "Portfolio Intelligence API", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}


# ---------------------------------------------------------------------------
# Admin endpoints — require admin role
# ---------------------------------------------------------------------------

@app.get("/admin/scheduler/status", tags=["admin"])
def scheduler_status(current_user: User = Depends(_require_admin)):
    """Return current scheduler state: running flag, last run stats, next fire time."""
    return get_job_state()


@app.post("/admin/trigger-daily-job", tags=["admin"], status_code=status.HTTP_202_ACCEPTED)
async def trigger_daily_job(current_user: User = Depends(_require_admin)):
    """Manually trigger the daily intelligence job in the background."""
    from .services.scheduler import run_daily_job, _job_state

    if _job_state["is_running"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Daily job is already running",
        )
    asyncio.create_task(run_daily_job())
    return {"message": "Daily job triggered", "triggered_by": current_user.email}
