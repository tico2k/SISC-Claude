from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from typing import List
from ... import models, schemas
from ...core import dependencies
from ...core.database import get_db
from ...core.exceptions import AuthorizationException, ValidationException
from ...core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["System Audit"])

# Schema for Audit Log (if not in schemas.py, define locally or add to schemas)
# Checking schemas.py content from step 827... Log Schemas only had LoginHistoryResponse.
# I need to add SystemAuditLogResponse schemas.

from sqlalchemy.orm import joinedload

@router.get("/audit-logs", response_model=List[schemas.SystemAuditLogResponse])
def get_audit_logs(
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """시스템 감사 로그 조회"""
    if current_user.role not in [models.UserRole.SYSTEM_ADMIN, models.UserRole.SECURITY_ADMIN, models.UserRole.AUDIT_TEAM]:
        logger.warning(f"권한 없는 감사 로그 조회 시도: {current_user.user_email}")
        raise AuthorizationException("감사 로그를 조회할 권한이 없습니다")
    
    logger.info(f"감사 로그 조회: {current_user.user_email} (skip={skip}, limit={limit})")
    return db.query(models.SystemAuditLog).options(joinedload(models.SystemAuditLog.actor)).order_by(models.SystemAuditLog.occurred_at.desc()).offset(skip).limit(limit).all()


AUDIT_EXPORT_LIMIT = 100000


@router.get("/audit-logs/export")
def export_audit_logs(
    request: Request,
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """감사로그 CSV 내보내기 (감사 제출용). 내보내기 자체도 감사로그에 남긴다"""
    if current_user.role not in [models.UserRole.SYSTEM_ADMIN, models.UserRole.SECURITY_ADMIN, models.UserRole.AUDIT_TEAM]:
        raise AuthorizationException("감사 로그를 내보낼 권한이 없습니다")
    from ...utils.csv_export import csv_response

    query = db.query(models.SystemAuditLog).options(joinedload(models.SystemAuditLog.actor))
    try:
        if start_date:
            query = query.filter(models.SystemAuditLog.occurred_at >= datetime.strptime(start_date, "%Y-%m-%d"))
        if end_date:
            query = query.filter(models.SystemAuditLog.occurred_at < datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1))
    except ValueError:
        raise ValidationException("날짜는 YYYY-MM-DD 형식이어야 합니다")
    logs = query.order_by(models.SystemAuditLog.occurred_at.desc()).limit(AUDIT_EXPORT_LIMIT).all()

    db.add(models.SystemAuditLog(
        actor_id=current_user.user_id,
        action=f"AUDIT_LOG_EXPORTED: {len(logs)} rows (from={start_date or '-'}, to={end_date or '-'})",
        ip_address=request.client.host if request.client else "Unknown",
    ))
    db.commit()

    rows = [[l.log_id, l.occurred_at, l.actor.user_email if l.actor else "system", l.actor.user_name if l.actor else "",
             l.action, l.ip_address] for l in logs]
    return csv_response("audit_logs", ["번호", "일시", "수행자 이메일", "수행자 이름", "행위", "IP"], rows)
