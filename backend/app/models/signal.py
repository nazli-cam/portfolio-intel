import enum
import hashlib

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class SignalType(str, enum.Enum):
    NEW_HIRE = "new_hire"
    DEPARTURE = "departure"
    FOUNDER_POST = "founder_post"
    FUNDING = "funding"
    PARTNERSHIP = "partnership"
    PRODUCT_LAUNCH = "product_launch"
    EXIT = "exit"
    OTHER = "other"


class SignalImportance(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    signal_type = Column(Enum(SignalType), nullable=False, index=True)
    importance = Column(Enum(SignalImportance), default=SignalImportance.MEDIUM)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    source_url = Column(String, nullable=True)
    raw_data = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    person_name = Column(String(200), nullable=True)
    dedup_hash = Column(String(64), nullable=True, index=True, unique=True)
    is_read = Column(Boolean, default=False, index=True)
    is_alerted = Column(Boolean, default=False)
    is_accurate = Column(Boolean, nullable=True)    # None=not voted, True=correct, False=incorrect
    is_duplicate = Column(Boolean, nullable=True)   # True=fuzzy-match dup detected on save
    detected_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company", back_populates="signals")


def compute_dedup_hash(company_id: int, signal_type: str, title: str) -> str:
    """sha256 of (company_id + signal_type + title[:80]) — DB unique constraint key."""
    raw = f"{company_id}:{signal_type}:{title[:80]}"
    return hashlib.sha256(raw.encode()).hexdigest()
