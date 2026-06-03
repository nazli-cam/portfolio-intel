from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from ..models.signal import SignalImportance, SignalType


class SignalResponse(BaseModel):
    id: int
    company_id: int
    company_name: Optional[str] = None
    signal_type: SignalType
    importance: SignalImportance
    title: str
    description: Optional[str] = None
    source_url: Optional[str] = None
    confidence: Optional[float] = None
    person_name: Optional[str] = None
    is_read: bool
    is_alerted: bool
    is_accurate: Optional[bool] = None
    is_duplicate: Optional[bool] = None
    detected_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class SignalCreate(BaseModel):
    """Used by the Claude service to validate extracted signals before DB insert."""
    company_id: int
    signal_type: SignalType
    importance: SignalImportance = SignalImportance.MEDIUM
    title: str
    description: Optional[str] = None
    source_url: Optional[str] = None
    confidence: Optional[float] = None
    person_name: Optional[str] = None


class SignalUpdate(BaseModel):
    is_read: Optional[bool] = None


class SignalFeedback(BaseModel):
    is_accurate: bool
