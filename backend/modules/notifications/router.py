"""알림 메일 템플릿 API (시스템관리자·보안관리자)"""
from typing import List

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ... import models, schemas
from ...core import dependencies
from ...core.database import get_db
from ...core.exceptions import AuthorizationException
from . import services

router = APIRouter(prefix="/notifications", tags=["Notifications"])

ALLOWED_ROLES = (models.UserRole.SYSTEM_ADMIN, models.UserRole.SECURITY_ADMIN)


def _require_admin(user: models.User):
    if user.role not in ALLOWED_ROLES:
        raise AuthorizationException("알림 템플릿을 관리할 권한이 없습니다")


def _ip(request: Request) -> str:
    return request.client.host if request.client else "Unknown"


@router.get("/templates", response_model=List[schemas.NotificationTemplateResponse])
def list_templates(current_user: models.User = Depends(dependencies.get_current_user), db: Session = Depends(get_db)):
    _require_admin(current_user)
    return services.list_templates(db)


@router.put("/templates/{template_key}", response_model=schemas.NotificationTemplateResponse)
def update_template(
    template_key: str, data: schemas.NotificationTemplateUpdate, request: Request,
    current_user: models.User = Depends(dependencies.get_current_user), db: Session = Depends(get_db),
):
    _require_admin(current_user)
    return services.update_template(db, template_key, data, current_user, _ip(request))


@router.delete("/templates/{template_key}", response_model=schemas.NotificationTemplateResponse)
def reset_template(
    template_key: str, request: Request,
    current_user: models.User = Depends(dependencies.get_current_user), db: Session = Depends(get_db),
):
    """수정본을 지우고 기본 템플릿으로 되돌림"""
    _require_admin(current_user)
    return services.reset_template(db, template_key, current_user, _ip(request))


@router.post("/templates/{template_key}/preview", response_model=schemas.NotificationPreviewResponse)
def preview_template(
    template_key: str, data: schemas.NotificationTemplateUpdate,
    current_user: models.User = Depends(dependencies.get_current_user),
):
    """샘플 값으로 렌더링한 결과 (저장하지 않음)"""
    _require_admin(current_user)
    return services.preview_template(template_key, data)
