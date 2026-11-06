"""기존 운영 DB의 레거시 인덱스 이름을 모델 기준으로 정렬

초기 버전에서 SQL 스크립트로 만든 인덱스 이름(idx_submission_case 등)과
현재 ORM 모델의 인덱스 이름이 달라 생긴 차이를 맞춘다.
- 존재 여부를 확인하고 실행하므로 신규 설치(baseline로 생성된 DB)에서는 아무 작업도 하지 않는다.
- 데이터는 변경하지 않는다 (인덱스만 삭제/생성).

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (테이블, 레거시 인덱스명) — 모델 인덱스와 중복되거나 PK와 중복되어 제거
LEGACY_INDEXES = [
    ("clarification_submission", "idx_submission_case"),
    ("clarification_submission", "idx_submitter"),
    ("login_history", "idx_login_user"),
    ("review_history", "idx_review_case"),
    ("review_history", "idx_reviewer"),
    ("system_job_configuration", "ix_system_job_configuration_job_id"),
]

# (테이블, 모델 인덱스명, 컬럼) — 없으면 생성
MODEL_INDEXES = [
    ("clarification_submission", "idx_submission_case_id", ["case_id"]),
    ("clarification_submission", "idx_submission_submitter_id", ["submitter_id"]),
    ("clarification_submission", "idx_submitted_at", ["submitted_at"]),
    ("login_history", "idx_login_user_id", ["user_id"]),
    ("review_history", "idx_review_case_id", ["case_id"]),
    ("review_history", "idx_review_reviewer_id", ["reviewer_id"]),
    ("review_history", "idx_reviewed_at", ["reviewed_at"]),
    ("siem_sync_history", "idx_siem_sync_history_time", ["execution_time"]),
]


def _existing_indexes(table: str) -> set:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return set()
    return {ix["name"] for ix in inspector.get_indexes(table)}


def upgrade() -> None:
    for table, name in LEGACY_INDEXES:
        if name in _existing_indexes(table):
            op.drop_index(name, table_name=table)
    for table, name, columns in MODEL_INDEXES:
        if name not in _existing_indexes(table):
            op.create_index(name, table, columns)


def downgrade() -> None:
    # 레거시 이름은 운영 DB에만 있던 것이므로 되돌리지 않는다 (모델 인덱스는 baseline 소관)
    pass
