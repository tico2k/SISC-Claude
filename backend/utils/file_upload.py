"""
파일 업로드 유틸리티 및 검증 함수
"""
import hashlib
import os
import uuid
import re
from pathlib import Path
from typing import Optional, List
from fastapi import UploadFile, HTTPException
from dotenv import load_dotenv

load_dotenv()

# 환경 변수에서 설정 로드
ALLOWED_EXTENSIONS_STR = os.getenv("ALLOWED_FILE_EXTENSIONS", ".pdf,.docx,.xlsx,.pptx,.txt,.png,.jpg,.jpeg,.gif")
ALLOWED_EXTENSIONS = set(ext.strip() for ext in ALLOWED_EXTENSIONS_STR.split(","))
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024  # MB to bytes

def sanitize_filename(filename: str) -> str:
    """
    파일명에서 위험한 문자 제거 및 안전한 파일명 생성
    
    Args:
        filename: 원본 파일명
        
    Returns:
        안전하게 처리된 파일명
    """
    # 파일명과 확장자 분리
    name, ext = os.path.splitext(filename)
    
    # 특수문자 제거 (알파벳, 숫자, 밑줄, 하이픈, 공백만 허용)
    name = re.sub(r'[^\w\s-]', '', name)
    
    # 연속된 공백을 하나로
    name = re.sub(r'\s+', '_', name)
    
    # 길이 제한 (최대 50자)
    name = name[:50]
    
    # UUID 추가하여 중복 방지
    unique_name = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
    
    return unique_name

def validate_file_extension(filename: str) -> bool:
    """
    파일 확장자가 허용된 목록에 있는지 검증
    
    Args:
        filename: 파일명
        
    Returns:
        허용된 확장자이면 True, 아니면 False
    """
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS

def validate_file_size(file_size: int) -> bool:
    """
    파일 크기가 허용 범위 내인지 검증
    
    Args:
        file_size: 파일 크기 (bytes)
        
    Returns:
        허용 범위 내이면 True, 아니면 False
    """
    return file_size <= MAX_FILE_SIZE_BYTES

async def validate_and_save_file(
    file: UploadFile,
    upload_dir: Path,
    allowed_extensions: Optional[set] = None,
    max_size_bytes: Optional[int] = None
) -> tuple[str, str, int, str]:
    """
    파일 검증 및 저장 (증거 무결성 검증용 SHA-256 해시를 함께 반환)
    
    Args:
        file: 업로드된 파일
        upload_dir: 저장 디렉토리
        allowed_extensions: 허용된 확장자 목록 (None이면 기본값 사용)
        max_size_bytes: 최대 파일 크기 (None이면 기본값 사용)
        
    Returns:
        (원본 파일명, 저장된 파일명, 파일 크기, SHA-256 hex) 튜플
        
    Raises:
        HTTPException: 검증 실패 시
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="파일명이 없습니다.")
    
    # 확장자 검증
    allowed_exts = allowed_extensions or ALLOWED_EXTENSIONS
    ext = os.path.splitext(file.filename)[1].lower()
    
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"허용되지 않는 파일 형식입니다. 허용된 확장자: {', '.join(sorted(allowed_exts))}"
        )
    
    # 파일 내용 읽기
    content = await file.read()
    file_size = len(content)
    
    # 파일 크기 검증
    max_size = max_size_bytes or MAX_FILE_SIZE_BYTES
    if file_size > max_size:
        max_mb = max_size / (1024 * 1024)
        raise HTTPException(
            status_code=400,
            detail=f"파일 크기가 너무 큽니다. 최대 크기: {max_mb:.1f}MB"
        )
    
    # 빈 파일 체크
    if file_size == 0:
        raise HTTPException(status_code=400, detail="빈 파일은 업로드할 수 없습니다.")
    
    # 디렉토리 생성
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # 안전한 파일명 생성
    safe_filename = sanitize_filename(file.filename)
    file_path = upload_dir / safe_filename
    
    # 파일 저장
    with open(file_path, "wb") as buffer:
        buffer.write(content)
    
    # 파일 포인터를 처음으로 되돌림 (재사용을 위해)
    await file.seek(0)
    
    return file.filename, safe_filename, file_size, hashlib.sha256(content).hexdigest()


def compute_file_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """저장된 파일의 SHA-256 (다운로드 시 무결성 검증용)"""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()

def get_allowed_extensions_list() -> List[str]:
    """
    허용된 파일 확장자 목록 반환
    
    Returns:
        허용된 확장자 리스트
    """
    return sorted(list(ALLOWED_EXTENSIONS))

def get_max_file_size_mb() -> int:
    """
    최대 파일 크기(MB) 반환
    
    Returns:
        최대 파일 크기 (MB)
    """
    return MAX_FILE_SIZE_MB
