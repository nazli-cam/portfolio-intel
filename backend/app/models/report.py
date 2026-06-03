from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from ..database import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    month = Column(Integer, nullable=False)  # 1-12
    year = Column(Integer, nullable=False)
    html_content = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    signal_count = Column(Integer, default=0)
    company_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
