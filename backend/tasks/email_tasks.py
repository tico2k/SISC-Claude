"""
이메일 발송 작업 (BackgroundTasks·스케줄러에서 실행)

케이스 생성, 검토 완료, 마감 알림 등 이메일 발송 태스크
"""


from sqlalchemy.orm import Session
from datetime import datetime
from ..core.config import settings
from ..core.database import SessionLocal
from ..models import ClarificationCase, ClarificationSubmission, User, CaseStatus
from ..core.mail.services import send_template_mail
from ..core.logging_config import get_logger

logger = get_logger(__name__)



def send_case_created_email(case_id: int):
    """
    케이스 생성 알림 이메일 발송
    
    Args:
        case_id: 케이스 ID
    """
    db = SessionLocal()
    try:
        # 케이스 및 관련 사용자 정보 조회
        case = db.query(ClarificationCase).filter(
            ClarificationCase.case_id == case_id
        ).first()
        
        if not case:
            logger.warning(f"케이스를 찾을 수 없음: {case_id}")
            return
        
        employee = db.query(User).filter(
            User.user_id == case.related_employee_id
        ).first()
        
        if not employee:
            logger.warning(f"직원을 찾을 수 없음: {case.related_employee_id}")
            return
        
        # 이메일 발송
        success = send_template_mail(
            to_email=employee.user_email,
            template_name="case_created.html",
            employee_name=employee.user_name,
            employee_email=employee.user_email,
            case_id=case.case_id,
            case_type=case.case_type.value if case.case_type else "미정",
            siem_type=case.siem_type.value if case.siem_type else "미정",
            rule_title=case.rule_title or "제목 없음",
            summary=case.summary or "요약 없음",
            created_at=case.created_at.strftime("%Y-%m-%d %H:%M") if case.created_at else "",
            due_date=case.due_date.strftime("%Y-%m-%d") if case.due_date else None,
            app_url=settings.frontend_url
        )
        
        if success:
            logger.info(f"케이스 생성 이메일 발송 성공: Case #{case_id} -> {employee.user_email}")
        else:
            logger.error(f"케이스 생성 이메일 발송 실패: Case #{case_id}")
            
    except Exception as e:
        logger.error(f"케이스 생성 이메일 태스크 실패: {str(e)}", exc_info=True)
        raise e
    finally:
        db.close()



def send_case_reviewed_email(case_id: int):
    """
    케이스 검토 완료 알림 이메일 발송
    
    Args:
        case_id: 케이스 ID
    """
    db = SessionLocal()
    try:
        # 케이스 및 관련 사용자 정보 조회
        case = db.query(ClarificationCase).filter(
            ClarificationCase.case_id == case_id
        ).first()
        
        if not case:
            logger.warning(f"케이스를 찾을 수 없음: {case_id}")
            return
        
        employee = db.query(User).filter(
            User.user_id == case.related_employee_id
        ).first()
        
        if not employee:
            logger.warning(f"직원을 찾을 수 없음: {case.related_employee_id}")
            return
        
        reviewer = db.query(User).filter(
            User.user_id == case.final_reviewer_id
        ).first()
        
        # 결과 구분 (제목·본문 문구는 템플릿에서 decision으로 분기)
        if case.case_status == CaseStatus.APPROVE:
            decision = "APPROVE"
        elif case.case_status == CaseStatus.REJECT:
            decision = "REJECT"
        else:
            decision = "CLOSE"
        
        # 이메일 발송
        success = send_template_mail(
            to_email=employee.user_email,
            template_name="case_reviewed.html",
            employee_name=employee.user_name,
            employee_email=employee.user_email,
            case_id=case.case_id,
            decision=decision,
            reviewer_name=reviewer.user_name if reviewer else "관리자",
            reviewed_at=case.final_review_date.strftime("%Y-%m-%d %H:%M") if case.final_review_date else "",
            result=case.case_result.value if case.case_result else None,
            comments=case.summary or "",
            app_url=settings.frontend_url
        )
        
        if success:
            logger.info(f"케이스 검토 완료 이메일 발송 성공: Case #{case_id} -> {employee.user_email}")
        else:
            logger.error(f"케이스 검토 완료 이메일 발송 실패: Case #{case_id}")
            
    except Exception as e:
        logger.error(f"케이스 검토 완료 이메일 태스크 실패: {str(e)}", exc_info=True)
        raise e
    finally:
        db.close()



def send_deadline_reminder_email(case_id: int, days_left: int):
    """
    마감 임박 알림 이메일 발송
    
    Args:
        case_id: 케이스 ID
        days_left: 남은 일수
    """
    db = SessionLocal()
    try:
        # 케이스 및 관련 사용자 정보 조회
        case = db.query(ClarificationCase).filter(
            ClarificationCase.case_id == case_id
        ).first()
        
        if not case:
            logger.warning(f"케이스를 찾을 수 없음: {case_id}")
            return
        
        employee = db.query(User).filter(
            User.user_id == case.related_employee_id
        ).first()
        
        if not employee:
            logger.warning(f"직원을 찾을 수 없음: {case.related_employee_id}")
            return
        
        # 이메일 발송
        success = send_template_mail(
            to_email=employee.user_email,
            template_name="deadline_reminder.html",
            employee_name=employee.user_name,
            employee_email=employee.user_email,
            case_id=case.case_id,
            rule_title=case.rule_title or "제목 없음",
            days_left=days_left,
            due_date=case.due_date.strftime("%Y년 %m월 %d일") if case.due_date else "",
            app_url=settings.frontend_url
        )
        
        if success:
            logger.info(f"마감 알림 이메일 발송 성공: Case #{case_id} -> {employee.user_email}")
        else:
            logger.error(f"마감 알림 이메일 발송 실패: Case #{case_id}")
            
    except Exception as e:
        logger.error(f"마감 알림 이메일 태스크 실패: {str(e)}", exc_info=True)
        raise e
    finally:
        db.close()



def send_submission_notifications(case_id: int, submission_id: int):
    """소명 제출 후 알림: 부서장 참조 메일(지정된 경우) + 보안팀 Teams 채널(설정된 경우)

    소명 내용·첨부는 개인정보 보호를 위해 알림에 포함하지 않는다.
    """
    from ..modules.integrations.services import send_teams_message

    db = SessionLocal()
    try:
        case = db.get(ClarificationCase, case_id)
        submission = db.get(ClarificationSubmission, submission_id)
        if not case or not submission:
            logger.warning(f"소명 제출 알림 대상 없음: Case #{case_id}, Submission #{submission_id}")
            return
        employee = db.get(User, case.related_employee_id) if case.related_employee_id else None

        if employee and employee.manager_id:
            manager = db.get(User, employee.manager_id)
            if manager:
                ok = send_template_mail(
                    to_email=manager.user_email,
                    template_name="submission_cc.html",
                    manager_name=manager.user_name,
                    employee_name=employee.user_name,
                    employee_department=employee.department or "",
                    case_id=case.case_id,
                    rule_title=case.rule_title or "제목 없음",
                    submitted_at=submission.submitted_at.strftime("%Y-%m-%d %H:%M") if submission.submitted_at else "",
                )
                logger.info(f"부서장 참조 메일 {'발송' if ok else '실패'}: Case #{case_id} -> {manager.user_email}")

        send_teams_message(
            title=f"소명 제출: 케이스 #{case.case_id}",
            text="새 소명이 제출되어 심의를 기다리고 있습니다.",
            facts=[("규칙", case.rule_title or "-"), ("우선순위", case.priority.value if case.priority else "-")],
            link_url=f"{settings.frontend_url}/reviews?caseId={case.case_id}",
            db=db,
        )
    except Exception as e:
        # 알림 실패가 제출 결과에 영향을 주지 않도록 기록만 한다
        logger.error(f"소명 제출 알림 실패: Case #{case_id} - {e}", exc_info=True)
    finally:
        db.close()
