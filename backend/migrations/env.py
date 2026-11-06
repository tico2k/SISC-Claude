"""
Alembic 마이그레이션 환경 설정

- DB URL은 애플리케이션과 동일하게 backend.core.database.SQLALCHEMY_DATABASE_URL
  (.env의 DATABASE_URL, 또는 호환용 SICS_DATABASE_URL)을 사용한다.
- 새 모듈에서 ORM 모델을 추가하면 아래 '모델 등록' 구역에 import를 추가해야
  autogenerate가 해당 테이블을 인식한다.
"""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from backend.core.database import Base, SQLALCHEMY_DATABASE_URL

# --- 모델 등록 (Base.metadata에 테이블을 올리기 위한 import) ---
from backend import models  # noqa: F401
from backend.modules.reports import models as reports_models  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URL.replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_object(obj, name, type_, reflected, compare_to):
    """DB에는 있지만 모델에 없는 테이블(예: 등록 해제된 new_skill_items)은
    autogenerate가 DROP을 제안하지 않도록 무시한다. 테이블 삭제는 수동으로 작성할 것."""
    if type_ == "table" and reflected and compare_to is None:
        return False
    return True


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        render_as_batch=_is_sqlite(url),  # SQLite는 ALTER 제약이 있어 batch 모드 사용
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            render_as_batch=connection.dialect.name == "sqlite",
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
