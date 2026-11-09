"""
배치 작업 Celery 태스크

정기 실행되는 배치 작업 (통계 생성, 보고서, 마감 알림 일괄 발송 등)
"""


from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from datetime import datetime, timedelta, date
from typing import Optional
from ..core.database import SessionLocal
from ..models import ClarificationCase, CaseStatus, DailyStatistic, ReviewHistory, ClarificationSubmission, CaseResult, WeeklyReport, BackgroundJobLog
from .email_tasks import send_deadline_reminder_email
from ..core.config import settings
from ..core.logging_config import get_logger

logger = get_logger(__name__)

def record_job_log(db: Session, job_id: str, job_name: str, status: str, execution_type: str, records_processed: int = 0, message: str = None):
    """백그라운드 작업 실행 로그 기록"""
    try:
        log = BackgroundJobLog(
            job_id=job_id,
            job_name=job_name,
            status=status,
            execution_type=execution_type,
            records_processed=records_processed,
            message=message
        )
        db.add(log)
        db.commit()
    except Exception as e:
        logger.error(f"작업 로그 기록 실패 ({job_id}): {str(e)}")
        db.rollback()



def send_deadline_reminders(is_manual: bool = False):
    """
    매일 오전 9시 실행 - 마감 임박 케이스 알림 발송
    
    설정된 일수(기본: 3일, 1일)에 맞춰 알림 발송
    """
    db = SessionLocal()
    job_id = "send_deadline_reminders"
    job_name = "소명 기한 임박 안내 메일 일괄 발송"
    execution_type = "MANUAL" if is_manual else "AUTO"
    
    try:
        today = datetime.now().date()
        reminder_days = getattr(settings, 'DEADLINE_REMINDER_DAYS', [3, 1])
        
        logger.info(f"마감 알림 배치 시작: {reminder_days}일 전 케이스 조회")
        
        total_sent = 0
        
        for days in reminder_days:
            target_date = today + timedelta(days=days)
            
            # 마감일이 target_date인 REQUEST 상태 케이스 조회
            cases = db.query(ClarificationCase).filter(
                ClarificationCase.due_date >= target_date,
                ClarificationCase.due_date < target_date + timedelta(days=1),
                ClarificationCase.case_status == CaseStatus.REQUEST
            ).all()
            
            logger.info(f"{days}일 전 마감 케이스: {len(cases)}건")
            
            for case in cases:
                # 직접 호출 (또는 필요 시 asyncio.create_task 사용)
                send_deadline_reminder_email(case.case_id, days)
                total_sent += 1
        
        logger.info(f"마감 알림 배치 완료: 총 {total_sent}건 발송")
        record_job_log(db, job_id, job_name, "SUCCESS", execution_type, total_sent, f"정상 처리 완료. ({total_sent}건 발송)")
        return {"total_sent": total_sent}
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"마감 알림 배치 실패: {error_msg}", exc_info=True)
        record_job_log(db, job_id, job_name, "FAILED", execution_type, 0, f"실패: {error_msg}")
        raise
    finally:
        db.close()



def generate_daily_statistics(target_date: Optional[date] = None, is_manual: bool = False):
    """
    매일 자정 실행 - 일일 통계 생성
    
    기본적으로 전날의 통계를 계산하지만, target_date를 지정할 경우 해당 일자에 대한 통계를 재작성/생성합니다.
    """
    db = SessionLocal()
    job_id = "generate_daily_statistics"
    job_name = "일일 케이스 및 통계 지표 자동 생성"
    execution_type = "MANUAL" if is_manual or target_date else "AUTO"
    
    try:
        if target_date:
            yesterday = target_date
            logger.info(f"일일 통계 수동 생성 시작 (지정 일자): {yesterday}")
        else:
            yesterday = datetime.now().date() - timedelta(days=1)
            logger.info(f"일일 통계 자동 배치 시작: {yesterday}")
            
        # 사용자가 원하는 집계 방식:
        # "해당 일자(yesterday)에 생성(발생)된 케이스들이 현재 각각 어떤 상태(Status)에 놓여있는가?"
        
        # 1. 미확인 (Unclassified): 생성일이 yesterday이고 현재 상태가 UNCLASSIFIED
        unclassified_count = db.query(func.count(ClarificationCase.case_id)).filter(
            func.date(ClarificationCase.created_at) == yesterday,
            ClarificationCase.case_status == CaseStatus.UNCLASSIFIED
        ).scalar() or 0
        
        # 2. 요청 (Request): 생성일이 yesterday이고 현재 상태가 REQUEST
        request_count = db.query(func.count(ClarificationCase.case_id)).filter(
            func.date(ClarificationCase.created_at) == yesterday,
            ClarificationCase.case_status == CaseStatus.REQUEST
        ).scalar() or 0
        
        # 3. 제출 (Submit): 생성일이 yesterday이고 현재 상태가 SUBMIT
        submit_count = db.query(func.count(ClarificationCase.case_id)).filter(
            func.date(ClarificationCase.created_at) == yesterday,
            ClarificationCase.case_status == CaseStatus.SUBMIT
        ).scalar() or 0

        # 4. 검토 완료 (Reviewed): 생성일이 yesterday이고 현재 상태가 승인/반려/종결 중 하나
        reviewed_count = db.query(func.count(ClarificationCase.case_id)).filter(
            func.date(ClarificationCase.created_at) == yesterday,
            ClarificationCase.case_status.in_([CaseStatus.APPROVE, CaseStatus.REJECT, CaseStatus.CLOSE])
        ).scalar() or 0
        
        stats = {
            "date": str(yesterday),
            "unclassified": unclassified_count,
            "request": request_count,
            "submit": submit_count,
            "reviewed": reviewed_count
        }
        
        # 통계 DB 저장 (upsert 방식 적용)
        existing_stat = db.query(DailyStatistic).filter(
            func.date(DailyStatistic.stat_date) == yesterday
        ).first()

        if existing_stat:
            existing_stat.unclassified_count = stats["unclassified"]
            existing_stat.request_count = stats["request"]
            existing_stat.submit_count = stats["submit"]
            existing_stat.reviewed_count = stats["reviewed"]
            logger.info(f"일일 통계 업데이트 완료: {stats}")
        else:
            new_stat = DailyStatistic(
                stat_date=yesterday,
                unclassified_count=stats["unclassified"],
                request_count=stats["request"],
                submit_count=stats["submit"],
                reviewed_count=stats["reviewed"]
            )
            db.add(new_stat)
            logger.info(f"새 일일 통계 생성 완료: {stats}")

        db.commit()
        record_job_log(db, job_id, job_name, "SUCCESS", execution_type, 1, f"정상 처리 완료. (대상일: {yesterday})")
        return stats
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"일일 통계 생성/저장 실패: {error_msg}", exc_info=True)
        db.rollback()
        record_job_log(db, job_id, job_name, "FAILED", execution_type, 0, f"실패: {error_msg}")
        raise
    finally:
        db.close()



def generate_weekly_report(target_date: Optional[date] = None, is_manual: bool = False):
    """
    매주 월요일 오전 8시 실행 - 주간 보고서 생성
    
    지난주의 케이스 처리 현황을 요약한 보고서 생성
    """
    db = SessionLocal()
    job_id = "generate_weekly_report"
    job_name = "주간 보안 소명 진행률 리포트 생성"
    execution_type = "MANUAL" if is_manual or target_date else "AUTO"
    
    try:
        # 지난주 월요일~일요일
        if target_date:
            today = target_date
        else:
            today = datetime.now().date()
            
        days_since_monday = today.weekday()
        last_monday = today - timedelta(days=days_since_monday + 7)
        last_sunday = last_monday + timedelta(days=6)
        
        logger.info(f"주간 보고서 생성 시작: {last_monday} ~ {last_sunday}")
        
        # 지난주 통계
        created_count = db.query(func.count(ClarificationCase.case_id)).filter(
            ClarificationCase.created_at >= last_monday,
            ClarificationCase.created_at < last_sunday + timedelta(days=1)
        ).scalar()
        
        approved_count = db.query(func.count(ClarificationCase.case_id)).filter(
            ClarificationCase.final_review_date >= last_monday,
            ClarificationCase.final_review_date < last_sunday + timedelta(days=1),
            ClarificationCase.case_status == CaseStatus.APPROVE
        ).scalar()
        
        rejected_count = db.query(func.count(ClarificationCase.case_id)).filter(
            ClarificationCase.final_review_date >= last_monday,
            ClarificationCase.final_review_date < last_sunday + timedelta(days=1),
            ClarificationCase.case_status == CaseStatus.REJECT
        ).scalar()
        
        report = {
            "week_start": str(last_monday),
            "week_end": str(last_sunday),
            "created": created_count or 0,
            "approved": approved_count or 0,
            "rejected": rejected_count or 0,
        }
        
        # 주간 보고서 DB 저장 (해당 주차 데이터가 있으면 업데이트)
        existing_report = db.query(WeeklyReport).filter(
            func.date(WeeklyReport.week_start) == last_monday
        ).first()

        if existing_report:
            existing_report.created_count = report["created"]
            existing_report.approved_count = report["approved"]
            existing_report.rejected_count = report["rejected"]
            existing_report.generated_at = func.now()
            logger.info(f"주간 보고서 업데이트 완료: {report}")
        else:
            new_report = WeeklyReport(
                week_start=last_monday,
                week_end=last_sunday,
                created_count=report["created"],
                approved_count=report["approved"],
                rejected_count=report["rejected"]
            )
            db.add(new_report)
            logger.info(f"새 주간 보고서 생성 완료: {report}")
            
        db.commit()
        record_job_log(db, job_id, job_name, "SUCCESS", execution_type, 1, f"정상 처리 완료. (대상주: {last_monday} ~ {last_sunday})")
        return report
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"주간 보고서 생성 실패: {error_msg}", exc_info=True)
        record_job_log(db, job_id, job_name, "FAILED", execution_type, 0, f"실패: {error_msg}")
        raise
    finally:
        db.close()



def archive_old_cases(is_manual: bool = False):
    """
    보존기간이 지난 종결 케이스의 개인정보 파기(익명화) — 기본 매일 02:00

    기존 작업 ID(archive_old_cases)를 그대로 사용한다. 보존기간은 settings.CASE_RETENTION_DAYS,
    증거 보존(legal hold) 지정 케이스는 제외 (backend/modules/cases/retention.py)
    """
    from ..modules.cases import retention

    db = SessionLocal()
    job_id = "archive_old_cases"
    job_name = RETENTION_JOB_NAME
    execution_type = "MANUAL" if is_manual else "AUTO"

    try:
        cases = retention.find_expired_cases(db)
        logger.info(f"보존기간 경과 케이스 파기 시작: {len(cases)}건 (보존 {settings.CASE_RETENTION_DAYS}일)")
        files = 0
        for case in cases:
            files += retention.anonymize_case(db, case)
            db.commit()  # 건별 커밋: 중간에 실패해도 처리된 건은 유지

        msg = f"정상 처리 완료. (익명화 {len(cases)}건, 첨부 삭제 {files}건)"
        record_job_log(db, job_id, job_name, "SUCCESS", execution_type, len(cases), msg)
        return {"anonymized_count": len(cases), "deleted_files": files}

    except Exception as e:
        db.rollback()
        error_msg = str(e)
        logger.error(f"보존기간 경과 케이스 파기 실패: {error_msg}", exc_info=True)
        record_job_log(db, job_id, job_name, "FAILED", execution_type, 0, f"실패: {error_msg}")
        raise
    finally:
        db.close()


RETENTION_JOB_NAME = "보존기간 경과 케이스 개인정보 파기(익명화)"


def notify_overdue_cases(is_manual: bool = False):
    """
    소명 기한이 지난 '요청' 케이스 알림 — 기본 매일 09:30

    상태는 바꾸지 않는다. 케이스마다 한 번만 알림(overdue_notified_at 기록):
    직원·지정된 부서장에게 메일, 보안관리자에게 요약 메일, Teams 채널(설정 시)에 요약
    """
    from ..models import User, UserRole
    from ..core.mail.services import send_template_mail
    from ..modules.integrations.services import send_teams_message

    db = SessionLocal()
    job_id = "notify_overdue_cases"
    job_name = "소명 기한 초과 알림 발송"
    execution_type = "MANUAL" if is_manual else "AUTO"

    try:
        now = datetime.now()
        cases = db.query(ClarificationCase).filter(
            ClarificationCase.case_status == CaseStatus.REQUEST,
            ClarificationCase.due_date < now,
            ClarificationCase.overdue_notified_at.is_(None),
        ).order_by(ClarificationCase.due_date.asc()).all()

        digest = []
        for case in cases:
            employee = db.get(User, case.related_employee_id) if case.related_employee_id else None
            overdue_days = max((now.date() - case.due_date.date()).days, 1)
            common = dict(
                case_id=case.case_id,
                rule_title=case.rule_title or "제목 없음",
                due_date=case.due_date.strftime("%Y-%m-%d"),
                overdue_days=overdue_days,
                case_url=f"{settings.frontend_url}/cases/{case.case_id}",
                employee_name=employee.user_name if employee else "-",
            )
            if employee:
                send_template_mail(to_email=employee.user_email, template_name="overdue_notice.html",
                                   recipient_name=employee.user_name, is_manager=False, **common)
                manager = db.get(User, employee.manager_id) if employee.manager_id else None
                if manager:
                    send_template_mail(to_email=manager.user_email, template_name="overdue_notice.html",
                                       recipient_name=manager.user_name, is_manager=True, **common)
            case.overdue_notified_at = now
            digest.append({k: common[k] for k in ("case_id", "rule_title", "employee_name", "due_date", "overdue_days")})
        db.commit()

        if digest:
            admins = db.query(User).filter(User.role == UserRole.SECURITY_ADMIN).all()
            for admin in admins:
                send_template_mail(to_email=admin.user_email, template_name="overdue_digest.html",
                                   count=len(digest), cases=digest, app_url=settings.frontend_url)
            send_teams_message(
                title=f"소명 기한 초과 {len(digest)}건",
                text="오늘 새로 소명 기한이 지난 케이스입니다. 직원에게 개별 안내 메일을 보냈습니다.",
                facts=[(f"#{c['case_id']}", f"{c['rule_title']} ({c['overdue_days']}일 경과)") for c in digest[:10]],
                link_url=f"{settings.frontend_url}/reviews",
                db=db,
            )

        msg = f"정상 처리 완료. (기한 초과 {len(digest)}건 알림)"
        record_job_log(db, job_id, job_name, "SUCCESS", execution_type, len(digest), msg)
        return {"overdue_notified": len(digest)}

    except Exception as e:
        db.rollback()
        error_msg = str(e)
        logger.error(f"기한 초과 알림 실패: {error_msg}", exc_info=True)
        record_job_log(db, job_id, job_name, "FAILED", execution_type, 0, f"실패: {error_msg}")
        raise
    finally:
        db.close()
