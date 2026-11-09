from fastapi import APIRouter, Depends, status, Request
from sqlalchemy.orm import Session
from datetime import timedelta
from ... import models, schemas
from ...core import database
from ...core.database import get_db
from fastapi.security import OAuth2PasswordRequestForm
from ...core.dependencies import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user
)
from ...core.exceptions import AuthenticationException, NotFoundException, ValidationException
from ...core.logging_config import get_logger
from ..integrations import services as integration_services
from ..users import services as user_services
from sqlalchemy import func
from datetime import datetime, timezone

logger = get_logger(__name__)

router = APIRouter(tags=["Authentication"])

@router.get("/config", response_model=schemas.AuthConfigResponse)
def get_auth_config(db: Session = Depends(database.get_db)):
    """현재 활성화된 인증 수단 반환 (Entra는 관리자 화면에서 연동을 설정한 경우에만 활성)"""
    return integration_services.get_auth_config(db)

@router.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    user: schemas.UserCreate, 
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """새 사용자 등록 (시스템 관리자 전용)"""
    # 권한 확인
    if current_user.role != models.UserRole.SYSTEM_ADMIN:
        logger.warning(f"권한 없는 회원가입 시도: {current_user.user_email}")
        raise AuthenticationException("사용자를 등록할 권한이 없습니다")

    # 이메일 검증
    if not user.user_email or '@' not in user.user_email:
        logger.warning(f"잘못된 이메일 형식: {user.user_email}")
        raise ValidationException("올바른 이메일 주소를 입력해주세요")
    
    # 기존 사용자 확인
    existing_user = db.query(models.User).filter(models.User.user_email == user.user_email).first()
    if existing_user:
        logger.warning(f"중복 회원가입 시도: {user.user_email}")
        raise ValidationException("이미 등록된 이메일 주소입니다")
    
    # 사용자 생성
    db_user = models.User(
        user_email=user.user_email,
        hashed_password=get_password_hash(user.password),
        user_name=user.user_name,
        company=user.company,
        department=user.department,
        role=user.role,
        manager_id=user_services.validate_manager(db, user.manager_id),
    )
    db.add(db_user)
    
    # 감사 로그 생성
    audit_log = models.SystemAuditLog(
        actor_id=current_user.user_id,
        action=f"USER_REGISTERED: {user.user_email} ({user.role})",
        ip_address=request.client.host if request.client else "Unknown"
    )
    db.add(audit_log)
    
    db.commit()
    db.refresh(db_user)
    
    logger.info(f"새 사용자 등록 완료: {user.user_email} (역할: {user.role}) by {current_user.user_email}")
    return db_user

from ...core.limiter import limiter
from fastapi import Request

@router.post("/login", response_model=schemas.Token)
@limiter.limit("5/minute")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(database.get_db)
):
    """
    사용자 로그인
    - Swagger UI 호환성을 위해 OAuth2PasswordRequestForm 사용
    - Frontend에서는 JSON으로 보내는 대신 Form Data로 보내거나,
      또는 이 함수를 수정하여 Union[OAuth2PasswordRequestForm, schemas.UserLogin]을 처리해야 함.
    - 가장 깔끔한 방법은 Frontend도 Form Data를 사용하도록 변경하거나,
      여기서 Body/Form을 모두 받을 수 있도록 처리하는 것임.
    """
    
    # OAuth2PasswordRequestForm의 username 필드를 이메일로 사용
    user_email = form_data.username
    password = form_data.password

    # 사용자 조회
    user = db.query(models.User).filter(models.User.user_email == user_email).first()
    
    # 자체 계정 로그인 제한 정책 확인 (Entra 미설정 시 기본 인증 방식은 LOCAL로 간주)
    auth_config = integration_services.get_auth_config(db)
    allow_local = auth_config.allow_local
    default_auth_method = auth_config.default_method
    
    # 로컬 로그인이 비활성화되었거나, 기본 인증 방식이 LOCAL이 아닌 경우(예: ENTRA) 일반 사용자의 로그인을 제한
    if not allow_local or default_auth_method != "LOCAL":
        # 사용자가 없거나, 역할이 관리자가 아닌 경우 거부
        if not user or user.role not in [models.UserRole.SYSTEM_ADMIN, models.UserRole.SECURITY_ADMIN]:
            logger.warning(f"로그인 거부: 자체 계정 로그인 제한(정책: {default_auth_method}) - {user_email}")
            raise AuthenticationException("현재 인증 정책에 의해 자체 계정 로그인은 관리자에게만 허용됩니다. SSO 로그인을 이용해 주세요.")

    if not user:
        logger.warning(f"로그인 실패: 존재하지 않는 이메일 - {user_email}")
        raise AuthenticationException("이메일 또는 비밀번호가 올바르지 않습니다")
    
    # 비밀번호 검증
    if not verify_password(password, user.hashed_password):
        logger.warning(f"로그인 실패: 잘못된 비밀번호 - {user_email}")
        raise AuthenticationException("이메일 또는 비밀번호가 올바르지 않습니다")
    
    # 액세스 토큰 생성
    access_token = create_access_token(
        data={"sub": user.user_email, "name": user.user_name, "role": user.role}
    )
    
    # 마지막 로그인 시간 업데이트
    user.last_login = datetime.now(timezone.utc)
    db.commit()
    
    logger.info(f"로그인 성공: {user_email} (역할: {user.role})")
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/pwchange")
def change_password(request: Request, pw_data: schemas.PasswordChange, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(pw_data.old_password, current_user.hashed_password):
        logger.warning(f"비밀번호 변경 실패: 기존 비밀번호 불일치 - {current_user.user_email}")
        raise ValidationException("기존 비밀번호가 올바르지 않습니다")
        
    current_user.hashed_password = get_password_hash(pw_data.new_password)
    
    # Log Password Change
    log = models.LoginHistory(
        user_id=current_user.user_id,
        ip_address=request.client.host,
        status="PW_CHANGE"
    )
    db.add(log)
    db.commit()
    
    return {"message": "Password updated successfully"}

@router.post("/loginhistory")
def create_login_history(
    request: Request,
    status: str, # passed as query or body? Let's assume body if schema, or simple query for now to match table simplicity. Use Schema properly.
    # Actually, better to use a Pydantic model for body. But table just says POST /loginhistory.
    # I will assume it takes a simple JSON with status.
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # This endpoint allows manual logging of events
    log = models.LoginHistory(
        user_id=current_user.user_id,
        ip_address=request.client.host,
        status=status
    )
    db.add(log)
    db.commit()
    return {"message": "Log saved"}

@router.get("/loginhistory", response_model=list[schemas.LoginHistoryResponse])
def get_login_history(
    skip: int = 0, 
    limit: int = 100,
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    # Security/Audit Admin can see all
    if current_user.role in [models.UserRole.SECURITY_ADMIN, models.UserRole.AUDIT_TEAM, models.UserRole.SYSTEM_ADMIN]:
        return db.query(models.LoginHistory).order_by(models.LoginHistory.login_at.desc()).offset(skip).limit(limit).all()
    
    # Regular users see their own
    return db.query(models.LoginHistory).filter(models.LoginHistory.user_id == current_user.user_id).order_by(models.LoginHistory.login_at.desc()).offset(skip).limit(limit).all()
@router.post("/login/entra", response_model=schemas.Token)
@limiter.limit("10/minute")
def login_entra(
    request: Request,
    token_data: schemas.EntraLoginRequest,
    db: Session = Depends(database.get_db)
):
    """
    Microsoft Entra ID(SSO)를 통한 로그인
    - 관리자 화면에서 Entra 연동을 활성화한 경우에만 허용
    - 프론트엔드가 받은 ID 토큰의 서명·대상(우리 앱)·테넌트·만료를 검증한 뒤 사용자를 식별
    """
    entra = integration_services.get_entra_config(db)
    if not entra.is_ready:
        logger.warning("Entra ID 로그인 거부: 연동이 설정되지 않았거나 비활성 상태")
        raise AuthenticationException("Entra ID 로그인이 활성화되어 있지 않습니다")

    claims = integration_services.verify_entra_id_token(token_data.id_token, entra)
    user_email = claims.get("preferred_username") or claims.get("upn") or claims.get("email")
    if not user_email:
        logger.error("Entra ID 토큰에 사용자 식별 정보(UPN/email)가 없습니다")
        raise AuthenticationException("사용자 정보를 식별할 수 없습니다")

    # 로컬 DB에서 사용자 조회 (UPN 대소문자 차이 무시)
    user = db.query(models.User).filter(func.lower(models.User.user_email) == user_email.lower()).first()
    if not user:
        logger.warning(f"Entra ID 로그인 실패: 등록되지 않은 사용자 - {user_email}")
        # 전수 동기화 정책이므로, 여기에 없는 사용자는 접근 거부
        raise AuthenticationException("등록되지 않은 사용자 계정입니다. 관리자에게 문의하세요.")

    local_access_token = create_access_token(
        data={"sub": user.user_email, "name": user.user_name, "role": user.role}
    )
    user.last_login = datetime.now(timezone.utc)
    db.add(models.SystemAuditLog(
        actor_id=user.user_id,
        action="LOGIN_ENTRA_SUCCESS",
        ip_address=request.client.host if request.client else "Unknown"
    ))
    db.commit()

    logger.info(f"Entra ID 로그인 성공: {user.user_email} (역할: {user.role})")
    return {"access_token": local_access_token, "token_type": "bearer"}
