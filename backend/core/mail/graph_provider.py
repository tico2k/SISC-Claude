import requests
import logging
from typing import List, Optional
from backend.core.config import settings
from .base import MailProvider

logger = logging.getLogger(__name__)

class GraphMailProvider(MailProvider):
    """Microsoft Graph API 기반 이메일 발송"""
    
    def __init__(self):
        self.tenant_id = settings.ENTRA_TENANT_ID
        self.client_id = settings.ENTRA_CLIENT_ID
        self.client_secret = settings.ENTRA_CLIENT_SECRET
        self.sender_email = settings.GRAPH_MAIL_SENDER or settings.SMTP_FROM_EMAIL
        
    def _get_access_token(self) -> Optional[str]:
        """Client Credentials Flow를 통한 액세스 토큰 획득"""
        url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        data = {
            "client_id": self.client_id,
            "scope": "https://graph.microsoft.com/.default",
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
        }
        try:
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            return response.json().get("access_token")
        except Exception as e:
            logger.error(f"Failed to get Microsoft Graph access token: {str(e)}")
            return None

    def send_mail(
        self,
        to_email: str,
        subject: str,
        content: str,
        is_html: bool = True,
        attachments: Optional[List[str]] = None
    ) -> bool:
        if not settings.ENABLE_EMAIL_NOTIFICATIONS:
            logger.info("Email notifications are disabled in settings.")
            return True

        if not all([self.tenant_id, self.client_id, self.client_secret]):
            logger.warning("Microsoft Graph settings (Tenant/Client ID/Secret) are missing.")
            return False

        token = self._get_access_token()
        if not token:
            return False

        # Graph API sendMail 엔드포인트
        # 특정 사용자 계정의 사함함을 통해 발송 (Application 권한 필요: Mail.Send)
        url = f"https://graph.microsoft.com/v1.0/users/{self.sender_email}/sendMail"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "HTML" if is_html else "Text",
                    "content": content
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": to_email
                        }
                    }
                ]
            }
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            logger.info(f"Email sent successfully to {to_email} via Microsoft Graph")
            return True
        except Exception as e:
            logger.error(f"Failed to send email via Microsoft Graph: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Graph API Error Response: {e.response.text}")
            return False
