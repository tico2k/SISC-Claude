"""
메일 발송 서비스 (단일 진입점)

- 템플릿: backend/templates/email/*.html (Jinja2, HTML 자동 이스케이프)
- 발송: MailFactory가 MAIL_SENDER_TYPE에 따라 SMTP 또는 Outlook(Graph) 프로바이더 선택
- 발송 함수는 blocking I/O이므로 동기 함수로 두고, BackgroundTasks/스케줄러의 스레드에서 실행한다
"""

from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from backend.core.config import settings
from backend.core.logging_config import get_logger
from backend.core.mail.factory import MailFactory

logger = get_logger(__name__)

TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates" / "email"

_jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def render_template(template_name: str, **context) -> str:
    return _jinja_env.get_template(template_name).render(**context)


def send_template_mail(to_email: str, subject: str, template_name: str, **context) -> bool:
    """템플릿을 렌더링해 설정된 프로바이더로 발송. 실패해도 예외를 던지지 않고 False 반환"""
    try:
        html = render_template(template_name, **context)
    except Exception as e:
        logger.error(f"메일 템플릿 렌더링 실패: {template_name} - {str(e)}", exc_info=True)
        return False
    return MailFactory.get_provider().send_mail(to_email=to_email, subject=subject, content=html, is_html=True)


def send_request_notification(
    to_email: str,
    user_name: str,
    priority: str,
    incident_num: str,
    rule_title: str,
    due_date: datetime,
    request_reason: str,
    case_id: int
) -> bool:
    """소명 요청 알림 메일 발송"""
    # 줄바꿈만 <br>로 바꾸고 나머지 내용은 이스케이프
    reason_html = Markup("<br>").join(str(request_reason or "").splitlines())
    return send_template_mail(
        to_email=to_email,
        subject=f"[{priority}] 보안 소명 요청 안내 - #{incident_num}",
        template_name="request_mail.html",
        user_name=user_name,
        priority=priority,
        priority_class="badge-urgent" if priority == "높음" else "badge-normal",
        incident_num=incident_num,
        rule_title=rule_title,
        due_date=due_date.strftime("%Y년 %m월 %d일") if due_date else "-",
        request_reason=reason_html,
        login_url=f"{settings.frontend_url}/cases/{case_id}",
    )
