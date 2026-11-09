"""
Microsoft Entra ID 앱 권한(Client Credentials) 호출

설정은 호출할 때마다 DB(integration_setting)에서 받은 EntraConfig를 사용한다.
(설치 후 설정을 바꿔도 재시작 없이 반영)
"""
from typing import Any, Dict, List

import msal
import requests

from ...core.config import settings
from ...core.exceptions import ExternalServiceException, ValidationException
from ...core.logging_config import get_logger
from ...core.security import DecryptionError

logger = get_logger(__name__)


def get_app_access_token(entra) -> str:
    """Graph API 호출용 앱 토큰 발급. entra: integrations.services.EntraConfig"""
    if not entra.has_app_credentials:
        raise ValidationException("Entra 연동(테넌트·클라이언트 ID·시크릿)이 설정되지 않았습니다")
    try:
        secret = entra.client_secret()
    except DecryptionError as e:
        raise ValidationException(str(e))

    try:
        app = msal.ConfidentialClientApplication(
            entra.client_id, authority=entra.authority, client_credential=secret
        )
        result = app.acquire_token_for_client(scopes=[f"{settings.GRAPH_API_URL}/.default"])
    except Exception as e:  # msal은 네트워크·설정 오류를 다양한 예외로 던진다
        logger.error(f"Entra 앱 토큰 발급 중 오류: {type(e).__name__}: {e}")
        raise ExternalServiceException("Entra ID", "Entra ID 인증 서버에 연결할 수 없습니다")

    if "access_token" not in result:
        logger.error(f"Entra 앱 토큰 발급 실패: {result.get('error')} - {result.get('error_description')}")
        raise ExternalServiceException("Entra ID", f"Entra ID 앱 인증 실패: {result.get('error', 'unknown_error')}")
    return result["access_token"]


def get_all_users(entra) -> List[Dict[str, Any]]:
    """Graph API로 전체 사용자 목록을 가져온다 (페이지 처리 포함)"""
    token = get_app_access_token(entra)
    headers = {"Authorization": f"Bearer {token}"}
    # manager는 부서장 자동 지정에 사용 (User.Read.All 권한으로 조회 가능)
    url = (f"{settings.GRAPH_API_URL}/v1.0/users?$select=userPrincipalName,displayName,companyName,department,jobTitle"
           "&$expand=manager($select=userPrincipalName)")

    users: List[Dict[str, Any]] = []
    while url:
        try:
            response = requests.get(url, headers=headers, timeout=30)
        except requests.RequestException as e:
            logger.error(f"Graph 사용자 조회 중 네트워크 오류: {type(e).__name__}")
            raise ExternalServiceException("Microsoft Graph")
        if response.status_code != 200:
            # 일부만 받은 상태로 동기화하지 않도록 중단
            logger.error(f"Graph 사용자 조회 실패: {response.status_code} {response.text[:500]}")
            raise ExternalServiceException("Microsoft Graph", "Graph 사용자 조회에 실패했습니다 (User.Read.All 권한과 관리자 동의를 확인하세요)")
        data = response.json()
        users.extend(data.get("value", []))
        url = data.get("@odata.nextLink")
    return users
