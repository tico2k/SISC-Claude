"""
로깅 설정
구조화된 로깅 시스템 구성
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging():
    """로깅 시스템 초기화"""
    
    # 로그 디렉토리 생성
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 환경 변수에서 로그 레벨 가져오기
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    
    # 로그 포맷 정의
    log_format = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # JSON 형식 로그 포맷 (프로덕션용)
    json_format = logging.Formatter(
        fmt='{"timestamp":"%(asctime)s","logger":"%(name)s","level":"%(levelname)s","message":"%(message)s"}',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Root logger 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 기존 핸들러 제거 (중복 방지)
    root_logger.handlers.clear()
    
    # 콘솔 핸들러 (개발 환경)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)
    
    # 파일 핸들러 - INFO 이상
    info_file_handler = RotatingFileHandler(
        filename=log_dir / "app.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    info_file_handler.setLevel(logging.INFO)
    info_file_handler.setFormatter(log_format)
    root_logger.addHandler(info_file_handler)
    
    # 파일 핸들러 - ERROR 이상
    error_file_handler = RotatingFileHandler(
        filename=log_dir / "error.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(log_format)
    root_logger.addHandler(error_file_handler)
    
    # 특정 라이브러리 로그 레벨 조정 (노이즈 감소)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    
    # 로깅 시스템 초기화 완료 로그
    root_logger.info(f"로깅 시스템 초기화 완료 (레벨: {log_level_str})")
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    이름으로 로거 가져오기
    
    Args:
        name: 로거 이름 (일반적으로 __name__ 사용)
    
    Returns:
        logging.Logger: 설정된 로거
    """
    return logging.getLogger(name)


# 민감 정보 마스킹 유틸리티
def mask_sensitive_data(data: str, mask_char: str = "*", visible_chars: int = 4) -> str:
    """
    민감 정보 마스킹
    
    Args:
        data: 마스킹할 데이터
        mask_char: 마스킹 문자
        visible_chars: 보이는 문자 수
    
    Returns:
        str: 마스킹된 문자열
    
    Example:
        >>> mask_sensitive_data("admin@example.com")
        'admi***************'
        >>> mask_sensitive_data("secret_password_123", visible_chars=3)
        'sec*****************'
    """
    if not data or len(data) <= visible_chars:
        return mask_char * len(data) if data else ""
    
    visible_part = data[:visible_chars]
    masked_part = mask_char * (len(data) - visible_chars)
    return visible_part + masked_part


def sanitize_log_data(data: dict) -> dict:
    """
    로그 데이터에서 민감 정보 제거/마스킹
    
    Args:
        data: 로깅할 딕셔너리 데이터
    
    Returns:
        dict: 민감 정보가 제거된 데이터
    """
    sensitive_keys = [
        'password', 'passwd', 'pwd', 'secret', 'token', 
        'api_key', 'apikey', 'access_token', 'refresh_token',
        'client_secret', 'private_key', 'hashed_password'
    ]
    
    sanitized = {}
    for key, value in data.items():
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_log_data(value)
        else:
            sanitized[key] = value
    
    return sanitized
