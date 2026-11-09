"""
환경 변수 및 애플리케이션 설정 관리
"""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
from pathlib import Path


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # 데이터베이스
    DATABASE_URL: str = "sqlite:///./sql_app.db"
    
    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS 설정
    CORS_ORIGINS: str = "http://localhost:5173"
    
    # 파일 업로드 설정
    ALLOWED_FILE_EXTENSIONS: str = ".pdf,.docx,.xlsx,.pptx,.txt,.png,.jpg,.jpeg,.gif"
    MAX_FILE_SIZE_MB: int = 10
    UPLOAD_DIR: str = "uploads"
    
    # 로깅 설정
    LOG_LEVEL: str = "INFO"
    
    # Microsoft Entra ID 공용 엔드포인트 (테넌트·앱 정보는 설치 후 관리자 화면에서 DB에 저장)
    # 국가별 클라우드 등 다른 엔드포인트가 필요할 때만 변경
    ENTRA_AUTHORITY_HOST: str = "https://login.microsoftonline.com"
    GRAPH_API_URL: str = "https://graph.microsoft.com"
    
    # 암호화 키
    ENCRYPTION_KEY: Optional[str] = None
    
    # 초기 관리자 정보
    INITIAL_ADMIN_EMAIL: str = "system@fleitlab.com"
    INITIAL_ADMIN_PASSWORD: str = "password123"
    
    # 이메일 전송 방식 (SMTP, OUTLOOK). OUTLOOK은 Entra 연동(관리자 화면)이 설정된 경우에만 동작
    MAIL_SENDER_TYPE: str = "SMTP"  # "SMTP" 또는 "OUTLOOK"
    
    # 이메일 (SMTP)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: str = "noreply@fleitlab.com"
    SMTP_FROM_NAME: str = "Fleit InsiderGuard"
    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    
    # 애플리케이션
    APP_NAME: str = "Fleit InsiderGuard - SICS"
    APP_VERSION: str = "2.1.0"
    APP_URL: Optional[str] = None  # 메일 본문 링크에 쓰는 프론트엔드 접속 주소 (미설정 시 CORS_ORIGINS 첫 주소)
    DEBUG: bool = False
    
    # 알림 및 자동화 설정
    ENABLE_EMAIL_NOTIFICATIONS: bool = True
    DEADLINE_REMINDER_DAYS: List[int] = [3, 1]  # 마감 3일 전, 1일 전

    # 보존기간: 종결(승인·반려·종결) 후 이 기간이 지나면 개인정보를 익명화 (증거 보존 지정 케이스 제외)
    CASE_RETENTION_DAYS: int = 1095  # 3년
    
    @property
    def frontend_url(self) -> str:
        """메일 링크용 프론트엔드 주소: APP_URL, 없으면 CORS_ORIGINS의 첫 주소"""
        url = self.APP_URL or self.CORS_ORIGINS.split(",")[0]
        return url.strip().rstrip("/")

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",  # 불필요한 환경 변수 무시
    )


# 싱글톤 인스턴스
settings = Settings()
