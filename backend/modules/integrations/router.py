"""외부 연동 설정 API (시스템 관리자 전용)"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ... import models, schemas
from ...core import dependencies
from ...core.database import get_db
from ...core.exceptions import AuthorizationException
from ...core.logging_config import get_logger
from . import services

logger = get_logger(__name__)
router = APIRouter(prefix="/integrations", tags=["Integrations"])


def _require_system_admin(user: models.User):
    if user.role != models.UserRole.SYSTEM_ADMIN:
        logger.warning(f"권한 없는 연동 설정 접근 시도: {user.user_email}")
        raise AuthorizationException("연동 설정 권한이 없습니다")


@router.get("/entra", response_model=schemas.EntraIntegrationResponse)
def get_entra_integration(
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """Entra ID 연동 설정 조회 (시크릿은 설정 여부만 반환)"""
    _require_system_admin(current_user)
    return services.to_entra_response(db)


@router.put("/entra", response_model=schemas.EntraIntegrationResponse)
def update_entra_integration(
    data: schemas.EntraIntegrationUpdate,
    request: Request,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """Entra ID 연동 설정 저장 (재시작 없이 즉시 반영)"""
    _require_system_admin(current_user)
    ip = request.client.host if request.client else "Unknown"
    return services.update_entra_config(db, data, current_user, ip)


@router.post("/entra/test", response_model=schemas.IntegrationTestResponse)
def test_entra_integration(
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """저장된 설정으로 Entra ID 앱 인증을 시험한다"""
    _require_system_admin(current_user)
    return services.check_entra_connection(db)


@router.get("/teams", response_model=schemas.TeamsIntegrationResponse)
def get_teams_integration(
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """Teams 채널 웹훅 설정 조회 (URL은 설정 여부만 반환)"""
    _require_system_admin(current_user)
    return services.to_teams_response(db)


@router.put("/teams", response_model=schemas.TeamsIntegrationResponse)
def update_teams_integration(
    data: schemas.TeamsIntegrationUpdate,
    request: Request,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """Teams 채널 웹훅 설정 저장"""
    _require_system_admin(current_user)
    ip = request.client.host if request.client else "Unknown"
    return services.update_teams_config(db, data, current_user, ip)


@router.post("/teams/test", response_model=schemas.IntegrationTestResponse)
def test_teams_integration(
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """저장된 웹훅으로 테스트 메시지 발송"""
    _require_system_admin(current_user)
    return services.check_teams_connection(db)
