from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CompanyCreate(BaseModel):
    name: str
    website: Optional[str] = None
    linkedin_url: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    stage: Optional[str] = None
    headquarters: Optional[str] = None
    founded_year: Optional[int] = None


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    website: Optional[str] = None
    linkedin_url: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    stage: Optional[str] = None
    headquarters: Optional[str] = None
    founded_year: Optional[int] = None
    is_active: Optional[bool] = None


class CompanyResponse(BaseModel):
    id: int
    name: str
    website: Optional[str] = None
    linkedin_url: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    stage: Optional[str] = None
    headquarters: Optional[str] = None
    employee_count: Optional[int] = None
    founded_year: Optional[int] = None
    is_active: bool
    last_synced_at: Optional[datetime] = None
    created_at: datetime
    signal_count: Optional[int] = None

    class Config:
        from_attributes = True
