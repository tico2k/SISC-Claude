from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from ... import models, schemas
from ...core import dependencies
from ...core.database import get_db
from ...core.exceptions import AuthorizationException
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
