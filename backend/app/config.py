import logging
import secrets
from typing import Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


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

    # Gmail SMTP (App Password — not account password)
    GMAIL_USER: str = ""          # sender address, e.g. alerts@yourfirm.com
    GMAIL_APP_PASSWORD: str = ""  # Gmail App Password (16-char, spaces optional)
    ALERT_EMAIL_RECIPIENTS: str = ""  # comma-separated recipient list

    # Frontend URL for CORS
    FRONTEND_URL: str = "http://localhost:5173"

    # Scheduler times
    DAILY_SCHEDULER_HOUR: int = 8
    DAILY_SCHEDULER_MINUTE: int = 0

    @model_validator(mode="after")
    def _validate_gmail(self) -> "Settings":
        if self.GMAIL_APP_PASSWORD:
            cleaned = self.GMAIL_APP_PASSWORD.replace(" ", "")
            if len(cleaned) != 16:
                logger.warning(
                    f"GMAIL_APP_PASSWORD has {len(cleaned)} chars after stripping spaces "
                    f"(expected 16). Gmail SMTP will fail at runtime."
                )
        return self

    @property
    def alert_recipients_list(self) -> list[str]:
        return [e.strip() for e in self.ALERT_EMAIL_RECIPIENTS.split(",") if e.strip()]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
