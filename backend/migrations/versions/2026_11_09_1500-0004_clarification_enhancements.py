"""소명 기능 개선: 기한 초과·증거 무결성·보존/파기·부서장 참조·알림 템플릿·Teams

- users.manager_id: 부서장(참조 알림 수신자)
- clarification_case: overdue_notified_at, legal_hold, legal_hold_reason, anonymized_at
- clarification_attachment.sha256: 업로드 시점 해시
- integration_setting.webhook_url: Teams 채널 웹훅(암호문)
- notification_template: 관리자가 수정한 메일 템플릿
- main.py의 create_all이 테이블을 먼저 만들었을 수 있으므로 존재 여부를 확인하고 실행한다

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    if "manager_id" not in _columns("users"):
        # SQLite는 FK 추가에 테이블 재생성이 필요하므로 batch 모드 사용
        with op.batch_alter_table("users") as batch:
            batch.add_column(sa.Column("manager_id", sa.Integer(), nullable=True))
            batch.create_foreign_key("fk_users_manager_id_users", "users", ["manager_id"], ["user_id"], ondelete="SET NULL")

    case_cols = _columns("clarification_case")
    with op.batch_alter_table("clarification_case") as batch:
        if "overdue_notified_at" not in case_cols:
            batch.add_column(sa.Column("overdue_notified_at", sa.DateTime(), nullable=True))
        if "legal_hold" not in case_cols:
            batch.add_column(sa.Column("legal_hold", sa.Boolean(), server_default=sa.false(), nullable=False))
        if "legal_hold_reason" not in case_cols:
            batch.add_column(sa.Column("legal_hold_reason", sa.Text(), nullable=True))
        if "anonymized_at" not in case_cols:
            batch.add_column(sa.Column("anonymized_at", sa.DateTime(), nullable=True))

    if "sha256" not in _columns("clarification_attachment"):
        with op.batch_alter_table("clarification_attachment") as batch:
            batch.add_column(sa.Column("sha256", sa.String(length=64), nullable=True))

    if "webhook_url" not in _columns("integration_setting"):
        with op.batch_alter_table("integration_setting") as batch:
            batch.add_column(sa.Column("webhook_url", sa.String(length=1000), nullable=True))

    if "notification_template" not in inspector.get_table_names():
        op.create_table(
            "notification_template",
            sa.Column("template_key", sa.String(length=100), nullable=False),
            sa.Column("subject", sa.String(length=500), nullable=False),
            sa.Column("body_html", sa.Text(), nullable=False),
            sa.Column("updated_by", sa.Integer(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.ForeignKeyConstraint(["updated_by"], ["users.user_id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("template_key"),
        )


def downgrade() -> None:
    op.drop_table("notification_template")
    with op.batch_alter_table("integration_setting") as batch:
        batch.drop_column("webhook_url")
    with op.batch_alter_table("clarification_attachment") as batch:
        batch.drop_column("sha256")
    with op.batch_alter_table("clarification_case") as batch:
        batch.drop_column("anonymized_at")
        batch.drop_column("legal_hold_reason")
        batch.drop_column("legal_hold")
        batch.drop_column("overdue_notified_at")
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("fk_users_manager_id_users", type_="foreignkey")
        batch.drop_column("manager_id")
