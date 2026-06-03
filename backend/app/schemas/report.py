from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ReportCreate(BaseModel):
    month: int  # 1-12
    year: int


class ReportResponse(BaseModel):
    id: int
    title: str
    month: int
    year: int
    html_content: Optional[str] = None
    summary: Optional[str] = None
    signal_count: int
    company_count: int
    created_at: datetime

    class Config:
        from_attributes = True
