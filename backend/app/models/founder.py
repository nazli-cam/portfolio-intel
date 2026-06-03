from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class Founder(Base):
    __tablename__ = "founders"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    linkedin_url = Column(String, nullable=True)
    twitter_url = Column(String, nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company", back_populates="founders")
