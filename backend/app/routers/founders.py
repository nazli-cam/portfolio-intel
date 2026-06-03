from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models.founder import Founder
from ..models.signal import Signal
from ..models.user import User
from ..routers.auth import get_current_user
from ..schemas.founder import FounderCreate, FounderResponse, FounderUpdate
from ..schemas.signal import SignalResponse

router = APIRouter(prefix="/founders", tags=["founders"])


def _founder_response(founder: Founder) -> FounderResponse:
    resp = FounderResponse.model_validate(founder)
    if founder.company:
        resp.company_name = founder.company.name
    return resp


def _signal_response(signal: Signal) -> SignalResponse:
    resp = SignalResponse.model_validate(signal)
    if signal.company:
        resp.company_name = signal.company.name
    return resp


@router.get("", response_model=List[FounderResponse])
def list_founders(
    company_id: Optional[int] = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Founder).options(joinedload(Founder.company))
    if active_only:
        q = q.filter(Founder.is_active)
    if company_id:
        q = q.filter(Founder.company_id == company_id)
    return [_founder_response(f) for f in q.order_by(Founder.name).all()]


@router.post("", response_model=FounderResponse, status_code=status.HTTP_201_CREATED)
def create_founder(
    founder_in: FounderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    founder = Founder(**founder_in.model_dump())
    db.add(founder)
    db.commit()
    db.refresh(founder)
    return _founder_response(db.query(Founder).options(joinedload(Founder.company)).filter(Founder.id == founder.id).first())


@router.get("/{founder_id}", response_model=FounderResponse)
def get_founder(
    founder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    founder = db.query(Founder).options(joinedload(Founder.company)).filter(Founder.id == founder_id).first()
    if not founder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Founder not found")
    return _founder_response(founder)


@router.put("/{founder_id}", response_model=FounderResponse)
def update_founder(
    founder_id: int,
    founder_in: FounderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    founder = db.query(Founder).options(joinedload(Founder.company)).filter(Founder.id == founder_id).first()
    if not founder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Founder not found")
    for field, value in founder_in.model_dump(exclude_unset=True).items():
        setattr(founder, field, value)
    db.commit()
    db.refresh(founder)
    return _founder_response(db.query(Founder).options(joinedload(Founder.company)).filter(Founder.id == founder_id).first())


@router.delete("/{founder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_founder(
    founder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    founder = db.query(Founder).filter(Founder.id == founder_id).first()
    if not founder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Founder not found")
    db.delete(founder)
    db.commit()


@router.get("/{founder_id}/signals", response_model=List[SignalResponse])
def get_founder_signals(
    founder_id: int,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    founder = db.query(Founder).filter(Founder.id == founder_id).first()
    if not founder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Founder not found")

    from sqlalchemy import func
    signals = (
        db.query(Signal)
        .options(joinedload(Signal.company))
        .filter(func.lower(Signal.person_name) == founder.name.lower())
        .order_by(Signal.detected_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [_signal_response(s) for s in signals]
