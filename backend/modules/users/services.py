import secrets
import string
from sqlalchemy.orm import Session
from ... import models
from ..auth import entra_service
from ..integrations.services import get_entra_config
from ...core.dependencies import get_password_hash
from ...core.logging_config import get_logger
from ...core.exceptions import ValidationException

logger = get_logger(__name__)

def generate_random_password(length=32):
    """
    SSO 사용자를 위한 임의의 비밀번호 생성 (DB 제약 조건 충족용)
    """
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def sync_users_from_entra(db: Session):
    """
    Microsoft Entra ID 사용자를 가져와 로컬 DB와 동기화합니다.
    """
    logger.info("Starting user synchronization from Entra ID...")
    # 설정이 없거나 Graph 호출이 실패하면 ValidationException / ExternalServiceException 발생
    entra_users = entra_service.get_all_users(get_entra_config(db))
    
    if not entra_users:
        logger.warning("No users found in Entra ID to sync.")
        return {"total": 0, "created": 0, "updated": 0}

    created_count = 0
    updated_count = 0
    manager_links = []  # (직원 UPN, 부서장 UPN) — 모든 사용자를 만든 뒤 연결
    
    for eu in entra_users:
        email = eu.get("userPrincipalName")
        if not email:
            continue
        manager_upn = (eu.get("manager") or {}).get("userPrincipalName")
        if manager_upn:
            manager_links.append((email, manager_upn))
            
        # 3대 관리자 계정은 동기화 제외하거나 룰에 따라 처리
        # 여기서는 이메일이 일치하면 정보를 업데이트만 수행 (권한은 유지)
        db_user = db.query(models.User).filter(models.User.user_email == email).first()
        
        user_name = eu.get("displayName") or email.split('@')[0]
        company = eu.get("companyName") or "Fleit Lab"
        department = eu.get("department") or eu.get("jobTitle") or "일반"

        if db_user:
            # 업데이트 (기존 관리자 계정의 이름이나 부서 정보가 Entra ID와 다를 경우 갱신)
            db_user.user_name = user_name
            db_user.company = company
            db_user.department = department
            updated_count += 1
        else:
            # 신규 생성
            new_user = models.User(
                user_email=email,
                user_name=user_name,
                hashed_password=get_password_hash(generate_random_password()),
                company=company,
                department=department,
                role=models.UserRole.USER # 기본값은 '일반'
            )
            db.add(new_user)
            created_count += 1
            
    # 부서장 연결 (Entra의 manager → SICS 부서장). Entra에 manager가 없으면 기존 지정값 유지
    db.flush()
    managers_linked = 0
    for email, manager_upn in manager_links:
        employee = db.query(models.User).filter(models.User.user_email == email).first()
        manager = db.query(models.User).filter(models.User.user_email == manager_upn).first()
        if employee and manager and employee.user_id != manager.user_id:
            employee.manager_id = manager.user_id
            managers_linked += 1

    try:
        db.commit()
        logger.info(f"User sync completed. Created: {created_count}, Updated: {updated_count}, Managers: {managers_linked}")
        return {
            "total": len(entra_users),
            "created": created_count,
            "updated": updated_count,
            "managers_linked": managers_linked
        }
    except Exception as e:
        db.rollback()
        logger.error(f"User sync failed during DB commit: {e}")
        raise e


def validate_manager(db: Session, manager_id, user_id=None):
    """부서장 지정 검증: 존재하는 사용자이고 본인이 아니어야 함. None이면 해제"""
    if manager_id is None:
        return None
    if user_id is not None and manager_id == user_id:
        raise ValidationException("본인을 부서장으로 지정할 수 없습니다")
    if not db.get(models.User, manager_id):
        raise ValidationException("부서장으로 지정한 사용자를 찾을 수 없습니다")
    return manager_id
