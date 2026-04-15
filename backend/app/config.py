from pydantic_settings import BaseSettings
from typing import Optional
import secrets


class Settings(BaseSettings):
    # App
    SECRET_KEY: str = secrets.token_hex(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str = "sqlite:///./portfolio_intel.db"

    # Anthropic
    ANTHROPIC_API_KEY: Optional[str] = None

    # Apollo.io
    APOLLO_API_KEY: Optional[str] = None

    # Gmail OAuth2
    GMAIL_CLIENT_ID: Optional[str] = None
    GMAIL_CLIENT_SECRET: Optional[str] = None
    GMAIL_REFRESH_TOKEN: Optional[str] = None
    GMAIL_SENDER_EMAIL: str = "alerts@example.com"

    # Alert recipients (comma-separated string)
    ALERT_EMAIL_RECIPIENTS: str = ""

    # Frontend URL for CORS
    FRONTEND_URL: str = "http://localhost:5173"

    # Scheduler times
    DAILY_SCHEDULER_HOUR: int = 8
    DAILY_SCHEDULER_MINUTE: int = 0

    @property
    def alert_recipients_list(self) -> list[str]:
        return [e.strip() for e in self.ALERT_EMAIL_RECIPIENTS.split(",") if e.strip()]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
