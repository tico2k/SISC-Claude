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
    매일 새벽 2시 실행 - 만료된 케이스 정리
    
    종료 후 90일이 지난 케이스를 아카이빙
    """
    db = SessionLocal()
    job_id = "archive_old_cases"
    job_name = "만료/종료 케이스 자동 아카이빙"
    execution_type = "MANUAL" if is_manual else "AUTO"
    
    try:
        archive_date = datetime.now() - timedelta(days=90)
        logger.info(f"만료 케이스 정리 시작: {archive_date} 이전 케이스")
        
        # 종료 후 90일 지난 케이스 조회
        old_cases = db.query(ClarificationCase).filter(
            ClarificationCase.final_review_date < archive_date,
            ClarificationCase.case_status.in_([CaseStatus.APPROVE, CaseStatus.REJECT, CaseStatus.CLOSE])
        ).all()
        
        logger.info(f"아카이빙 대상 케이스: {len(old_cases)}건")
        
        # TODO: 실제 아카이빙 로직 구현 (파일로 저장, 별도 DB로 이동 등)
        # 현재는 로깅만 수행
        for case in old_cases:
            logger.info(f"아카이빙: Case #{case.case_id}, 종료일: {case.final_review_date}")
        
        record_job_log(db, job_id, job_name, "SUCCESS", execution_type, len(old_cases), f"정상 처리 완료. ({len(old_cases)}건 처리)")
        return {"archived_count": len(old_cases)}
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"만료 케이스 정리 실패: {error_msg}", exc_info=True)
        record_job_log(db, job_id, job_name, "FAILED", execution_type, 0, f"실패: {error_msg}")
        raise
    finally:
        db.close()
