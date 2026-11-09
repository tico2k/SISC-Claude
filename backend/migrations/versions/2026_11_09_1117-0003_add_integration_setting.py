"""외부 연동 설정 테이블(integration_setting) 추가

Entra ID 연동 정보를 .env/프론트 빌드 변수 대신 DB에 저장한다 (설치 후 관리자 화면에서 설정).
- main.py의 create_all이 먼저 테이블을 만들었을 수 있으므로 존재하면 건너뛴다.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "integration_setting"


def upgrade() -> None:
    if TABLE in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        TABLE,
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("tenant_id", sa.String(length=100), nullable=True),
        sa.Column("client_id", sa.String(length=100), nullable=True),
        sa.Column("client_secret", sa.String(length=500), nullable=True),
        sa.Column("mail_sender", sa.String(length=150), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["updated_by"], ["users.user_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("provider"),
    )


def downgrade() -> None:
    op.drop_table(TABLE)
