import logging
import os
from datetime import datetime
from typing import Optional
from backend.core.config import settings
from backend.core.mail.factory import MailFactory
from backend.models import ClarificationCase, User

logger = logging.getLogger(__name__)

def get_template(template_name: str) -> str:
    """템플릿 파일 읽기"""
    template_path = os.path.join("backend/templates", template_name)
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to load email template {template_name}: {str(e)}")
        return ""

async def send_request_notification(
    to_email: str,
    user_name: str,
    priority: str,
    incident_num: str,
    rule_title: str,
    due_date: datetime,
    request_reason: str,
    case_id: int
):
    """소명 요청 알림 메일 발송"""
    if not settings.ENABLE_EMAIL_NOTIFICATIONS:
        return

    template = get_template("request_mail.html")
    if not template:
        return

    # 템플릿 변수 치환
    priority_class = "badge-urgent" if priority == "높음" else "badge-normal"
    due_date_str = due_date.strftime("%Y년 %m월 %d일") if due_date else "-"
    
    # 상제 소명 케이스 페이지 URL
    login_url = f"{settings.frontend_url}/cases/{case_id}"
    logger.info(f"Generated email redirect URL: {login_url}")

    safe_request_reason = str(request_reason or "").replace("\n", "<br>")

    content = template.replace("{user_name}", str(user_name)) \
                      .replace("{priority}", str(priority)) \
                      .replace("{priority_class}", str(priority_class)) \
                      .replace("{incident_num}", str(incident_num)) \
                      .replace("{rule_title}", str(rule_title)) \
                      .replace("{due_date}", str(due_date_str)) \
                      .replace("{request_reason}", safe_request_reason) \
                      .replace("{login_url}", str(login_url))

    subject = f"[{priority}] 보안 소명 요청 안내 - #{incident_num}"
    
    provider = MailFactory.get_provider()
    await provider.send_mail(
        to_email=to_email,
        subject=subject,
        content=content,
        is_html=True
    )
