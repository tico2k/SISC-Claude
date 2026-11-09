import requests
import logging
from typing import List, Optional
from backend.core.config import settings
from .base import MailProvider

logger = logging.getLogger(__name__)

class GraphMailProvider(MailProvider):
    """Microsoft Graph API 기반 이메일 발송 (Entra 연동 설정은 발송 시점에 DB에서 읽음)"""

    def _load_entra_config(self):
        # core → modules 순환 import를 피하려고 함수 안에서 import
        from backend.core.database import SessionLocal
        from backend.modules.integrations.services import get_entra_config

        db = SessionLocal()
        try:
            return get_entra_config(db)
        finally:
            db.close()

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

        from backend.modules.auth.entra_service import get_app_access_token

        entra = self._load_entra_config()
        if not entra.has_app_credentials:
            logger.warning("MAIL_SENDER_TYPE=OUTLOOK이지만 Entra 연동(테넌트·클라이언트 ID·시크릿)이 설정되지 않아 메일을 보내지 않습니다.")
            return False

        try:
            token = get_app_access_token(entra)
        except Exception as e:
            logger.error(f"Failed to get Microsoft Graph access token: {e}")
            return False

        sender_email = entra.mail_sender or settings.SMTP_FROM_EMAIL

        # Graph API sendMail 엔드포인트
        # 특정 사용자 계정의 사함함을 통해 발송 (Application 권한 필요: Mail.Send)
        url = f"{settings.GRAPH_API_URL}/v1.0/users/{sender_email}/sendMail"
        
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
