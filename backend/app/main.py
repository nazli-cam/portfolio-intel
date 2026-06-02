from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import create_tables
from .routers import auth, companies, signals, reports
from .services.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Portfolio Intelligence API...")
    create_tables()
    _seed_demo_user()
    start_scheduler()
    yield
    # Shutdown
    stop_scheduler()
    logger.info("Portfolio Intelligence API stopped.")


def _seed_demo_user():
    """Create a default admin user if no users exist."""
    from .database import SessionLocal
    from .models.user import User
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
            logger.info("Seeded default admin user: admin@portfoliointel.com / changeme123")
    finally:
        db.close()


app = FastAPI(
    title="Portfolio Intelligence API",
    description="VC Portfolio Intelligence Platform — signal extraction, alerts, and reporting",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
allowed_origins = [settings.FRONTEND_URL, "http://localhost:5173", "http://localhost:3000"]
if settings.ENVIRONMENT == "production":
    # Add your Vercel URL here
    allowed_origins = [settings.FRONTEND_URL]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
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


@app.post("/admin/trigger-daily-job", tags=["admin"])
async def trigger_daily_job(
    background_tasks: BackgroundTasks,
    current_user=Depends(auth.get_current_user),
):
    """Manually trigger the daily intelligence gathering job (admin only)."""
    from .services.scheduler import run_daily_job
    background_tasks.add_task(run_daily_job)
    return {"message": "Daily job triggered in background"}
