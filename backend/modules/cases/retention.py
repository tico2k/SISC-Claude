"""
케이스 보존기간 경과 후 개인정보 파기(익명화)

- 대상: 승인·반려·종결 상태이고 최종 처리 후 settings.CASE_RETENTION_DAYS가 지난 케이스
- 제외: 증거 보존(legal_hold) 지정 케이스, 이미 익명화된 케이스
- 처리: 직원 연결·요약·원본 링크·소명 내용·심의 의견을 지우고 첨부파일은 삭제
        케이스 번호·유형·상태·결과·날짜는 남겨 통계와 추이를 유지
"""
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from ... import models
from ...core.config import settings
from ...core.logging_config import get_logger

logger = get_logger(__name__)

S = models.CaseStatus
FINAL_STATUSES = (S.APPROVE, S.REJECT, S.CLOSE)
REDACTED = "[보존기간 경과로 파기됨]"


def find_expired_cases(db: Session, now: Optional[datetime] = None) -> list[models.ClarificationCase]:
    cutoff = (now or datetime.now()) - timedelta(days=settings.CASE_RETENTION_DAYS)
    return db.query(models.ClarificationCase).filter(
        models.ClarificationCase.case_status.in_(FINAL_STATUSES),
        models.ClarificationCase.final_review_date.isnot(None),
        models.ClarificationCase.final_review_date < cutoff,
        models.ClarificationCase.legal_hold.is_(False),
        models.ClarificationCase.anonymized_at.is_(None),
    ).all()


def _delete_file(path_str: str) -> bool:
    """업로드 폴더 하위 파일만 삭제 (경로 조작 방지)"""
    upload_root = Path(settings.UPLOAD_DIR).resolve()
    target = Path(path_str).resolve()
    if not target.is_relative_to(upload_root):
        logger.error(f"파기 중 업로드 폴더 밖 경로 무시: {target}")
        return False
    try:
        target.unlink(missing_ok=True)
        return True
    except OSError as e:
        logger.error(f"첨부파일 삭제 실패: {target} - {e}")
        return False


def anonymize_case(db: Session, case: models.ClarificationCase) -> int:
    """케이스 하나를 익명화하고 삭제한 첨부 수를 반환 (commit은 호출자가 수행)"""
    attachments = list(case.attachments)
    for submission in case.submissions:
        attachments.extend(submission.attachments)
        submission.content = REDACTED
        submission.submitter_id = None
        submission.classification = None

    deleted = 0
    for attachment in attachments:
        if _delete_file(attachment.file_path):
            deleted += 1
        db.delete(attachment)

    for review in case.review_history:
        review.comments = REDACTED if review.comments else None

    case.related_employee_id = None
    case.summary = REDACTED
    case.rule_description = None
    case.original_log_link = None
    case.locked_by_id = None
    case.locked_at = None
    case.anonymized_at = datetime.now()

    db.add(models.SystemAuditLog(
        actor_id=None,
        action=f"CASE_ANONYMIZED: Case {case.case_id} (retention {settings.CASE_RETENTION_DAYS}d, files {deleted})",
        ip_address="system",
    ))
    return deleted
