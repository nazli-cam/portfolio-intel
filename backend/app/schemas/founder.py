from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class FounderCreate(BaseModel):
    name: str
    linkedin_url: Optional[str] = None
    twitter_url: Optional[str] = None
    company_id: Optional[int] = None
    notes: Optional[str] = None


class FounderUpdate(BaseModel):
    name: Optional[str] = None
    linkedin_url: Optional[str] = None
    twitter_url: Optional[str] = None
    company_id: Optional[int] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class FounderResponse(BaseModel):
    id: int
    name: str
    linkedin_url: Optional[str] = None
    twitter_url: Optional[str] = None
    company_id: Optional[int] = None
    company_name: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
