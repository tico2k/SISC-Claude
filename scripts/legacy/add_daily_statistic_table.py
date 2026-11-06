import os
import sys

# 프로젝트 루트 경로를 sys.path에 추가 (backend 패키지 임포트를 위해)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from backend.models import DailyStatistic
from backend.core.database import engine

def create_table():
    print("Creating daily_statistic table...")
    DailyStatistic.__table__.create(engine, checkfirst=True)
    print("Creation check finished.")

if __name__ == "__main__":
    create_table()
