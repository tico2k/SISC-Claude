import os
import base64
from cryptography.fernet import Fernet
from fastapi import HTTPException
from dotenv import load_dotenv
from .logging_config import get_logger

load_dotenv()

logger = get_logger(__name__)

# 환경 변수에서 암호화 키 로드
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

def get_fernet():
    if not ENCRYPTION_KEY:
        # 키가 없을 경우 안내와 함께 에러 발생
        raise RuntimeError(
            "❌ ENCRYPTION_KEY 환경 변수가 설정되지 않았습니다. "
            "데이터를 암호화/복호화할 수 없습니다. "
            "생성 방법: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    try:
        return Fernet(ENCRYPTION_KEY.encode())
    except Exception as e:
        raise RuntimeError(f"❌ 유효하지 않은 ENCRYPTION_KEY입니다: {str(e)}")

class DecryptionError(Exception):
    """복호화 실패 (키 불일치 또는 데이터 손상). 상세 원인은 로그로만 남긴다."""


def encrypt_secret(plain_text: str) -> str:
    """텍스트를 암호화하여 Base64 문자열로 반환"""
    if not plain_text:
        return ""
    try:
        f = get_fernet()
        return f.encrypt(plain_text.encode()).decode()
    except Exception as e:
        logger.error(f"데이터 암호화 실패: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="데이터 암호화 중 오류가 발생했습니다. 서버 로그를 확인하세요.")

def decrypt_secret(encrypted_text: str) -> str:
    """암호화된 문자열을 복호화하여 원본 텍스트 반환

    Raises:
        DecryptionError: 복호화 실패 시. (이전에는 '[복호화 실패: ...]' 문자열을 반환해
            그 값이 실제 시크릿처럼 외부 SIEM에 전송되고 내부 오류가 노출되는 문제가 있었음)
    """
    if not encrypted_text:
        return ""
    try:
        f = get_fernet()
        return f.decrypt(encrypted_text.encode()).decode()
    except Exception as e:
        logger.error(f"데이터 복호화 실패: {type(e).__name__}")
        raise DecryptionError("저장된 값을 복호화할 수 없습니다. ENCRYPTION_KEY를 확인하세요.") from e
