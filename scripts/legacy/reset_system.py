import os
import sys

# Add the current directory to sys.path to import modules correctly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from backend.core.database import SessionLocal, engine
from backend import models
from backend.models import UserRole
from passlib.context import CryptContext

# Security Configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def reset_system():
    """
    1. 모든 테이블의 데이터를 삭제합니다.
    2. 필수 관리자 계정 3개(System, Security, Audit)를 생성합니다.
    """
    db = SessionLocal()
    try:
        print("Starting system reset...")
        
        # 1. 든 데이터 삭제 (FK 제약 조건을 고려하여 역순 또는 CASCADE 고려)
        print("Purging all existing data...")
        db.query(models.LoginHistory).delete()
        db.query(models.SystemAuditLog).delete()
        db.query(models.ReviewHistory).delete()
        db.query(models.ClarificationAttachment).delete()
        db.query(models.ClarificationSubmission).delete()
        db.query(models.ClarificationCase).delete()
        db.query(models.SiemConfiguration).delete()
        db.query(models.User).delete()
        
        db.commit()
        print("All data purged successfully.")

        # 2. 필수 관리자 계정 생성
        print("Creating default administrative accounts...")
        
        admin_users = [
            {
                "email": "system@fleitlab.com",
                "name": "시스템관리자",
                "role": UserRole.SYSTEM_ADMIN,
                "dept": "IT운영팀"
            },
            {
                "email": "security@fleitlab.com",
                "name": "보안관리자",
                "role": UserRole.SECURITY_ADMIN,
                "dept": "정보보안팀"
            },
            {
                "email": "audit@fleitlab.com",
                "name": "감사팀",
                "role": UserRole.AUDIT_TEAM,
                "dept": "준법감시팀"
            }
        ]

        for user_data in admin_users:
            new_user = models.User(
                user_email=user_data["email"],
                user_name=user_data["name"],
                hashed_password=get_password_hash("password123"), # 초기 비밀번호
                company="Fleit Lab",
                department=user_data["dept"],
                role=user_data["role"]
            )
            db.add(new_user)
            print(f"Created {user_data['role'].value}: {user_data['email']}")

        db.commit()
        print("System reset and minimal admin setup completed.")

    except Exception as e:
        print(f"Error during system reset: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    reset_system()
