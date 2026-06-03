from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models.signal import Signal, SignalType
from ..models.user import User
from ..routers.auth import get_current_user
from ..schemas.signal import SignalFeedback, SignalResponse, SignalUpdate

router = APIRouter(prefix="/signals", tags=["signals"])


def _signal_response(signal: Signal) -> SignalResponse:
    resp = SignalResponse.model_validate(signal)
    if signal.company:
        resp.company_name = signal.company.name
    return resp


@router.get("", response_model=List[SignalResponse])
def list_signals(
    company_id: Optional[int] = None,
    signal_type: Optional[SignalType] = None,
    unread_only: bool = False,
    hide_duplicates: bool = False,
    date_from: Optional[datetime] = Query(None, description="ISO-8601 UTC start, e.g. 2024-01-01T00:00:00Z"),
    date_to: Optional[datetime] = Query(None, description="ISO-8601 UTC end, e.g. 2024-01-31T23:59:59Z"),
    order_by: str = Query("created_at", description="Field to sort by: created_at or detected_at"),
    sort: str = Query("desc", description="Sort direction: asc or desc"),
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Signal).options(joinedload(Signal.company))

    if company_id:
        q = q.filter(Signal.company_id == company_id)
    if signal_type:
        q = q.filter(Signal.signal_type == signal_type)
    if unread_only:
        q = q.filter(not Signal.is_read)
    if hide_duplicates:
        q = q.filter((Signal.is_duplicate.is_(None)) | (Signal.is_duplicate.is_(False)))
    if date_from:
        q = q.filter(Signal.detected_at >= date_from)
    if date_to:
        q = q.filter(Signal.detected_at <= date_to)

    sort_col = Signal.created_at if order_by == "created_at" else Signal.detected_at
    sort_expr = sort_col.asc() if sort == "asc" else sort_col.desc()
    signals = q.order_by(sort_expr).offset(offset).limit(limit).all()
    return [_signal_response(s) for s in signals]


@router.get("/count")
def signal_count(
    company_id: Optional[int] = None,
    signal_type: Optional[SignalType] = None,
    importance: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return total signal count, optionally filtered. Used for dashboard stat cards."""
    from ..models.signal import SignalImportance
    q = db.query(Signal)
    if company_id:
        q = q.filter(Signal.company_id == company_id)
    if signal_type:
        q = q.filter(Signal.signal_type == signal_type)
    if importance:
        try:
            q = q.filter(Signal.importance == SignalImportance(importance))
        except ValueError:
            pass
    return {"count": q.count()}


@router.get("/unread-count")
def unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = db.query(Signal).filter(not Signal.is_read).count()
    return {"unread_count": count}


@router.get("/{signal_id}", response_model=SignalResponse)
def get_signal(
    signal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    signal = (
        db.query(Signal)
        .options(joinedload(Signal.company))
        .filter(Signal.id == signal_id)
        .first()
    )
    if not signal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signal not found")
    return _signal_response(signal)


@router.patch("/{signal_id}", response_model=SignalResponse)
def update_signal(
    signal_id: int,
    signal_in: SignalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    signal = (
        db.query(Signal)
        .options(joinedload(Signal.company))
        .filter(Signal.id == signal_id)
        .first()
    )
    if not signal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signal not found")

    update_data = signal_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(signal, field, value)

    db.commit()
    db.refresh(signal)
    return _signal_response(signal)


@router.patch("/{signal_id}/feedback", response_model=SignalResponse)
def signal_feedback(
    signal_id: int,
    feedback: SignalFeedback,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    signal = (
        db.query(Signal)
        .options(joinedload(Signal.company))
        .filter(Signal.id == signal_id)
        .first()
    )
    if not signal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signal not found")
    # Toggle: if same value sent again, clear the vote
    if signal.is_accurate == feedback.is_accurate:
        signal.is_accurate = None
    else:
        signal.is_accurate = feedback.is_accurate
    db.commit()
    db.refresh(signal)
    return _signal_response(signal)


@router.post("/mark-all-read", status_code=status.HTTP_200_OK)
def mark_all_read(
    company_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Signal).filter(not Signal.is_read)
    if company_id:
        q = q.filter(Signal.company_id == company_id)
    updated = q.update({"is_read": True})
    db.commit()
    return {"marked_read": updated}
