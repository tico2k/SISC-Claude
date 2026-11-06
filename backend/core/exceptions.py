"""
커스텀 예외 클래스 정의
API 에러 응답을 일관되게 처리하기 위한 예외 클래스들
"""

from typing import Any, Optional
from fastapi import HTTPException, status


class BaseAPIException(HTTPException):
    """기본 API 예외 클래스"""
    
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: Optional[str] = None,
        headers: Optional[dict] = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code


class AuthenticationException(BaseAPIException):
    """인증 실패 예외"""
    
    def __init__(self, detail: str = "인증에 실패했습니다"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code="AUTH_FAILED",
            headers={"WWW-Authenticate": "Bearer"}
        )


class AuthorizationException(BaseAPIException):
    """권한 부족 예외"""
    
    def __init__(self, detail: str = "권한이 없습니다"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code="FORBIDDEN"
        )


class NotFoundException(BaseAPIException):
    """리소스를 찾을 수 없음"""
    
    def __init__(self, resource: str = "리소스", detail: Optional[str] = None):
        if detail is None:
            detail = f"{resource}를 찾을 수 없습니다"
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            error_code="NOT_FOUND"
        )


class ValidationException(BaseAPIException):
    """데이터 검증 실패"""
    
    def __init__(self, detail: str = "입력 데이터가 올바르지 않습니다"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_code="VALIDATION_ERROR"
        )


class DuplicateException(BaseAPIException):
    """중복 데이터 예외"""
    
    def __init__(self, resource: str = "데이터", detail: Optional[str] = None):
        if detail is None:
            detail = f"이미 존재하는 {resource}입니다"
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_code="DUPLICATE"
        )


class FileUploadException(BaseAPIException):
    """파일 업로드 실패 예외"""
    
    def __init__(self, detail: str = "파일 업로드에 실패했습니다"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code="FILE_UPLOAD_ERROR"
        )


class DatabaseException(BaseAPIException):
    """데이터베이스 오류"""
    
    def __init__(self, detail: str = "데이터베이스 처리 중 오류가 발생했습니다"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code="DATABASE_ERROR"
        )


class ExternalServiceException(BaseAPIException):
    """외부 서비스 연동 오류"""
    
    def __init__(self, service: str = "외부 서비스", detail: Optional[str] = None):
        if detail is None:
            detail = f"{service} 연동 중 오류가 발생했습니다"
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
            error_code="EXTERNAL_SERVICE_ERROR"
        )


class CaseStateException(BaseAPIException):
    """케이스 현재 상태에서 허용되지 않는 작업(잘못된 상태 전이, 다른 관리자의 잠금 등)"""

    def __init__(self, detail: str = "현재 케이스 상태에서 수행할 수 없는 작업입니다"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_code="CASE_STATE_CONFLICT"
        )
