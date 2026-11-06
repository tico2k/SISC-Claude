from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
import os
from .config import settings

# DB 접속 URL: .env의 DATABASE_URL(settings) 사용.
# 이전 버전 호환을 위해 SICS_DATABASE_URL 환경 변수가 있으면 우선 적용
SQLALCHEMY_DATABASE_URL = os.getenv("SICS_DATABASE_URL") or settings.DATABASE_URL

connect_args = {}
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args=connect_args
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# SQLAlchemy 2.0 style DeclarativeBase
class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
