"""
권한 관리 유틸리티

역할 기반 접근 제어(RBAC)를 위한 데코레이터 및 헬퍼 함수
"""

from functools import wraps
from typing import List, Callable
from fastapi import Depends, HTTPException
from ..models import User, UserRole
from .dependencies import get_current_user
from .exceptions import AuthorizationException
from .logging_config import get_logger

logger = get_logger(__name__)


def require_roles(*allowed_roles: UserRole):
    """
    역할 기반 권한 검증 데코레이터
    
    사용 예시:
        @router.get("/admin")
        @require_roles(UserRole.SYSTEM_ADMIN, UserRole.SECURITY_ADMIN)
        def admin_endpoint(current_user: User = Depends(get_current_user)):
            return {"message": "Admin access granted"}
    
    Args:
        *allowed_roles: 허용된 역할 목록 (UserRole enum)
    
    Returns:
        데코레이터 함수
    
    Raises:
        AuthorizationException: 사용자가 필요한 역할을 가지고 있지 않은 경우
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, current_user: User = Depends(get_current_user), **kwargs):
            if current_user.role not in allowed_roles:
                logger.warning(
                    f"권한 없는 접근 시도: User {current_user.user_email} "
                    f"(Role: {current_user.role}), Required: {allowed_roles}"
                )
                raise AuthorizationException(
                    f"이 작업을 수행할 권한이 없습니다. 필요한 역할: {', '.join([role.value for role in allowed_roles])}"
                )
            return await func(*args, current_user=current_user, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, current_user: User = Depends(get_current_user), **kwargs):
            if current_user.role not in allowed_roles:
                logger.warning(
                    f"권한 없는 접근 시도: User {current_user.user_email} "
                    f"(Role: {current_user.role}), Required: {allowed_roles}"
                )
                raise AuthorizationException(
                    f"이 작업을 수행할 권한이 없습니다. 필요한 역할: {', '.join([role.value for role in allowed_roles])}"
                )
            return func(*args, current_user=current_user, **kwargs)
        
        # async 함수인지 확인
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def is_admin(user: User) -> bool:
    """
    사용자가 관리자 권한을 가지고 있는지 확인
    
    Args:
        user: 확인할 사용자 객체
    
    Returns:
        관리자 여부 (True/False)
    """
    return user.role in [UserRole.SYSTEM_ADMIN, UserRole.SECURITY_ADMIN]


def is_security_admin(user: User) -> bool:
    """
    사용자가 보안 관리자 권한을 가지고 있는지 확인
    
    Args:
        user: 확인할 사용자 객체
    
    Returns:
        보안 관리자 여부 (True/False)
    """
    return user.role == UserRole.SECURITY_ADMIN


def is_system_admin(user: User) -> bool:
    """
    사용자가 시스템 관리자 권한을 가지고 있는지 확인
    
    Args:
        user: 확인할 사용자 객체
    
    Returns:
        시스템 관리자 여부 (True/False)
    """
    return user.role == UserRole.SYSTEM_ADMIN


def is_audit_team(user: User) -> bool:
    """
    사용자가 감사팀 권한을 가지고 있는지 확인
    
    Args:
        user: 확인할 사용자 객체
    
    Returns:
        감사팀 여부 (True/False)
    """
    return user.role == UserRole.AUDIT_TEAM


def can_review_cases(user: User) -> bool:
    """
    사용자가 케이스를 검토할 수 있는지 확인
    
    Args:
        user: 확인할 사용자 객체
    
    Returns:
        케이스 검토 권한 여부 (True/False)
    """
    return user.role in [UserRole.SECURITY_ADMIN, UserRole.AUDIT_TEAM, UserRole.SYSTEM_ADMIN]


def can_manage_users(user: User) -> bool:
    """
    사용자가 다른 사용자를 관리할 수 있는지 확인
    
    Args:
        user: 확인할 사용자 객체
    
    Returns:
        사용자 관리 권한 여부 (True/False)
    """
    return user.role == UserRole.SYSTEM_ADMIN


def can_configure_siem(user: User) -> bool:
    """
    사용자가 SIEM 설정을 관리할 수 있는지 확인
    
    Args:
        user: 확인할 사용자 객체
    
    Returns:
        SIEM 설정 권한 여부 (True/False)
    """
    return user.role in [UserRole.SECURITY_ADMIN, UserRole.SYSTEM_ADMIN]


def can_access_audit_logs(user: User) -> bool:
    """
    사용자가 감사 로그에 접근할 수 있는지 확인
    
    Args:
        user: 확인할 사용자 객체
    
    Returns:
        감사 로그 접근 권한 여부 (True/False)
    """
    return user.role in [UserRole.SYSTEM_ADMIN, UserRole.SECURITY_ADMIN, UserRole.AUDIT_TEAM]


def can_access_case(user: User, case_owner_id: int) -> bool:
    """
    사용자가 특정 케이스에 접근할 수 있는지 확인
    
    Args:
        user: 확인할 사용자 객체
        case_owner_id: 케이스 소유자 ID
    
    Returns:
        케이스 접근 권한 여부 (True/False)
    """
    # 관리자이거나 본인의 케이스인 경우
    return can_review_cases(user) or user.user_id == case_owner_id
