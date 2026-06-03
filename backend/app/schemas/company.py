from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class FounderInline(BaseModel):
    name: str
    linkedin_url: Optional[str] = None
    twitter_url: Optional[str] = None
    notes: Optional[str] = None


class CompanyCreate(BaseModel):
    name: str
    website: Optional[str] = None
    linkedin_url: Optional[str] = None
    description: Optional[str] = None
    categories: Optional[List[str]] = None
    founders: Optional[List[FounderInline]] = None


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    website: Optional[str] = None
    linkedin_url: Optional[str] = None
    description: Optional[str] = None
    categories: Optional[List[str]] = None
    is_active: Optional[bool] = None
    founders: Optional[List[FounderInline]] = None


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
    categories: Optional[List[str]] = None
    is_active: bool
    last_synced_at: Optional[datetime] = None
    created_at: datetime
    signal_count: Optional[int] = None

    class Config:
        from_attributes = True
