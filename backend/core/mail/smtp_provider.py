import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from backend.core.config import settings
from .base import MailProvider

logger = logging.getLogger(__name__)

class SMTPProvider(MailProvider):
    """SMTP 기반 이메일 발송"""
    
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
        
        if not settings.SMTP_HOST or not settings.SMTP_USER:
            logger.warning("SMTP settings are missing.")
            return False

        try:
            msg = MIMEMultipart()
            msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
            msg["To"] = to_email
            msg["Subject"] = subject

            part = MIMEText(content, "html" if is_html else "plain", "utf-8")
            msg.attach(part)

            # TODO: 첨부 파일 처리 (필요시)

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                if settings.SMTP_TLS:
                    server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email} via SMTP")
            return True
        except Exception as e:
            logger.error(f"Failed to send email via SMTP: {str(e)}", exc_info=True)
            return False
