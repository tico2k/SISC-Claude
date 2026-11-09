from backend.modules.reports.router import router as reports_router
from fastapi import FastAPI, Request, status
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from .modules.auth.router import router as auth_router
from .modules.cases.router import router as cases_router
from .modules.submissions.router import router as submissions_router
from .modules.reviews.router import router as reviews_router
from .modules.siem.router import router as siem_router
from .modules.users.router import router as users_router
from .modules.audit.router import router as audit_router
from .modules.system.router import router as system_router
from .modules.integrations.router import router as integrations_router
from .modules.notifications.router import router as notifications_router
from . import models
from .core import database
from .core.exceptions import BaseAPIException
from .core.logging_config import setup_logging, get_logger
from .core.limiter import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import os
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError
from .core.scheduler import start_scheduler, stop_scheduler
from .core.config import settings

# 환경 변수 로드
load_dotenv(override=True)

# 로깅 시스템 초기화
setup_logging()
logger = get_logger(__name__)

async def create_initial_admin():
    """초기 설치 시 시스템 관리자 자동 생성"""
    from .core.database import SessionLocal
    from .core.dependencies import get_password_hash
    from . import models
    
    db = SessionLocal()
    try:
        # 사용자 존재 여부 확인
        user_count = db.query(models.User).count()
        if user_count == 0:
            admin_email = os.getenv("INITIAL_ADMIN_EMAIL", "system@fleitlab.com")
            admin_password = os.getenv("INITIAL_ADMIN_PASSWORD", "password123")
            
            logger.info(f"초기 관리자 계정 생성 시도: {admin_email}")
            
            new_admin = models.User(
                user_email=admin_email,
                user_name="시스템관리자(초기)",
                hashed_password=get_password_hash(admin_password),
                company="Fleitlab",
                department="System Admin",
                role=models.UserRole.SYSTEM_ADMIN
            )
            db.add(new_admin)
            
            # 감사 로그 (시스템 자체 생성)
            audit_log = models.SystemAuditLog(
                actor_id=None, # 시스템 자동 생성
                action=f"BOOTSTRAP_ADMIN_CREATED: {admin_email}",
                ip_address="127.0.0.1"
            )
            db.add(audit_log)
            
            db.commit()
            logger.info(f"초기 관리자 계정이 성공적으로 생성되었습니다: {admin_email}")
        else:
            logger.debug(f"기본 사용자({user_count}명)가 이미 존재하여 Bootstrap을 건너뜁니다.")
    except Exception as e:
        db.rollback()
        logger.error(f"초기 관리자 계정 생성 실패: {str(e)}")
    finally:
        db.close()

async def create_initial_menu_permissions():
    """초기 메뉴 권한 설정 시딩"""
    from .core.database import SessionLocal
    from . import models
    
    db = SessionLocal()
    try:
        logger.debug("기본 메뉴 권한 시딩 확인...")
        
        # 권한 규칙 정의 (메뉴 경로: [허용된 역할들])
        menu_rules = {
            "/dashboard": [models.UserRole.USER, models.UserRole.SECURITY_ADMIN, models.UserRole.AUDIT_TEAM, models.UserRole.SYSTEM_ADMIN],
            "/cases": [models.UserRole.USER, models.UserRole.SECURITY_ADMIN],
            "/reviews": [models.UserRole.SECURITY_ADMIN, models.UserRole.AUDIT_TEAM, models.UserRole.SYSTEM_ADMIN],
            "/logs": [models.UserRole.SECURITY_ADMIN, models.UserRole.AUDIT_TEAM, models.UserRole.SYSTEM_ADMIN],
            "/siem": [models.UserRole.SECURITY_ADMIN, models.UserRole.AUDIT_TEAM, models.UserRole.SYSTEM_ADMIN],
            "/users": [models.UserRole.SYSTEM_ADMIN],
            "/env": [models.UserRole.SECURITY_ADMIN, models.UserRole.AUDIT_TEAM, models.UserRole.SYSTEM_ADMIN],
            "/jobs": [models.UserRole.SYSTEM_ADMIN],
            "/permissions": [models.UserRole.SYSTEM_ADMIN],
            "/integrations": [models.UserRole.SYSTEM_ADMIN],
            "/notifications": [models.UserRole.SYSTEM_ADMIN, models.UserRole.SECURITY_ADMIN],
        }

        roles = [models.UserRole.USER, models.UserRole.SECURITY_ADMIN, models.UserRole.AUDIT_TEAM, models.UserRole.SYSTEM_ADMIN]
        
        # 없는 (역할, 메뉴) 조합만 추가 — 관리자가 바꾼 기존 설정은 유지하고, 새 메뉴는 기존 설치에도 반영
        existing = {(p.role, p.menu_path) for p in db.query(models.MenuPermission).all()}
        new_permissions = []
        for path, allowed_roles in menu_rules.items():
            for role in roles:
                if (role, path) in existing:
                    continue
                new_permissions.append(
                    models.MenuPermission(
                        role=role,
                        menu_path=path,
                        is_visible=(role in allowed_roles)
                    )
                )
        
        if not new_permissions:
            return
        db.add_all(new_permissions)
        db.commit()
        logger.info(f"메뉴 권한 {len(new_permissions)}건을 추가했습니다.")
        
    except Exception as e:
        db.rollback()
        logger.error(f"메뉴 권한 초기 설정 실패: {str(e)}")
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 이벤트
    logger.info("=" * 50)
    logger.info("Fleit InsiderGuard SICS Backend 시작")
    logger.info(f"환경: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info("=" * 50)
    
    # 초기 관리자 생성 (Bootstrap)
    await create_initial_admin()
    
    # 초기 메뉴 권한 생성
    await create_initial_menu_permissions()
    
    # 스케줄러 시작 (경량 백그라운드 태스크)
    start_scheduler()
    
    yield
    
    # 스케줄러 종료
    stop_scheduler()
    
    # 종료 이벤트
    logger.info("Fleit InsiderGuard SICS Backend 종료")

# Create tables
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(
    title="Fleit InsiderGuard - SICS Backend",
    description="Security Incident Clarification System API",
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# CORS 설정 - 환경 변수에서 허용된 origin 로드
origins_env = os.getenv("CORS_ORIGINS", "http://localhost:5173")
origins = [origin.strip() for origin in origins_env.split(",")]

logger.info(f"CORS 허용 origin: {origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "Accept",
        "X-Requested-With",
        "X-CSRF-Token",
        "Access-Control-Allow-Origin"
    ],
)


# 전역 예외 핸들러
# 전역 예외 핸들러
@app.exception_handler(BaseAPIException)
async def custom_exception_handler(request: Request, exc: BaseAPIException):
    """커스텀 예외 핸들러"""
    logger.warning(
        f"API 예외 발생: {exc.error_code} - {exc.detail} - "
        f"경로: {request.url.path} - 메서드: {request.method}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "detail": exc.detail
        }
    )

# Rate Limit 예외 핸들러 등록
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """FastAPI 검증 에러 핸들러"""
    # 에러를 문자열로 변환하여 JSON 직렬화 문제 방지
    error_details = []
    for error in exc.errors():
        error_dict = {
            "loc": [str(loc) for loc in error.get("loc", [])],
            "msg": error.get("msg", ""),
            "type": error.get("type", ""),
        }
        error_details.append(error_dict)
    
    logger.warning(
        f"요청 검증 실패 - 경로: {request.url.path} - 에러: {error_details}"
    )
    return JSONResponse(
        status_code=422,  # Starlette 버전별 상수명 차이(ENTITY→CONTENT)를 피하려고 숫자 사용
        content={
            "error": "VALIDATION_ERROR",
            "message": "입력 데이터가 올바르지 않습니다",
            "details": error_details
        }
    )


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    """데이터베이스 예외 핸들러"""
    logger.error(
        f"데이터베이스 오류 - 경로: {request.url.path} - 에러: {str(exc)}",
        exc_info=True
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "DATABASE_ERROR",
            "message": "데이터베이스 처리 중 오류가 발생했습니다"
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """일반 예외 핸들러 (최종 안전망)"""
    logger.error(
        f"예상치 못한 오류 - 경로: {request.url.path} - "
        f"메서드: {request.method} - 에러: {str(exc)}",
        exc_info=True
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "서버 내부 오류가 발생했습니다"
        }
    )






# Include Routers
app.include_router(reports_router)
app.include_router(auth_router)
app.include_router(cases_router)
app.include_router(submissions_router)
app.include_router(reviews_router)
app.include_router(siem_router)
app.include_router(users_router)
app.include_router(audit_router)
app.include_router(system_router)
app.include_router(integrations_router)
app.include_router(notifications_router)


@app.get("/")
def read_root():
    """루트 엔드포인트 - 헬스 체크"""
    return {
        "message": "Welcome to Fleit InsiderGuard SICS Backend",
        "status": "healthy",
        "version": settings.APP_VERSION
    }


@app.get("/health")
def health_check():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "service": "SICS Backend"
    }
