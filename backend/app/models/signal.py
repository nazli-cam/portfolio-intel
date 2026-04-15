import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum
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
    raw_data = Column(Text, nullable=True)  # JSON string of raw Apollo/source data
    is_read = Column(Boolean, default=False, index=True)
    is_alerted = Column(Boolean, default=False)  # email alert sent
    detected_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company", back_populates="signals")
