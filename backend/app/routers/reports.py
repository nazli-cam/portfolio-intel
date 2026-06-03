from datetime import datetime
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.report import Report
from ..models.user import User
from ..routers.auth import get_current_user
from ..schemas.report import ReportCreate, ReportResponse

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=List[ReportResponse])
def list_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reports = db.query(Report).order_by(Report.year.desc(), Report.month.desc()).all()
    return reports


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report


@router.post("/generate", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def generate_report(
    report_in: ReportCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check if report for this month/year already exists
    existing = (
        db.query(Report)
        .filter(Report.month == report_in.month, Report.year == report_in.year)
        .first()
    )
    if existing:
        # Regenerate: delete old and create new
        db.delete(existing)
        db.commit()

    from ..services.report import generate_monthly_report
    report = await generate_monthly_report(report_in.month, report_in.year, db)
    return report


@router.post("/generate/current-month", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def generate_current_month_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.now()
    existing = (
        db.query(Report)
        .filter(Report.month == now.month, Report.year == now.year)
        .first()
    )
    if existing:
        db.delete(existing)
        db.commit()

    from ..services.report import generate_monthly_report
    report = await generate_monthly_report(now.month, now.year, db)
    return report


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    db.delete(report)
    db.commit()
