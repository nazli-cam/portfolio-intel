from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    website = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    industry = Column(String, nullable=True)
    stage = Column(String, nullable=True)
    headquarters = Column(String, nullable=True)
    employee_count = Column(Integer, nullable=True)
    founded_year = Column(Integer, nullable=True)
    categories = Column(JSON, nullable=True, default=list)
    apollo_org_id = Column(String, nullable=True, index=True)
    is_active = Column(Boolean, default=True)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    signals = relationship("Signal", back_populates="company", cascade="all, delete-orphan")
