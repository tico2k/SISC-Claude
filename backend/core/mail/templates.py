"""
알림 메일 템플릿 목록과 렌더링

- 기본 본문: backend/templates/email/<key> 파일, 기본 제목: 아래 TEMPLATES의 subject
- 관리자가 화면에서 수정하면 DB(notification_template)에 저장되고, 저장본이 있으면 그것을 우선 사용
- 관리자가 입력한 템플릿은 Jinja2 샌드박스로 렌더링 (서버 측 템플릿 주입 방지), 본문은 HTML 자동 이스케이프
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, TemplateError, select_autoescape
from jinja2.sandbox import SandboxedEnvironment

TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates" / "email"

_file_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)
_body_sandbox = SandboxedEnvironment(autoescape=True)
_subject_sandbox = SandboxedEnvironment(autoescape=False)

PREFIX = "[Fleit InsiderGuard]"


@dataclass(frozen=True)
class TemplateSpec:
    name: str
    description: str
    subject: str
    variables: list = field(default_factory=list)
    sample: dict = field(default_factory=dict)


_SAMPLE_COMMON = {"case_id": 1024, "rule_title": "대용량 파일 외부 전송", "app_url": "https://sics.example.com"}

TEMPLATES: dict[str, TemplateSpec] = {
    "request_mail.html": TemplateSpec(
        name="소명 요청",
        description="보안팀이 소명을 요청할 때 직원에게 발송",
        subject="[{{ priority }}] 보안 소명 요청 안내 - #{{ incident_num }}",
        variables=["user_name", "priority", "priority_class", "incident_num", "rule_title", "due_date", "request_reason", "login_url"],
        sample={"user_name": "홍길동", "priority": "높음", "priority_class": "badge-urgent", "incident_num": "1024",
                "rule_title": "대용량 파일 외부 전송", "due_date": "2026년 12월 31일",
                "request_reason": "업무 목적 여부를 확인하고자 합니다.", "login_url": "https://sics.example.com/cases/1024"},
    ),
    "case_created.html": TemplateSpec(
        name="케이스 생성",
        description="보안팀이 케이스를 등록할 때 직원에게 발송",
        subject=PREFIX + " 새로운 소명 케이스 #{{ case_id }}",
        variables=["employee_name", "employee_email", "case_id", "case_type", "siem_type", "rule_title", "summary", "created_at", "due_date", "app_url"],
        sample={**_SAMPLE_COMMON, "employee_name": "홍길동", "employee_email": "hong@example.com", "case_type": "정보유출",
                "siem_type": "Sentinel", "summary": "탐지 요약", "created_at": "2026-11-09 10:00", "due_date": "2026-11-16"},
    ),
    "case_reviewed.html": TemplateSpec(
        name="심의 결과",
        description="승인·반려·종결 시 직원에게 발송",
        subject=(PREFIX + " 케이스 #{{ case_id }} "
                 "{% if decision == 'APPROVE' %}승인 완료{% elif decision == 'REJECT' %}반려{% else %}종결{% endif %}"),
        variables=["employee_name", "employee_email", "case_id", "decision", "reviewer_name", "reviewed_at", "result", "comments", "app_url"],
        sample={**_SAMPLE_COMMON, "employee_name": "홍길동", "employee_email": "hong@example.com", "decision": "APPROVE",
                "reviewer_name": "보안관리자", "reviewed_at": "2026-11-09 15:00", "result": "정당 사유", "comments": ""},
    ),
    "deadline_reminder.html": TemplateSpec(
        name="기한 임박",
        description="소명 기한 전(기본 3일·1일 전) 직원에게 발송",
        subject=PREFIX + " 케이스 #{{ case_id }} 마감 {{ days_left }}일 전",
        variables=["employee_name", "employee_email", "case_id", "rule_title", "days_left", "due_date", "app_url"],
        sample={**_SAMPLE_COMMON, "employee_name": "홍길동", "employee_email": "hong@example.com", "days_left": 3, "due_date": "2026년 11월 16일"},
    ),
    "overdue_notice.html": TemplateSpec(
        name="기한 초과 (직원·부서장)",
        description="소명 기한이 지난 날 직원과 지정된 부서장에게 1회 발송 (is_manager로 구분)",
        subject=PREFIX + " 케이스 #{{ case_id }} 소명 기한 초과{% if is_manager %} (참조: {{ employee_name }}){% endif %}",
        variables=["recipient_name", "employee_name", "is_manager", "case_id", "rule_title", "due_date", "overdue_days", "case_url"],
        sample={**_SAMPLE_COMMON, "recipient_name": "홍길동", "employee_name": "홍길동", "is_manager": False,
                "due_date": "2026-11-08", "overdue_days": 1, "case_url": "https://sics.example.com/cases/1024"},
    ),
    "overdue_digest.html": TemplateSpec(
        name="기한 초과 요약 (보안팀)",
        description="새로 기한이 지난 케이스 목록을 보안관리자에게 발송",
        subject=PREFIX + " 소명 기한 초과 {{ count }}건",
        variables=["count", "cases (case_id, rule_title, employee_name, due_date, overdue_days)", "app_url"],
        sample={"count": 1, "app_url": "https://sics.example.com",
                "cases": [{"case_id": 1024, "rule_title": "대용량 파일 외부 전송", "employee_name": "홍길동", "due_date": "2026-11-08", "overdue_days": 1}]},
    ),
    "submission_cc.html": TemplateSpec(
        name="소명 제출 (부서장 참조)",
        description="직원이 소명을 제출하면 지정된 부서장에게 참조로 발송 (소명 내용은 포함하지 않음)",
        subject=PREFIX + " {{ employee_name }}님 소명 제출 안내 (참조) - 케이스 #{{ case_id }}",
        variables=["manager_name", "employee_name", "employee_department", "case_id", "rule_title", "submitted_at"],
        sample={**_SAMPLE_COMMON, "manager_name": "김부장", "employee_name": "홍길동", "employee_department": "영업팀",
                "submitted_at": "2026-11-09 11:00"},
    ),
}


def default_body(template_key: str) -> str:
    return (TEMPLATE_DIR / template_key).read_text(encoding="utf-8")


def validate_template(subject: str, body_html: str, template_key: str) -> None:
    """문법 오류·샌드박스 위반이 있으면 TemplateError. 샘플 값으로 실제 렌더링까지 확인한다"""
    sample = TEMPLATES[template_key].sample
    _subject_sandbox.from_string(subject).render(**sample)
    _body_sandbox.from_string(body_html).render(**sample)


def _clean_subject(subject: str) -> str:
    # 메일 헤더 주입 방지: 줄바꿈 제거
    return " ".join(subject.split())


def render(template_key: str, context: dict, override: Optional[tuple[str, str]] = None) -> tuple[str, str]:
    """(제목, 본문 HTML). override=(subject, body_html)가 있으면 샌드박스로, 없으면 기본 파일로 렌더링"""
    spec = TEMPLATES[template_key]
    if override:
        subject_t, body_t = override
        subject = _subject_sandbox.from_string(subject_t).render(**context)
        body = _body_sandbox.from_string(body_t).render(**context)
    else:
        subject = _subject_sandbox.from_string(spec.subject).render(**context)
        body = _file_env.get_template(template_key).render(**context)
    return _clean_subject(subject), body


__all__ = ["TEMPLATES", "TemplateSpec", "TemplateError", "default_body", "validate_template", "render"]
