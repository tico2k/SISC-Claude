import re
from fastapi import APIRouter, Depends, status, Request, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from ... import models, schemas
from ...core import dependencies
from ...core.database import get_db
from ...seed_data import clear_data, generate_sample_data
from ...core.exceptions import AuthorizationException, ValidationException
from ...core.logging_config import get_logger
import csv
import json
import codecs
from io import StringIO
import os
from pathlib import Path
from typing import List, Optional

logger = get_logger(__name__)
router = APIRouter(
    prefix="/system",
    tags=["System Management"]
)

@router.post("/reset", status_code=status.HTTP_200_OK)
def reset_database(
    request: Request,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """
    데이터베이스 초기화 (시스템 관리자 전용)
    - 기존 케이스 및 관련 데이터를 모두 삭제합니다.
    - 사용자 계정과 설정은 유지됩니다.
    """
    # 1. 권한 확인
    if current_user.role != models.UserRole.SYSTEM_ADMIN:
        logger.warning(f"권한 없는 데이터베이스 초기화 시도: {current_user.user_email}")
        raise AuthorizationException("시스템 초기화 권한이 없습니다.")

    logger.info(f"데이터베이스 초기화(삭제) 시작: Requested by {current_user.user_email}")

    try:

        clear_data(db=db)
        
        audit_log = models.SystemAuditLog(
            actor_id=current_user.user_id,
            action="SYSTEM_RESET: All cases and related data deleted",
            ip_address=request.client.host if request.client else "Unknown"
        )
        db.add(audit_log)
        db.commit()
        
        logger.info("데이터베이스 초기화 완료")
        return {"message": "Database reset successfully", "status": "completed"}

    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {str(e)}", exc_info=True)
        raise e

@router.post("/seed", status_code=status.HTTP_200_OK)
def seed_database(
    request: Request,
    target_cases: int = Query(200, ge=10, le=1000, description="생성할 샘플 케이스 수 (기본: 200건)"),
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """
    샘플 데이터 및 대시보드 지표 생성 (시스템 관리자 전용)
    - 최신 프로세스(미확인, 요청, 제출, 승인, 반려 3종, 종결)에 맞춘 케이스를 지정된 건수(기본 200건)만큼 생성합니다.
    - 대시보드의 '최근 일일 소명 및 검토 추이' 및 '주간 보안 보고서' 데이터를 즉시 동기화합니다.
    """
    # 1. 권한 확인
    if current_user.role != models.UserRole.SYSTEM_ADMIN:
        logger.warning(f"권한 없는 샘플 데이터 생성 시도: {current_user.user_email}")
        raise AuthorizationException("샘플 데이터 생성 권한이 없습니다.")

    logger.info(f"샘플 데이터 생성 시작 (목표: {target_cases}건): Requested by {current_user.user_email}")

    try:
        total_cases = generate_sample_data(db=db, target_total_cases=target_cases)
        
        audit_log = models.SystemAuditLog(
            actor_id=current_user.user_id,
            action=f"SYSTEM_SEED: {total_cases} sample cases and dashboard metrics generated",
            ip_address=request.client.host if request.client else "Unknown"
        )
        db.add(audit_log)
        db.commit()
        
        logger.info(f"샘플 데이터 및 대시보드 지표 생성 완료 (총 {total_cases}건)")
        return {
            "message": f"샘플 케이스 {total_cases}건 생성 및 대시보드 지표(일일 추이 및 주간 보고서) 동기화 완료",
            "cases_count": total_cases,
            "status": "completed"
        }

    except Exception as e:
        logger.error(f"샘플 데이터 생성 실패: {str(e)}", exc_info=True)
        raise e

@router.post("/users/upload", status_code=status.HTTP_200_OK)
async def upload_users(
    file: UploadFile = File(...),
    format: str = Form("auto"), # auto, csv, json
    request: Request = None,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """
    사용자 일괄 업로드 (CSV/JSON)
    - 시스템 관리자 전용
    - 이메일 중복 시 건너뜀
    - 비밀번호는 평문으로 입력받아 해시 처리
    """
    
    # 1. 권한 확인
    if current_user.role != models.UserRole.SYSTEM_ADMIN:
        logger.warning(f"권한 없는 사용자 업로드 시도: {current_user.user_email}")
        raise AuthorizationException("사용자 업로드 권한이 없습니다.")

    logger.info(f"사용자 일괄 업로드 시작: Requested by {current_user.user_email}, File: {file.filename}, Format: {format}")

    # 2. 파일 포맷 결정
    file_ext = file.filename.split(".")[-1].lower()
    if format == "auto":
        if file_ext == "csv":
            parse_format = "csv"
        elif file_ext == "json":
            parse_format = "json"
        else:
            raise ValidationException("지원하지 않는 파일 형식입니다. (CSV 또는 JSON)")
    else:
        parse_format = format.lower()
        if parse_format not in ["csv", "json"]:
             raise ValidationException("잘못된 포맷 지정입니다. (csv, json, auto)")

    # 3. 파일 파싱 및 사용자 데이터 추출
    users_to_create = []
    
    try:
        content = await file.read()
        
        if parse_format == "json":
            try:
                data = json.loads(content)
                if not isinstance(data, list):
                    raise ValidationException("JSON 데이터는 객체 배열(List)이어야 합니다.")
                users_to_create = data
            except json.JSONDecodeError:
                raise ValidationException("유효하지 않은 JSON 파일입니다.")
                
        elif parse_format == "csv":
            try:
                # Decode bytes to string
                decoded_content = content.decode("utf-8-sig")
                csv_reader = csv.DictReader(StringIO(decoded_content))
                
                # Check header
                if not csv_reader.fieldnames:
                     raise ValidationException("CSV 파일이 비어있거나 헤더를 읽을 수 없습니다.")
                
                # Normalize headers (remove quotes if any, strip spaces)
                # But CSV DictReader usually handles standard CSV.
                # Let's map headers to expected keys if needed, or assume they match schema.
                
                for row in csv_reader:
                    users_to_create.append(row)
            except Exception as e:
                logger.error(f"CSV 파싱 오류: {e}")
                raise ValidationException(f"CSV 파싱 중 오류가 발생했습니다: {str(e)}")

    except Exception as e:
         logger.error(f"파일 읽기 오류: {e}")
         raise ValidationException(f"파일을 읽는 중 오류가 발생했습니다: {str(e)}")

    # 4. 사용자 생성 루프
    stats = {
        "total": len(users_to_create),
        "created": 0,
        "skipped": 0,
        "errors": 0,
        "details": []
    }

    for user_data in users_to_create:
        try:
            # 필수 필드 매핑 및 검증
            email = user_data.get("user_email")
            name = user_data.get("user_name")
            password = user_data.get("password")
            role = user_data.get("role")
            
            if not all([email, name, password, role]):
                stats["errors"] += 1
                stats["details"].append(f"Missing required fields for row: {user_data}")
                continue

            # 이메일 중복 확인
            existing_user = db.query(models.User).filter(models.User.user_email == email).first()
            if existing_user:
                stats["skipped"] += 1
                stats["details"].append(f"Skipped duplicate email: {email}")
                continue

            # Role 매핑 (한글 -> Enum)
            # csv/json might contain "일반", "보안관리자" etc. OR "USER", "SECURITY_ADMIN"
            # Try to map string to Enum
            role_enum = None
            
            # 1. Try matching Enum value (Korean)
            for r in models.UserRole:
                if r.value == role:
                    role_enum = r
                    break
            
            # 2. Try matching Enum name (English)
            if not role_enum:
                try:
                    role_enum = models.UserRole[role]
                except KeyError:
                    pass
            
            # Default to USER if map failed? Or Error? Let's Error for safety.
            if not role_enum:
                # Fallback: if input is "감사팀" it matches value.
                # Let's assume input matches exactly either name or value.
                stats["errors"] += 1
                stats["details"].append(f"Invalid role for {email}: {role}")
                continue

            # User Create
            hashed_pw = dependencies.get_password_hash(password)
            new_user = models.User(
                user_email=email,
                user_name=name,
                hashed_password=hashed_pw,
                company=user_data.get("company"),
                department=user_data.get("department"),
                role=role_enum
            )
            db.add(new_user)
            stats["created"] += 1
            
        except Exception as e:
            stats["errors"] += 1
            stats["details"].append(f"Error creating user {user_data.get('user_email', 'Unknown')}: {str(e)}")

    # 5. 커밋 및 감사 로그
    try:
        db.commit()
        
        audit_log = models.SystemAuditLog(
            actor_id=current_user.user_id,
            action=f"BULK_USER_UPLOAD: Total {stats['total']}, Created {stats['created']}, Skipped {stats['skipped']}",
            ip_address=request.client.host if request.client else "Unknown"
        )
        db.add(audit_log)
        db.commit()
        
        logger.info(f"사용자 일괄 업로드 완료: {stats}")
        return {"message": "Bulk upload processed", "stats": stats}
        
    except Exception as e:
        db.rollback()
        logger.error(f"DB 커밋 실패: {e}")
        raise ValidationException("데이터베이스 저장 중 오류가 발생했습니다.")


# --- Environment Variable Management ---

# "KEY": ENCRYPTION_KEY·SECRET_KEY 등 / "DATABASE_URL": PostgreSQL 접속 URL에 비밀번호 포함 가능
SENSITIVE_KEYWORDS = ["SECRET", "PASSWORD", "API_KEY", "CLIENT_SECRET", "TOKEN", "KEY", "DATABASE_URL"]
ENV_KEY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# 관리 대상 .env 파일 경로 (프로젝트 루트 기준, 테스트에서 교체 가능)
BACKEND_ENV_PATH = Path(".env")
FRONTEND_ENV_PATH = Path("frontend/.env")

ENV_METADATA = {
    # [1] 데이터베이스 설정
    "DATABASE_URL": {"category": "[1] 데이터베이스 설정", "description": "데이터베이스 접속 경로 (SQLite/PostgreSQL)"},
    
    # [2] 인증 및 보안 설정
    "SECRET_KEY": {"category": "[2] 인증 및 보안 설정", "description": "JWT 토큰 서명 및 보안 암호화용 시크릿 키"},
    "ACCESS_TOKEN_EXPIRE_MINUTES": {"category": "[2] 인증 및 보안 설정", "description": "JWT 토큰 만료 시간 (단위: 분)"},
    "ENCRYPTION_KEY": {"category": "[2] 인증 및 보안 설정", "description": "데이터 암호화 키 (로그/시크릿 보관용)"},
    
    # [3] CORS 설정
    "CORS_ORIGINS": {"category": "[3] CORS 설정", "description": "CORS 허용 도메인 목록 (쉼표 구분)"},
    
    # [4] 파일 업로드 설정
    "ALLOWED_FILE_EXTENSIONS": {"category": "[4] 파일 업로드 설정", "description": "업로드 허가 파일 확장자 (점 포함, 쉼표 구분)"},
    "MAX_FILE_SIZE_MB": {"category": "[4] 파일 업로드 설정", "description": "단일 파일 최대 업로드 크기 (단위: MB)"},
    "UPLOAD_DIR": {"category": "[4] 파일 업로드 설정", "description": "업로드된 파일이 저장될 디렉토리 경로"},
    
    # [6] 이메일 알림 설정
    "ENABLE_EMAIL_NOTIFICATIONS": {"category": "[6] 이메일 알림 설정", "description": "이메일 알림 기능 활성화 여부 (true/false)"},
    "MAIL_SENDER_TYPE": {"category": "[6] 이메일 알림 설정", "description": "이메일 전송 방식 (SMTP 또는 OUTLOOK, OUTLOOK은 연동 설정에서 Entra 구성 필요)"},
    
    # [7] 애플리케이션 및 로깅
    "APP_NAME": {"category": "[7] 애플리케이션 및 로깅", "description": "애플리케이션 명칭 (SICS)"},
    "APP_URL": {"category": "[7] 애플리케이션 및 로깅", "description": "메일 링크에 쓰는 프론트엔드 접속 주소"},
    "LOG_LEVEL": {"category": "[7] 애플리케이션 및 로깅", "description": "로그 기록 수준 (DEBUG, INFO, WARNING, ERROR)"},
    "DEBUG": {"category": "[7] 애플리케이션 및 로깅", "description": "디버그 모드 활성화 여부"},
    
    # [8] 초기 관리자 계정 생성 정보
    "INITIAL_ADMIN_EMAIL": {"category": "[8] 초기 관리자 계정 생성 정보", "description": "최초 설치 시 생성될 관리자 이메일"},
    "INITIAL_ADMIN_PASSWORD": {"category": "[8] 초기 관리자 계정 생성 정보", "description": "최초 설치 시 생성될 관리자 비밀번호"},

    # Email Details (Internal)
    "SMTP_HOST": {"category": "Email (SMTP 상세)", "description": "이메일 발송용 SMTP 호스트 주소"},
    "SMTP_PORT": {"category": "Email (SMTP 상세)", "description": "이메일 발송용 SMTP 포트 번호"},
    "SMTP_USER": {"category": "Email (SMTP 상세)", "description": "SMTP 인증 사용자 계정"},
    "SMTP_PASSWORD": {"category": "Email (SMTP 상세)", "description": "SMTP 인증 비밀번호"},
    "SMTP_FROM_EMAIL": {"category": "Email (SMTP 상세)", "description": "발신용 이메일 주소"},
    "SMTP_FROM_NAME": {"category": "Email (SMTP 상세)", "description": "발신인 표시 이름"},
    
    # Frontend
    "VITE_API_URL": {"category": "Network (Frontend)", "description": "프론트엔드에서 바라볼 API 서버 주소"},
    # Entra ID·Sentinel 연동 정보는 .env가 아니라 관리자 화면(연동 설정 / SIEM 연동)에서 DB에 저장한다
}

def is_key_sensitive(key: str) -> bool:
    return any(keyword in key.upper() for keyword in SENSITIVE_KEYWORDS)

def mask_value(value: str) -> str:
    """민감값은 앞뒤 글자도 노출하지 않고 고정 마스크로 반환"""
    if not value:
        return ""
    return "********"

def parse_env_file(file_path: Path):
    entries = []
    if not file_path.exists():
        return entries
    
    current_category = "General"
    current_description = ""
    
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            
            # 주석 파싱 (카테고리 또는 설명 추출)
            if line.startswith("#"):
                comment = line[1:].strip()
                if not comment:
                    continue
                
                # '[n] 카테고리명' 패턴 감지하여 카테고리 갱신
                if comment.startswith("[") and "]" in comment:
                    # 카테고리 갱신 시 누적되었던 설명은 초기화
                    current_category = comment
                    current_description = ""
                else:
                    # 일반 주석은 설명으로 누적
                    if current_description:
                        current_description += " " + comment
                    else:
                        current_description = comment
                continue
            
            if not line:
                # 빈 줄이면 설명 초기화 (단, 카테고리는 유지)
                current_description = ""
                continue
                
            if "=" in line:
                key, value = line.split("=", 1)
                is_sensitive = is_key_sensitive(key)
                
                # 사전 정의된 메타데이터 사용
                meta = ENV_METADATA.get(key, {})
                category = meta.get("category", current_category)
                
                # 설명 결정: 메타데이터 우선 -> 없으면 주석에서 파싱한 설명 사용
                description = meta.get("description", current_description)
                
                entries.append(schemas.EnvEntry(
                    key=key,
                    value=mask_value(value) if is_sensitive else value,
                    is_sensitive=is_sensitive,
                    category=category,
                    description=description
                ))
                # 변수를 만나면 설명 초기화 (카테고리는 다음 주석을 만날 때까지 유지)
                current_description = ""
                
    return entries

@router.get("/env", response_model=schemas.EnvResponse)
def get_env(
    current_user: models.User = Depends(dependencies.get_current_user)
):
    """실행 환경 변수 조회 (관리자 전용)"""
    if current_user.role not in [models.UserRole.SYSTEM_ADMIN, models.UserRole.SECURITY_ADMIN]:
        raise AuthorizationException("설정 조회 권한이 없습니다.")
    
    backend_env = BACKEND_ENV_PATH
    frontend_env = FRONTEND_ENV_PATH
    
    return schemas.EnvResponse(
        backend=parse_env_file(backend_env),
        frontend=parse_env_file(frontend_env)
    )

@router.post("/env", status_code=status.HTTP_200_OK)
def update_env(
    request: schemas.EnvUpdateRequest,
    current_request: Request,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """환경 변수 업데이트 (시스템 관리자 전용)"""
    if current_user.role != models.UserRole.SYSTEM_ADMIN:
        raise AuthorizationException("설정 변경 권한이 없습니다.")
    
    file_path = BACKEND_ENV_PATH if request.file_type == "backend" else FRONTEND_ENV_PATH
    
    if not file_path.exists():
        raise ValidationException(f"파일을 찾을 수 없습니다: {file_path}")
    
    # 안전 점검: 키는 영문/숫자/밑줄만 허용
    if not ENV_KEY_PATTERN.match(request.key):
        raise ValidationException("유효하지 않은 키 이름입니다.")
        
    # 값(value)에 줄바꿈 문자가 포함되어 있는지 확인 (인젝션 방지)
    if "\n" in request.value or "\r" in request.value:
        raise ValidationException("값에 줄바꿈 문자를 포함할 수 없습니다.")

    try:
        lines = []
        key_found = False
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith(f"{request.key}="):
                    lines.append(f"{request.key}={request.value}\n")
                    key_found = True
                else:
                    lines.append(line)
        
        if not key_found:
            # 웹 UI는 기존 키 수정만 지원. 임의의 새 키 추가는 차단
            raise ValidationException(f"존재하지 않는 키입니다: {request.key}")
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
            
        # 감사 로그 기록
        audit_log = models.SystemAuditLog(
            actor_id=current_user.user_id,
            action=f"ENV_UPDATE: {request.file_type} - {request.key}",
            ip_address=current_request.client.host if current_request.client else "Unknown"
        )
        db.add(audit_log)
        db.commit()
        
        logger.info(f"환경 변수 업데이트 완료: {request.file_type} {request.key} by {current_user.user_email}")
        return {"message": f"Successfully updated {request.key}"}
        
    except ValidationException:
        raise
    except Exception as e:
        logger.error(f"환경 변수 업데이트 실패: {str(e)}", exc_info=True)
        raise ValidationException("환경 변수 업데이트 중 오류가 발생했습니다. 서버 로그를 확인하세요.")

# --- Background Job Management ---
from ...core.scheduler import scheduler
from typing import List

@router.get("/jobs", response_model=List[schemas.JobResponse])
def get_jobs(
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """백그라운드 스케줄 작업 목록 조회 (관리자 전용)"""
    if current_user.role != models.UserRole.SYSTEM_ADMIN:
        raise AuthorizationException("작업 조회 권한이 없습니다.")
    
    # 1. DB에서 모든 설정값 로드 (목록의 기준)
    system_configs = db.query(models.SystemJobConfiguration).all()
    siem_configs = db.query(models.SiemConfiguration).all()
    
    # 2. 현재 스케줄러 상태 맵핑
    scheduler_jobs = {job.id: job for job in scheduler.get_jobs()}
    
    jobs = []
    
    # 시스템 작업 추가
    for config in system_configs:
        job = scheduler_jobs.get(config.job_id)
        jobs.append({
            "id": config.job_id,
            "name": config.job_name,
            "next_run_time": job.next_run_time if job else None,
            "status": "RUNNING" if job and job.next_run_time else "PAUSED",
            "cron_expression": config.cron_expression
        })
        
    # SIEM 동기화 작업 추가
    for siem in siem_configs:
        job_id = f"sync_siem_logs_{siem.siem_id}"
        job = scheduler_jobs.get(job_id)
        jobs.append({
            "id": job_id,
            "name": f"SIEM Sync: {siem.name}",
            "next_run_time": job.next_run_time if job else None,
            "status": "RUNNING" if job and job.next_run_time else "PAUSED",
            "cron_expression": siem.cron_expression or "*/30 * * * *"
        })
        
    return jobs

@router.post("/jobs/{job_id}/pause", status_code=status.HTTP_200_OK)
def pause_job(
    job_id: str,
    request: Request,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """특정 작업 일시 정지 (관리자 전용)"""
    if current_user.role != models.UserRole.SYSTEM_ADMIN:
        raise AuthorizationException("작업 제어 권한이 없습니다.")
    
    # 스케줄러에서 중지/제거
    job = scheduler.get_job(job_id)
    if job:
        job.pause()
    
    # DB 상태 업데이트
    if job_id.startswith("sync_siem_logs_"):
        siem_id = int(job_id.split("_")[-1])
        siem = db.query(models.SiemConfiguration).filter(models.SiemConfiguration.siem_id == siem_id).first()
        if siem:
            siem.is_active = False
    else:
        config = db.query(models.SystemJobConfiguration).filter(models.SystemJobConfiguration.job_id == job_id).first()
        if config:
            config.is_active = False
    
    audit_log = models.SystemAuditLog(
        actor_id=current_user.user_id,
        action=f"JOB_PAUSE: {job_id}",
        ip_address=request.client.host if request.client else "Unknown"
    )
    db.add(audit_log)
    db.commit()
    
    return {"message": f"작업 '{job_id}'가 일시 정지 및 비활성화되었습니다."}

@router.post("/jobs/{job_id}/resume", status_code=status.HTTP_200_OK)
def resume_job(
    job_id: str,
    request: Request,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """특정 작업 재개 (관리자 전용)"""
    if current_user.role != models.UserRole.SYSTEM_ADMIN:
        raise AuthorizationException("작업 제어 권한이 없습니다.")
    
    # 1. DB 상태 업데이트 및 설정 로드
    cron_expr = None
    if job_id.startswith("sync_siem_logs_"):
        siem_id = int(job_id.split("_")[-1])
        siem = db.query(models.SiemConfiguration).filter(models.SiemConfiguration.siem_id == siem_id).first()
        if siem:
            siem.is_active = True
            cron_expr = siem.cron_expression or "*/30 * * * *"
    else:
        config = db.query(models.SystemJobConfiguration).filter(models.SystemJobConfiguration.job_id == job_id).first()
        if config:
            config.is_active = True
            cron_expr = config.cron_expression

    # 2. 스케줄러 반영
    job = scheduler.get_job(job_id)
    if job:
        job.resume()
    else:
        # 작업이 스케줄러에 없는 경우(서버 시작 시 비활성이었으면 등록 안 됨) 새로 등록
        from ...core.scheduler import CronTrigger
        from ...tasks import batch_tasks, siem_tasks
        
        if job_id.startswith("sync_siem_logs_"):
            siem_id = int(job_id.split("_")[-1])
            scheduler.add_job(
                siem_tasks.sync_siem_logs,
                CronTrigger.from_crontab(cron_expr),
                id=job_id,
                args=[siem_id],
                replace_existing=True
            )
        else:
            # 시스템 작업 매핑
            system_funcs = {
                "send_deadline_reminders": batch_tasks.send_deadline_reminders,
                "generate_daily_statistics": batch_tasks.generate_daily_statistics,
                "generate_weekly_report": batch_tasks.generate_weekly_report,
                "archive_old_cases": batch_tasks.archive_old_cases,
            }
            if job_id in system_funcs:
                scheduler.add_job(
                    system_funcs[job_id],
                    CronTrigger.from_crontab(cron_expr),
                    id=job_id,
                    replace_existing=True
                )

    audit_log = models.SystemAuditLog(
        actor_id=current_user.user_id,
        action=f"JOB_RESUME: {job_id}",
        ip_address=request.client.host if request.client else "Unknown"
    )
    db.add(audit_log)
    db.commit()
    
    return {"message": f"작업 '{job_id}'가 재개 및 활성화되었습니다."}

    return {"message": f"작업 '{job_id}'를 백그라운드로 1회 수동 실행 완료했습니다."}

@router.post("/jobs/{job_id}/reschedule", status_code=status.HTTP_200_OK)
def reschedule_job(
    job_id: str,
    payload: schemas.JobRescheduleRequest,
    request: Request,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """특정 작업의 실행 주기(Cron) 변경 (관리자 전용)"""
    if current_user.role != models.UserRole.SYSTEM_ADMIN:
        raise AuthorizationException("작업 제어 권한이 없습니다.")
    
    # 1. DB 업데이트
    if job_id.startswith("sync_siem_logs_"):
        try:
            siem_id = int(job_id.split("_")[-1])
            siem = db.query(models.SiemConfiguration).filter(models.SiemConfiguration.siem_id == siem_id).first()
            if not siem:
                raise ValidationException(f"SIEM 설정을 찾을 수 없습니다: {siem_id}")
            siem.cron_expression = payload.cron_expression
        except ValueError:
            raise ValidationException(f"유효하지 않은 작업 ID 형식입니다: {job_id}")
    else:
        config = db.query(models.SystemJobConfiguration).filter(models.SystemJobConfiguration.job_id == job_id).first()
        if not config:
            raise ValidationException(f"시스템 작업을 찾을 수 없습니다: {job_id}")
        config.cron_expression = payload.cron_expression
    
    # 2. 스케줄러 즉시 반영
    from ...core.scheduler import reschedule_job as aps_reschedule
    success = aps_reschedule(job_id, payload.cron_expression)
    
    if not success:
        db.rollback()
        raise ValidationException("스케줄러 반영에 실패했습니다. Cron 표현식을 확인하세요.")
    
    # 3. 감사 로그기록
    db.commit()
    audit_log = models.SystemAuditLog(
        actor_id=current_user.user_id,
        action=f"JOB_RESCHEDULE: {job_id} -> {payload.cron_expression}",
        ip_address=request.client.host if request.client else "Unknown"
    )
    db.add(audit_log)
    db.commit()
    
    return {"message": f"작업 '{job_id}'의 스케줄이 '{payload.cron_expression}'으로 변경되었습니다."}

@router.get("/jobs/logs", response_model=List[schemas.BackgroundJobLogResponse])
def get_job_logs(
    job_id: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    """백그라운드 작업 로그 조회 (관리자 전용)"""
    if current_user.role not in [models.UserRole.SYSTEM_ADMIN, models.UserRole.SECURITY_ADMIN]:
        raise AuthorizationException("로그 조회 권한이 없습니다.")
    
    query = db.query(models.BackgroundJobLog)
    if job_id and job_id != "all":
        query = query.filter(models.BackgroundJobLog.job_id == job_id)
    
    return query.order_by(models.BackgroundJobLog.execution_time.desc()).limit(limit).all()

@router.get("/jobs/log-filters")
def get_job_log_filters(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    """로그 필터링을 위한 작업 ID/명칭 목록 조회 (로그 존재 기준)"""
    if current_user.role not in [models.UserRole.SYSTEM_ADMIN, models.UserRole.SECURITY_ADMIN]:
        raise AuthorizationException("필터 조회 권한이 없습니다.")
    
    # BackgroundJobLog 테이블에서 실제 기록된 작업들의 고유 ID와 명칭을 가져옴
    results = db.query(
        models.BackgroundJobLog.job_id, 
        models.BackgroundJobLog.job_name
    ).distinct().all()
    
    return [{"job_id": r[0], "job_name": r[1]} for r in results]

# --- Menu Permission Endpoints ---

@router.get("/permissions", response_model=List[schemas.MenuPermissionResponse])
def get_menu_permissions(
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """역할별 메뉴 권한 목록 조회 (관리자 또는 메뉴 권한 보유자)"""
    has_permission = (
        current_user.role in [models.UserRole.SYSTEM_ADMIN, models.UserRole.SECURITY_ADMIN] or
        db.query(models.MenuPermission).filter(
            models.MenuPermission.role == current_user.role,
            models.MenuPermission.menu_path == "/permissions",
            models.MenuPermission.is_visible == True
        ).first() is not None
    )
    if not has_permission:
        raise AuthorizationException("권한 조회 권한이 없습니다.")
    
    return db.query(models.MenuPermission).all()

@router.post("/permissions/bulk-update")
def update_menu_permissions(
    payload: List[schemas.MenuPermissionResponse],
    request: Request = None,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """메뉴 권한 대량 업데이트 (관리자 또는 메뉴 권한 보유자)"""
    has_permission = (
        current_user.role in [models.UserRole.SYSTEM_ADMIN, models.UserRole.SECURITY_ADMIN] or
        db.query(models.MenuPermission).filter(
            models.MenuPermission.role == current_user.role,
            models.MenuPermission.menu_path == "/permissions",
            models.MenuPermission.is_visible == True
        ).first() is not None
    )
    if not has_permission:
        raise AuthorizationException("권한 수정 권한이 없습니다.")
    
    for item in payload:
        perm = db.query(models.MenuPermission).filter(models.MenuPermission.permission_id == item.permission_id).first()
        if perm:
            perm.is_visible = item.is_visible
    
    db.commit()
    
    # 감사 로그
    client_ip = request.client.host if request and request.client else "Internal"
    audit_log = models.SystemAuditLog(
        actor_id=current_user.user_id,
        action="MENU_PERMISSIONS_UPDATED",
        ip_address=client_ip
    )
    db.add(audit_log)
    db.commit()
    
    return {"message": "메뉴 권한이 성공적으로 업데이트되었습니다."}

@router.get("/permissions/my", response_model=List[str])
def get_my_menu_permissions(
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """현재 로그인한 사용자의 접근 가능한 메뉴 경로 목록 조회"""
    permissions = db.query(models.MenuPermission).filter(
        models.MenuPermission.role == current_user.role,
        models.MenuPermission.is_visible == True
    ).all()
    
    return [p.menu_path for p in permissions]
