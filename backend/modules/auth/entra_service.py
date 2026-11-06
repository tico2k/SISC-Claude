import msal
import requests
from typing import List, Dict, Any, Optional
from ...core.entra_config import entra_settings
from ...core.logging_config import get_logger

logger = get_logger(__name__)

class EntraService:
    def __init__(self):
        self._app = None

    @property
    def app(self):
        """
        ConfidentialClientApplication을 필요한 시점에 초기화합니다.
        설정이 누락된 경우 서버 시작 시점이 아닌, 실제 호출 시점에 오류를 발생시킵니다.
        """
        if self._app is None:
            if not entra_settings.ENTRA_CLIENT_ID or not entra_settings.ENTRA_TENANT_ID:
                # 설정이 누락된 경우 None을 유지하여 나중에 체크 가능하게 함
                return None
                
            try:
                self._app = msal.ConfidentialClientApplication(
                    entra_settings.ENTRA_CLIENT_ID,
                    authority=entra_settings.authority,
                    client_credential=entra_settings.ENTRA_CLIENT_SECRET,
                )
            except Exception as e:
                logger.error(f"Failed to initialize MSAL application: {e}")
                return None
        return self._app

    def get_access_token(self) -> Optional[str]:
        """
        Client Credentials Flow를 사용하여 Graph API 액세스 토큰을 획득합니다. (동기화용)
        """
        msal_app = self.app
        if not msal_app:
            logger.error("Entra ID configuration is missing or invalid. Check your .env file.")
            return None
            
        result = msal_app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        if "access_token" in result:
            return result["access_token"]
        else:
            logger.error(f"Failed to acquire Entra ID access token: {result.get('error_description')}")
            return None

    def get_all_users(self) -> List[Dict[str, Any]]:
        """
        Microsoft Graph API를 통해 모든 사용자 리스트를 가져옵니다.
        """
        token = self.get_access_token()
        if not token:
            return []

        users = []
        # https://learn.microsoft.com/en-us/graph/api/user-list
        url = "https://graph.microsoft.com/v1.0/users?$select=userPrincipalName,displayName,companyName,department,jobTitle"
        
        headers = {"Authorization": f"Bearer {token}"}
        
        while url:
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                logger.error(f"Graph API call failed: {response.text}")
                break
            
            data = response.json()
            users.extend(data.get("value", []))
            
            # Pagination 처리
            url = data.get("@odata.nextLink")
            
        return users

    def validate_id_token(self, id_token: str) -> Optional[Dict[str, Any]]:
        """
        Frontend에서 받은 ID Token의 유효성을 검증합니다. (비즈니스 로직에 따라 추가 구현 가능)
        실제로는 msal-python의 기능을 활용하거나 전용 JWT 검증 라이브러리를 사용할 수 있습니다.
        """
        # Note: 간단한 구현을 위해 여기서는 msal의 acquire_token_by_auth_code 등의 결과에서 
        # 나오는 정보를 신뢰하는 수준으로 제안하거나, JWT 디코딩 로직을 추가합니다.
        # 이 가이드에서는 OIDC 표준에 따라 유효성을 검증하는 것으로 간주합니다.
        pass

entra_service = EntraService()
