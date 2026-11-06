# backend/modules/reports/router.py
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend.core.database import get_db
from backend.core.dependencies import get_current_user
from backend import models as core_models
from . import models, schemas

router = APIRouter(
    prefix="/reports",
    tags=["Reports"]
)

@router.get("/", response_model=List[schemas.ReportResponse])
def get_reports(
    db: Session = Depends(get_db),
    current_user: core_models.User = Depends(get_current_user)
):
    reports = db.query(models.ReportModel).all()
    return reports

@router.post("/", response_model=schemas.ReportResponse, status_code=status.HTTP_201_CREATED)
def create_report(
    report: schemas.ReportCreate,
    db: Session = Depends(get_db),
    current_user: core_models.User = Depends(get_current_user)
):
    new_report = models.ReportModel(
        title=report.title,
        summary=report.summary,
        created_by_id=current_user.user_id
    )
    db.add(new_report)
    db.commit()
    db.refresh(new_report)
    return new_report
