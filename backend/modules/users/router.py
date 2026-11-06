from fastapi import APIRouter, Depends, status, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List
from ... import models, schemas
from ...core import dependencies
from ...core.database import get_db
from ...core.exceptions import AuthorizationException, NotFoundException, ValidationException, DuplicateException, DatabaseException
from . import services
from ...core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["User Management"])

@router.get("/users", response_model=List[schemas.UserResponse])
def get_users(current_user: models.User = Depends(dependencies.get_current_user), db: Session = Depends(get_db)):
    """사용자 목록 조회"""
    if current_user.role not in [models.UserRole.SYSTEM_ADMIN, models.UserRole.SECURITY_ADMIN]:
        logger.warning(f"권한 없는 사용자 목록 조회 시도: {current_user.user_email}")
        raise AuthorizationException("사용자 목록을 조회할 권한이 없습니다")
    
    logger.info(f"사용자 목록 조회: {current_user.user_email}")
    return db.query(models.User).all()

@router.post("/users", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user: schemas.UserCreate,
    request: Request,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """새 사용자 생성 (시스템 관리자만 가능)"""
    if current_user.role not in [models.UserRole.SYSTEM_ADMIN]:
        logger.warning(f"권한 없는 사용자 생성 시도: {current_user.user_email}")
        raise AuthorizationException("사용자를 생성할 권한이 없습니다")
    
    # 이메일 중복 확인
    db_user = db.query(models.User).filter(models.User.user_email == user.user_email).first()
    if db_user:
        logger.warning(f"중복된 이메일로 사용자 생성 시도: {user.user_email}")
        raise DuplicateException("이미 등록된 이메일 주소입니다")
    
    try:
        # 사용자 생성
        hashed_password = dependencies.get_password_hash(user.password)
        new_user = models.User(
            user_email=user.user_email,
            user_name=user.user_name,
            hashed_password=hashed_password,
            company=user.company,
            department=user.department,
            role=user.role
        )
        db.add(new_user)
        db.flush()

        # 감사 로그 생성
        audit_log = models.SystemAuditLog(
            actor_id=current_user.user_id,
            action=f"USER_CREATED: {new_user.user_email} ({new_user.role})",
            ip_address=request.client.host if request.client else "Unknown"
        )
        db.add(audit_log)
        
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"사용자 생성 성공: {new_user.user_email} (역할: {new_user.role})")
        return new_user
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"사용자 생성 실패: {str(e)}", exc_info=True)
        raise DatabaseException("사용자 생성 중 오류가 발생했습니다")

@router.put("/users/{user_id}", response_model=schemas.UserResponse)
def update_user(
    user_id: int,
    user_update: schemas.UserUpdate,
    request: Request,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """사용자 정보 수정"""
    # 권한 확인: 시스템 관리자이거나 본인
    if current_user.role not in [models.UserRole.SYSTEM_ADMIN]:
        if current_user.user_id != user_id:
            logger.warning(f"권한 없는 사용자 수정 시도: {current_user.user_email} -> User ID {user_id}")
            raise AuthorizationException("사용자 정보를 수정할 권한이 없습니다")
    
    # 사용자 조회
    db_user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not db_user:
        logger.warning(f"존재하지 않는 사용자 수정 시도: User ID {user_id}")
        raise NotFoundException("사용자를 찾을 수 없습니다")
    
    try:
        original_email = db_user.user_email
        
        # 사용자 정보 업데이트
        db_user.user_email = user_update.user_email
        db_user.user_name = user_update.user_name
        db_user.company = user_update.company
        db_user.department = user_update.department
        db_user.role = user_update.role

        # 비밀번호 변경 시
        if user_update.password:
            db_user.hashed_password = dependencies.get_password_hash(user_update.password)
            
            audit_log = models.SystemAuditLog(
                actor_id=current_user.user_id,
                action=f"USER_PASSWORD_RESET: ID {user_id}",
                ip_address=request.client.host if request.client else "Unknown"
            )
            db.add(audit_log)
            logger.info(f"사용자 비밀번호 변경: User ID {user_id}")
        
        # 일반 업데이트 감사 로그
        audit_log_update = models.SystemAuditLog(
            actor_id=current_user.user_id,
            action=f"USER_UPDATED: ID {user_id} ({original_email} -> {user_update.user_email})",
            ip_address=request.client.host if request.client else "Unknown"
        )
        db.add(audit_log_update)
        
        db.commit()
        db.refresh(db_user)
        
        logger.info( f"사용자 정보 수정 성공: User ID {user_id} ({original_email} -> {user_update.user_email})")
        return db_user
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"사용자 수정 실패: {str(e)}", exc_info=True)
        raise DatabaseException("사용자 정보 수정 중 오류가 발생했습니다")

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    request: Request,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """사용자 삭제 (시스템 관리자만 가능)"""
    if current_user.role not in [models.UserRole.SYSTEM_ADMIN]:
        logger.warning(f"권한 없는 사용자 삭제 시도: {current_user.user_email}")
        raise AuthorizationException("사용자를 삭제할 권한이 없습니다")
    
    # 본인 삭제 방지
    if current_user.user_id == user_id:
        logger.warning(f"본인 계정 삭제 시도: {current_user.user_email}")
        raise ValidationException("자기 자신의 계정은 삭제할 수 없습니다")

    # 사용자 조회
    db_user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not db_user:
        logger.warning(f"존재하지 않는 사용자 삭제 시도: User ID {user_id}")
        raise NotFoundException("사용자를 찾을 수 없습니다")
    
    try:
        deleted_email = db_user.user_email
        
        db.delete(db_user)

        # 감사 로그
        audit_log = models.SystemAuditLog(
            actor_id=current_user.user_id,
            action=f"USER_DELETED: ID {user_id} ({deleted_email})",
            ip_address=request.client.host if request.client else "Unknown"
        )
        db.add(audit_log)

        db.commit()
        
        logger.info(f"사용자 삭제 성공: User ID {user_id} ({deleted_email})")
        return None
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"사용자 삭제 실패: {str(e)}", exc_info=True)
        raise DatabaseException("사용자 삭제 중 오류가 발생했습니다")
@router.post("/users/sync-entra")
def sync_users(
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """Microsoft Entra ID로부터 사용자 정보를 강제 동기화합니다 (시스템 관리자 전용)"""
    if current_user.role not in [models.UserRole.SYSTEM_ADMIN]:
        logger.warning(f"권한 없는 사용자 동기화 시도: {current_user.user_email}")
        raise AuthorizationException("사용자 정보를 동기화할 권한이 없습니다")
    
    try:
        result = services.sync_users_from_entra(db)
        return {
            "message": "사용자 정보 동기화가 성공적으로 완료되었습니다",
            "stats": result
        }
    except Exception as e:
        logger.error(f"사용자 동기화 실패: {str(e)}", exc_info=True)
        raise DatabaseException("사용자 동기화 중 오류가 발생했습니다")
