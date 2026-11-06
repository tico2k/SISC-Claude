"""
이메일 발송 서비스

SMTP를 통한 이메일 발송 및 템플릿 렌더링
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import List, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape
from ..core.config import settings
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class EmailService:
    """이메일 발송 서비스"""
    
    def __init__(self):
        # Jinja2 환경 설정
        template_dir = Path(__file__).parent.parent / "templates" / "email"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(['html', 'xml'])
        )
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None
    ) -> bool:
        """
        이메일 발송
        
        Args:
            to_email: 수신자 이메일
            subject: 제목
            html_body: HTML 본문
            text_body: 텍스트 본문 (선택사항)
        
        Returns:
            발송 성공 여부
        """
        if not settings.ENABLE_EMAIL_NOTIFICATIONS:
            logger.info(f"이메일 알림이 비활성화되어 있습니다: {to_email}")
            return False
        
        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            logger.warning("SMTP 설정이 완료되지 않았습니다")
            return False
        
        try:
            # 메시지 생성
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
            msg["To"] = to_email
            
            # 텍스트 파트 (선택사항)
            if text_body:
                part1 = MIMEText(text_body, "plain", "utf-8")
                msg.attach(part1)
            
            # HTML 파트
            part2 = MIMEText(html_body, "html", "utf-8")
            msg.attach(part2)
            
            # SMTP 서버 연결 및 발송
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                if settings.SMTP_TLS:
                    server.starttls()
                
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
            
            logger.info(f"이메일 발송 성공: {to_email} - {subject}")
            return True
            
        except Exception as e:
            logger.error(f"이메일 발송 실패: {to_email} - {str(e)}", exc_info=True)
            return False
    
    def render_template(self, template_name: str, **context) -> str:
        """
        템플릿 렌더링
        
        Args:
            template_name: 템플릿 파일명
            **context: 템플릿 컨텍스트
        
        Returns:
            렌더링된 HTML
        """
        try:
            template = self.jinja_env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            logger.error(f"템플릿 렌더링 실패: {template_name} - {str(e)}")
            raise
    
    def send_template_email(
        self,
        to_email: str,
        subject: str,
        template_name: str,
        **template_context
    ) -> bool:
        """
        템플릿 기반 이메일 발송
        
        Args:
            to_email: 수신자 이메일
            subject: 제목
            template_name: 템플릿 파일명
            **template_context: 템플릿 컨텍스트
        
        Returns:
            발송 성공 여부
        """
        try:
            html_body = self.render_template(template_name, **template_context)
            return self.send_email(to_email, subject, html_body)
        except Exception as e:
            logger.error(f"템플릿 이메일 발송 실패: {to_email} - {str(e)}")
            return False


# 싱글톤 인스턴스
email_service = EmailService()
