from sqlalchemy.orm import Session
from .database import SessionLocal
from . import models
from .models import UserRole, SiemType, CaseType, CaseStatus, CasePriority, CaseResult
from datetime import datetime, timedelta
import random
from backend.dependencies import get_password_hash

def bulk_seed():
    db = SessionLocal()
    try:
        print("Starting bulk data generation...")

        # 1. Fetch Existing Users
        # Try to find a Security Admin to act as the requester
        security_admin = db.query(models.User).filter(models.User.role == models.UserRole.SECURITY_ADMIN).first()
        
        if not security_admin:
            print("Security Admin not found. Creating one...")
            security_admin = models.User(
                user_email="security@fleitlab.com",
                user_name="Security Admin",
                hashed_password=get_password_hash("password"),
                role=models.UserRole.SECURITY_ADMIN,
                company="Fleit",
                department="Security"
            )
            db.add(security_admin)
            db.flush()

        # Fetch all users to be targets of cases
        all_users = db.query(models.User).all()
        
        # Filter out users to use as targets (can include admin, but typically regular users)
        # If no other users exist, use the admin itself or create a dummy user
        target_users = [u for u in all_users if u.user_id != security_admin.user_id]
        
        if not target_users:
            print("No other users found. Creating a general user...")
            new_user = models.User(
                    user_email="user1@fleitlab.com",
                    user_name="User 1",
                    hashed_password=get_password_hash("password"),
                    role=models.UserRole.USER,
                    company="Fleit",
                    department="Dept 1"
                )
            db.add(new_user)
            db.flush()
            target_users.append(new_user)
        
        print(f"Found {len(target_users)} target users for case generation.")
        
        db.commit()
        
        # Refresh to ensure we have IDs
        # (Already have objects with IDs from flush/query, but just to be safe if anything detached)
        
        # 2. Date Range
        start_date = datetime(2026, 2, 10)
        end_date = datetime.now()
        delta = timedelta(days=1)
        
        current_date = start_date
        total_cases = 0

        while current_date <= end_date:
            daily_case_count = random.randint(3, 10)
            print(f"Generating {daily_case_count} cases for {current_date.strftime('%Y-%m-%d')}...")
            
            for _ in range(daily_case_count): # 5-15 cases per day
                
                # Random Attributes
                c_type = random.choice(list(CaseType))
                c_priority = random.choice(list(CasePriority))
                
                # Random Status with weights (More APPROVED/REJECTED/SUBMITTED than REQUEST)
                # Weighted: Approve(30%), Reject(20%), Submit(20%), Request(10%), Unclassified(20%)
                status_roll = random.random()
                if status_roll < 0.3:
                    c_status = CaseStatus.APPROVE
                elif status_roll < 0.5:
                    c_status = CaseStatus.REJECT
                elif status_roll < 0.7:
                    c_status = CaseStatus.SUBMIT
                elif status_roll < 0.8:
                    c_status = CaseStatus.REQUEST
                else:
                    c_status = CaseStatus.UNCLASSIFIED

                # Titles based on type
                titles = {
                    CaseType.INFO_LEAK: ["대외비 문서 출력", "개인 메일로 소스코드 전송", "클라우드 스토리지 파일 업로드", "메신저로 개인정보 전송"],
                    CaseType.SECURITY_VIOLATION: ["비인가 USB 사용", "불법 소프트웨어 설치", "보안 프로그램 강제 종료", "유해 사이트 접속"],
                    CaseType.SYSTEM_ACCESS: ["비업무 시간 VPN 접속", "DB 접근 권한 과다 조회", "서버 직접 접속 시도", "관리자 페이지 접근"],
                    CaseType.AUTH_ABUSE: ["계정 공유 의심", "반복적인 로그인 실패", "타인 계정 접속 시도", "권한 상승 시도"]
                }
                c_title = random.choice(titles[c_type])
                
                # Select a random user for this case
                target_user = random.choice(target_users)

                # Case
                case = models.ClarificationCase(
                    siem_type=SiemType.SENTINEL,
                    rule_title=c_title,
                    rule_description=f"Generated sample detection for {c_type.value}",
                    incident_num=random.randint(10000, 99999),
                    case_type=c_type,
                    related_employee_id=target_user.user_id,
                    requester_id=security_admin.user_id,
                    created_at=current_date + timedelta(hours=random.randint(9, 18)), # Work hours
                    due_date=current_date + timedelta(days=3),
                    case_status=c_status,
                    priority=c_priority,
                    summary="SIEM에서 자동 탐지된 이상 징후입니다. 소명이 필요합니다.",
                    original_log_link=f"https://portal.azure.com/#asset/Microsoft_Azure_Security_Insights/Incident/subscriptions/sub-id/resourceGroups/rg-name/providers/Microsoft.OperationalInsights/workspaces/ws-name/incidents/{random.randint(1000, 9999)}"
                )
                
                # Assign result if approved/rejected
                if c_status in [CaseStatus.APPROVE, CaseStatus.REJECT]:
                    case.case_result = random.choice(list(CaseResult))
                    case.final_reviewer_id = security_admin.user_id
                    case.final_review_date = current_date + timedelta(days=1)

                db.add(case)
                db.flush() # to get case_id

                # Submission (if status is not REQUEST)
                if c_status != CaseStatus.REQUEST:
                    sub = models.ClarificationSubmission(
                        case_id=case.case_id,
                        submitter_id=target_user.user_id,
                        submitted_at=current_date + timedelta(hours=random.randint(19, 23)),
                        content="업무상 필요에 의해 진행하였습니다. 향후 주의하겠습니다.",
                        classification="BUSINESS"
                    )
                    db.add(sub)
                
                # Review (if status is APPROVE/REJECT)
                if c_status in [CaseStatus.APPROVE, CaseStatus.REJECT]:
                    review = models.ReviewHistory(
                        case_id=case.case_id,
                        reviewer_id=security_admin.user_id,
                        reviewed_at=current_date + timedelta(days=1, hours=10),
                        case_status=c_status,
                        case_result=case.case_result,
                        comments="소명 내용 확인하였습니다."
                    )
                    db.add(review)

                total_cases += 1
            
            current_date += delta

        db.commit()
        print(f"Successfully generated {total_cases} cases.")

    except Exception as e:
        print(f"Bulk seeding failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    bulk_seed()

