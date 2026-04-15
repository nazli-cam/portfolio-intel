from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from ..models.signal import SignalType, SignalImportance


class SignalResponse(BaseModel):
    id: int
    company_id: int
    company_name: Optional[str] = None
    signal_type: SignalType
    importance: SignalImportance
    title: str
    description: Optional[str] = None
    source_url: Optional[str] = None
    is_read: bool
    is_alerted: bool
    detected_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class SignalUpdate(BaseModel):
    is_read: Optional[bool] = None
