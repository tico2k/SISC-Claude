"""
케이스 워크플로우 규칙

상태 전이: UNCLASSIFIED → REQUEST → SUBMIT → APPROVE | REJECT(A/B/C) → CLOSE
- 반려 A(소명 불충분)만 재소명(REJECT → SUBMIT) 가능
- 일반 사용자는 본인 케이스만, UNCLASSIFIED/CLOSE 상태는 접근 불가
- 다른 관리자가 잠근(Case Lock) 케이스는 심의·요청·종결 불가 (잠금은 30분 후 만료)
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Request
from sqlalchemy.orm import Session

from ... import models
from ...core.exceptions import AuthorizationException, CaseStateException, ValidationException
from ...core.permissions import can_review_cases

S = models.CaseStatus
R = models.CaseResult

LOCK_TIMEOUT = timedelta(minutes=30)

# 일반 사용자에게 숨기는 상태
HIDDEN_FROM_USER = (S.UNCLASSIFIED, S.CLOSE)

# 심의 결과별 허용 사유
REVIEW_RESULTS = {
    S.APPROVE: {R.JUSTIFIED, R.MINOR_VIOLATION},
    S.REJECT: {R.INSUFFICIENT, R.EDUCATION_NEEDED, R.DISCIPLINARY_ACTION},
}


def _label(status) -> str:
    return status.value if hasattr(status, "value") else str(status)


def can_user_access_case(user: models.User, case: models.ClarificationCase) -> bool:
    """관리자이거나, 본인 케이스이면서 숨김 상태가 아닌 경우"""
    if can_review_cases(user):
        return True
    return case.related_employee_id == user.user_id and case.case_status not in HIDDEN_FROM_USER


def ensure_not_locked_by_other(case: models.ClarificationCase, user: models.User) -> None:
    """다른 관리자가 유효한 잠금을 보유 중이면 거부 (만료된 잠금은 무시)"""
    if not case.locked_by_id or case.locked_by_id == user.user_id:
        return
    if case.locked_at and case.locked_at < datetime.now() - LOCK_TIMEOUT:
        return
    raise CaseStateException("다른 관리자가 이 케이스를 검토 중입니다")


def ensure_can_request(case: models.ClarificationCase, user: models.User) -> None:
    if case.case_status != S.UNCLASSIFIED:
        raise CaseStateException(f"'{_label(case.case_status)}' 상태에서는 소명을 요청할 수 없습니다")
    ensure_not_locked_by_other(case, user)


def ensure_can_submit(case: models.ClarificationCase, user: models.User) -> None:
    if not can_user_access_case(user, case):
        raise AuthorizationException("이 케이스에 소명을 제출할 권한이 없습니다")
    if case.case_status == S.REQUEST:
        return
    if case.case_status == S.REJECT and case.case_result == R.INSUFFICIENT:
        return  # 반려 A: 재소명
    raise CaseStateException(f"'{_label(case.case_status)}' 상태에서는 소명을 제출할 수 없습니다")


def ensure_can_review(case: models.ClarificationCase, user: models.User,
                      new_status: models.CaseStatus, result: models.CaseResult) -> None:
    allowed = REVIEW_RESULTS.get(new_status)
    if allowed is None:
        raise ValidationException("심의 결과는 '승인' 또는 '반려'만 가능합니다")
    if result not in allowed:
        raise ValidationException(f"'{_label(new_status)}' 심의에 사용할 수 없는 결과입니다: {_label(result)}")
    if case.case_status != S.SUBMIT:
        raise CaseStateException(f"'{_label(case.case_status)}' 상태의 케이스는 심의할 수 없습니다")
    ensure_not_locked_by_other(case, user)


def ensure_can_close(case: models.ClarificationCase, user: models.User) -> None:
    if case.case_status == S.CLOSE:
        raise CaseStateException("이미 종결된 케이스입니다")
    ensure_not_locked_by_other(case, user)


def add_audit_log(db: Session, actor: models.User, action: str, request: Optional[Request] = None) -> None:
    """SystemAuditLog 추가 (commit은 호출자 트랜잭션에서 수행)"""
    ip = request.client.host if request is not None and request.client else "Unknown"
    db.add(models.SystemAuditLog(actor_id=actor.user_id, action=action, ip_address=ip))


# --- 심의 참고: 같은 직원의 다른 케이스 이력 ---

HISTORY_RECENT_LIMIT = 20


def employee_history(db: Session, case: models.ClarificationCase) -> dict:
    """현재 케이스를 제외한 같은 직원의 케이스 요약 (반복 위반 판단용)"""
    if not case.related_employee_id:
        return {"employee_id": None, "employee_name": None, "total": 0, "rejected": 0,
                "disciplinary": 0, "by_status": {}, "by_result": {}, "recent": []}

    others = db.query(models.ClarificationCase).filter(
        models.ClarificationCase.related_employee_id == case.related_employee_id,
        models.ClarificationCase.case_id != case.case_id,
    ).order_by(models.ClarificationCase.created_at.desc()).all()

    by_status: dict[str, int] = {}
    by_result: dict[str, int] = {}
    for c in others:
        by_status[_label(c.case_status)] = by_status.get(_label(c.case_status), 0) + 1
        if c.case_result:
            by_result[_label(c.case_result)] = by_result.get(_label(c.case_result), 0) + 1

    employee = case.related_employee
    return {
        "employee_id": case.related_employee_id,
        "employee_name": employee.user_name if employee else None,
        "total": len(others),
        "rejected": by_status.get(_label(S.REJECT), 0),
        "disciplinary": by_result.get(_label(R.DISCIPLINARY_ACTION), 0),
        "by_status": by_status,
        "by_result": by_result,
        "recent": others[:HISTORY_RECENT_LIMIT],
    }
