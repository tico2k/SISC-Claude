"""
알림 메일 템플릿 관리 (관리자가 화면에서 제목·본문 수정)

- 수정본은 notification_template 테이블에 저장되고, 삭제하면 기본 템플릿으로 돌아간다
- 저장 전에 샌드박스로 샘플 렌더링을 해 문법 오류·허용되지 않는 구문을 막는다
"""
from sqlalchemy.orm import Session

from ... import models, schemas
from ...core.exceptions import NotFoundException, ValidationException
from ...core.logging_config import get_logger
from ...core.mail import templates as mail_templates

logger = get_logger(__name__)

MAX_SUBJECT = 500
MAX_BODY = 200_000


def _spec(template_key: str) -> mail_templates.TemplateSpec:
    spec = mail_templates.TEMPLATES.get(template_key)
    if not spec:
        raise NotFoundException("알림 템플릿을 찾을 수 없습니다")
    return spec


def _to_response(template_key: str, row) -> schemas.NotificationTemplateResponse:
    spec = _spec(template_key)
    return schemas.NotificationTemplateResponse(
        template_key=template_key,
        name=spec.name,
        description=spec.description,
        variables=spec.variables,
        subject=row.subject if row else spec.subject,
        body_html=row.body_html if row else mail_templates.default_body(template_key),
        is_customized=row is not None,
        updated_at=row.updated_at if row else None,
    )


def list_templates(db: Session) -> list[schemas.NotificationTemplateResponse]:
    rows = {r.template_key: r for r in db.query(models.NotificationTemplate).all()}
    return [_to_response(key, rows.get(key)) for key in mail_templates.TEMPLATES]


def _validate(template_key: str, data: schemas.NotificationTemplateUpdate) -> None:
    if not data.subject.strip() or not data.body_html.strip():
        raise ValidationException("제목과 본문을 입력하세요")
    if len(data.subject) > MAX_SUBJECT or len(data.body_html) > MAX_BODY:
        raise ValidationException("제목 또는 본문이 너무 깁니다")
    try:
        mail_templates.validate_template(data.subject, data.body_html, template_key)
    except Exception as e:  # TemplateSyntaxError, SecurityError(샌드박스 위반) 등
        raise ValidationException(f"템플릿 오류: {type(e).__name__}: {e}")


def update_template(
    db: Session, template_key: str, data: schemas.NotificationTemplateUpdate, actor: models.User, ip_address: str
) -> schemas.NotificationTemplateResponse:
    _spec(template_key)
    _validate(template_key, data)
    row = db.get(models.NotificationTemplate, template_key)
    if not row:
        row = models.NotificationTemplate(template_key=template_key)
        db.add(row)
    row.subject = data.subject
    row.body_html = data.body_html
    row.updated_by = actor.user_id
    db.add(models.SystemAuditLog(actor_id=actor.user_id, action=f"NOTIFICATION_TEMPLATE_UPDATED: {template_key}", ip_address=ip_address))
    db.commit()
    db.refresh(row)
    return _to_response(template_key, row)


def reset_template(db: Session, template_key: str, actor: models.User, ip_address: str) -> schemas.NotificationTemplateResponse:
    _spec(template_key)
    row = db.get(models.NotificationTemplate, template_key)
    if row:
        db.delete(row)
        db.add(models.SystemAuditLog(actor_id=actor.user_id, action=f"NOTIFICATION_TEMPLATE_RESET: {template_key}", ip_address=ip_address))
        db.commit()
    return _to_response(template_key, None)


def preview_template(template_key: str, data: schemas.NotificationTemplateUpdate) -> schemas.NotificationPreviewResponse:
    spec = _spec(template_key)
    _validate(template_key, data)
    subject, body = mail_templates.render(template_key, spec.sample, (data.subject, data.body_html))
    return schemas.NotificationPreviewResponse(subject=subject, body_html=body)
