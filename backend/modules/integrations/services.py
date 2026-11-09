"""
외부 연동 설정 서비스 (설치 후 관리자 화면에서 설정)

- Microsoft Entra ID: SSO 로그인, 사용자 동기화, Outlook(Graph) 메일 발송에 사용
- 설정은 DB(integration_setting)에 저장하고 시크릿은 Fernet으로 암호화한다
- 연동을 설정하지 않으면 Entra 관련 기능은 모두 꺼진 상태로 동작한다
"""
import os
import re
import time
from dataclasses import dataclass
from typing import Optional

import requests
from dotenv import load_dotenv
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from ... import models, schemas
from ...core.config import settings
from ...core.exceptions import AuthenticationException, ExternalServiceException, ValidationException
from ...core.logging_config import get_logger
from ...core.security import encrypt_secret, decrypt_secret

logger = get_logger(__name__)

ENTRA = "ENTRA"
SECRET_MASK = "********"
GUID_PATTERN = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
JWKS_CACHE_SECONDS = 3600


@dataclass(frozen=True)
class EntraConfig:
    is_enabled: bool = False
    tenant_id: str = ""
    client_id: str = ""
    encrypted_secret: str = ""
    mail_sender: str = ""

    @property
    def is_ready(self) -> bool:
        """SSO 로그인 가능 여부 (활성화 + 테넌트/클라이언트 ID 입력)"""
        return self.is_enabled and bool(self.tenant_id and self.client_id)

    @property
    def has_app_credentials(self) -> bool:
        """사용자 동기화·메일 발송 가능 여부 (클라이언트 시크릿까지 필요)"""
        return self.is_ready and bool(self.encrypted_secret)

    @property
    def authority(self) -> str:
        return f"{settings.ENTRA_AUTHORITY_HOST}/{self.tenant_id}"

    def client_secret(self) -> str:
        """복호화된 클라이언트 시크릿 (실패 시 DecryptionError)"""
        return decrypt_secret(self.encrypted_secret) if self.encrypted_secret else ""


def get_entra_config(db: Session) -> EntraConfig:
    row = db.get(models.IntegrationSetting, ENTRA)
    if not row:
        return EntraConfig()
    return EntraConfig(
        is_enabled=bool(row.is_enabled),
        tenant_id=row.tenant_id or "",
        client_id=row.client_id or "",
        encrypted_secret=row.client_secret or "",
        mail_sender=row.mail_sender or "",
    )


def to_entra_response(db: Session) -> schemas.EntraIntegrationResponse:
    row = db.get(models.IntegrationSetting, ENTRA)
    if not row:
        return schemas.EntraIntegrationResponse(is_enabled=False, client_secret_set=False)
    return schemas.EntraIntegrationResponse(
        is_enabled=bool(row.is_enabled),
        tenant_id=row.tenant_id,
        client_id=row.client_id,
        client_secret_set=bool(row.client_secret),
        mail_sender=row.mail_sender,
        updated_at=row.updated_at,
    )


def update_entra_config(
    db: Session, data: schemas.EntraIntegrationUpdate, actor: models.User, ip_address: str
) -> schemas.EntraIntegrationResponse:
    tenant_id = (data.tenant_id or "").strip()
    client_id = (data.client_id or "").strip()
    mail_sender = (data.mail_sender or "").strip()

    # 테넌트 ID는 인증 URL에 들어가므로 GUID 형식만 허용
    if tenant_id and not GUID_PATTERN.match(tenant_id):
        raise ValidationException("테넌트 ID는 GUID 형식이어야 합니다 (예: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)")
    if client_id and not GUID_PATTERN.match(client_id):
        raise ValidationException("클라이언트(애플리케이션) ID는 GUID 형식이어야 합니다")
    if mail_sender and not EMAIL_PATTERN.match(mail_sender):
        raise ValidationException("메일 발송 사서함 주소 형식이 올바르지 않습니다")
    if data.is_enabled and not (tenant_id and client_id):
        raise ValidationException("연동을 활성화하려면 테넌트 ID와 클라이언트 ID를 입력해야 합니다")

    row = db.get(models.IntegrationSetting, ENTRA)
    if not row:
        row = models.IntegrationSetting(provider=ENTRA)
        db.add(row)

    secret_action = "unchanged"
    if data.client_secret is not None and data.client_secret != SECRET_MASK:
        if data.client_secret == "":
            row.client_secret = None
            secret_action = "cleared"
        else:
            row.client_secret = encrypt_secret(data.client_secret)
            secret_action = "replaced"

    row.is_enabled = data.is_enabled
    row.tenant_id = tenant_id or None
    row.client_id = client_id or None
    row.mail_sender = mail_sender or None
    row.updated_by = actor.user_id

    # 시크릿·ID 값은 감사로그에 남기지 않는다
    db.add(models.SystemAuditLog(
        actor_id=actor.user_id,
        action=f"INTEGRATION_ENTRA_UPDATED: enabled={data.is_enabled}, secret={secret_action}",
        ip_address=ip_address,
    ))
    db.commit()
    logger.info(f"Entra 연동 설정 변경: enabled={data.is_enabled}, secret={secret_action} by {actor.user_email}")
    return to_entra_response(db)


def check_entra_connection(db: Session) -> schemas.IntegrationTestResponse:
    """저장된 설정으로 앱 토큰 발급을 시도한다 (사용자 동기화·메일 발송 권한 확인용)"""
    from ..auth import entra_service

    entra = get_entra_config(db)
    if not (entra.tenant_id and entra.client_id):
        return schemas.IntegrationTestResponse(status="error", message="테넌트 ID와 클라이언트 ID를 먼저 저장하세요")
    if not entra.encrypted_secret:
        return schemas.IntegrationTestResponse(
            status="error",
            message="클라이언트 시크릿이 없습니다. SSO 로그인만 사용할 경우 시크릿 없이도 동작하지만, 사용자 동기화와 Outlook 메일 발송에는 필요합니다",
        )
    try:
        entra_service.get_app_access_token(entra)
    except ExternalServiceException as e:
        return schemas.IntegrationTestResponse(status="error", message=e.detail)
    return schemas.IntegrationTestResponse(status="success", message="Entra ID 앱 인증에 성공했습니다")


# --- 인증 정책 ---

def read_local_login_policy() -> tuple[bool, str]:
    """(자체 로그인 허용 여부, 기본 인증 방식). 화면에서 .env를 바꾸면 재시작 없이 반영되도록 매번 읽는다"""
    load_dotenv(override=True)
    allow_local = os.getenv("ALLOW_LOCAL_LOGIN", "true").lower() == "true"
    default_method = os.getenv("DEFAULT_AUTH_METHOD", "LOCAL").upper()
    return allow_local, default_method


def get_auth_config(db: Session) -> schemas.AuthConfigResponse:
    allow_local, default_method = read_local_login_policy()
    entra = get_entra_config(db)
    if not entra.is_ready:
        # Entra가 설정되지 않았으면 기본 인증 방식이 ENTRA여도 자체 로그인으로 동작
        default_method = "LOCAL"
    return schemas.AuthConfigResponse(
        allow_local=allow_local,
        allow_entra=entra.is_ready,
        default_method=default_method,
        entra_client_id=entra.client_id if entra.is_ready else None,
        entra_tenant_id=entra.tenant_id if entra.is_ready else None,
    )


# --- ID 토큰 검증 ---

_jwks_cache: dict[str, tuple[float, dict]] = {}


def _get_jwks(tenant_id: str, force_refresh: bool = False) -> dict:
    cached = _jwks_cache.get(tenant_id)
    now = time.monotonic()
    if cached and not force_refresh and now - cached[0] < JWKS_CACHE_SECONDS:
        return cached[1]
    url = f"{settings.ENTRA_AUTHORITY_HOST}/{tenant_id}/discovery/v2.0/keys"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        jwks = response.json()
    except (requests.RequestException, ValueError) as e:
        logger.error(f"Entra 서명 키(JWKS) 조회 실패: {type(e).__name__}")
        raise ExternalServiceException("Entra ID", "인증 서비스 연결 중 오류가 발생했습니다")
    _jwks_cache[tenant_id] = (now, jwks)
    return jwks


def verify_entra_id_token(id_token: str, entra: EntraConfig) -> dict:
    """ID 토큰의 서명(JWKS)·대상(aud=우리 앱)·발급자/테넌트(tid)·만료를 검증하고 클레임을 반환한다"""
    try:
        kid = jwt.get_unverified_header(id_token).get("kid")
    except JWTError:
        raise AuthenticationException("Entra ID 토큰 형식이 올바르지 않습니다")

    jwks = _get_jwks(entra.tenant_id)
    if kid not in {k.get("kid") for k in jwks.get("keys", [])}:
        # 키 교체 직후일 수 있으므로 한 번 새로 받는다
        jwks = _get_jwks(entra.tenant_id, force_refresh=True)

    expected_issuer = f"{settings.ENTRA_AUTHORITY_HOST}/{entra.tenant_id}/v2.0"
    try:
        claims = jwt.decode(
            id_token,
            jwks,
            algorithms=["RS256"],
            audience=entra.client_id,
            issuer=expected_issuer,
            # 프론트는 ID 토큰만 보내므로 access token 해시(at_hash) 비교는 하지 않음
            options={"verify_at_hash": False},
        )
    except JWTError as e:
        logger.warning(f"Entra ID 토큰 검증 실패: {type(e).__name__}: {e}")
        raise AuthenticationException("Entra ID 인증에 실패했습니다")

    if (claims.get("tid") or "").lower() != entra.tenant_id.lower():
        logger.warning("Entra ID 토큰 검증 실패: 테넌트 불일치")
        raise AuthenticationException("Entra ID 인증에 실패했습니다")
    return claims
