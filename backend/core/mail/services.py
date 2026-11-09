"""
메일 발송 서비스 (단일 진입점)

- 템플릿: core/mail/templates.py 목록 + backend/templates/email/*.html 기본 본문. 관리자 수정본(DB)이 있으면 우선 사용
- 발송: MailFactory가 MAIL_SENDER_TYPE에 따라 SMTP 또는 Outlook(Graph) 프로바이더 선택
- 발송 함수는 blocking I/O이므로 동기 함수로 두고, BackgroundTasks/스케줄러의 스레드에서 실행한다
"""

from datetime import datetime
from typing import Optional

from markupsafe import Markup

from backend.core import database as core_db
from backend.core.config import settings
from backend.core.logging_config import get_logger
from backend.core.mail import templates as mail_templates
from backend.core.mail.factory import MailFactory

logger = get_logger(__name__)


def _load_override(template_key: str) -> Optional[tuple[str, str]]:
    """관리자가 수정한 템플릿(제목, 본문). 없거나 DB 조회에 실패하면 None (기본 템플릿 사용)"""
    from backend.models import NotificationTemplate

    try:
        db = core_db.SessionLocal()
        try:
            row = db.get(NotificationTemplate, template_key)
            return (row.subject, row.body_html) if row else None
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"알림 템플릿 조회 실패, 기본 템플릿 사용: {template_key} - {type(e).__name__}")
        return None


def render_template(template_name: str, **context) -> str:
    """본문만 렌더링 (수정본이 있으면 수정본 사용)"""
    return mail_templates.render(template_name, context, _load_override(template_name))[1]


def send_template_mail(to_email: str, template_name: str, subject: Optional[str] = None, **context) -> bool:
    """템플릿을 렌더링해 설정된 프로바이더로 발송. 제목은 템플릿 설정을 따르고, subject를 주면 그 값을 사용.
    실패해도 예외를 던지지 않고 False 반환"""
    try:
        rendered_subject, html = mail_templates.render(template_name, context, _load_override(template_name))
    except Exception as e:
        logger.error(f"메일 템플릿 렌더링 실패: {template_name} - {str(e)}", exc_info=True)
        return False
    return MailFactory.get_provider().send_mail(
        to_email=to_email, subject=subject or rendered_subject, content=html, is_html=True
    )


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
