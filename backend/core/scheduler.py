from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
from .logging_config import get_logger
from ..tasks import batch_tasks, siem_tasks

logger = get_logger(__name__)

executors = {
    'default': ThreadPoolExecutor(20)
}

job_defaults = {
    'coalesce': True,
    'max_instances': 1,
    'misfire_grace_time': 3600
}

scheduler = AsyncIOScheduler(
    timezone="Asia/Seoul",
    executors=executors,
    job_defaults=job_defaults
)

def start_scheduler():
    """스케줄러 시작 및 작업 등록"""
    if not scheduler.running:
        try:
            from ..core.database import SessionLocal
            from .. import models
            
            db = SessionLocal()
            try:
                # 1. 시스템 기본 작업 등록/시딩
                system_jobs = [
                    {"id": "send_deadline_reminders", "name": "소명 기한 임박 안내 메일 일괄 발송", "cron": "0 9 * * *", "func": batch_tasks.send_deadline_reminders},
                    {"id": "generate_daily_statistics", "name": "일일 케이스 및 통계 지표 자동 생성", "cron": "0 0 * * *", "func": batch_tasks.generate_daily_statistics},
                    {"id": "generate_weekly_report", "name": "주간 보안 소명 진행률 리포트 생성", "cron": "0 8 * * 1", "func": batch_tasks.generate_weekly_report},
                    {"id": "archive_old_cases", "name": batch_tasks.RETENTION_JOB_NAME, "cron": "0 2 * * *", "func": batch_tasks.archive_old_cases},
                    {"id": "notify_overdue_cases", "name": "소명 기한 초과 알림 발송", "cron": "30 9 * * *", "func": batch_tasks.notify_overdue_cases},
                ]

                for job_info in system_jobs:
                    # DB에서 설정 조회
                    config = db.query(models.SystemJobConfiguration).filter(
                        models.SystemJobConfiguration.job_id == job_info["id"]
                    ).first()

                    if not config:
                        # 초기 시딩
                        config = models.SystemJobConfiguration(
                            job_id=job_info["id"],
                            job_name=job_info["name"],
                            cron_expression=job_info["cron"],
                            is_active=True
                        )
                        db.add(config)
                        db.commit()
                        logger.info(f"시스템 작업 초기 설정 등록: {job_info['id']}")
                    elif config.job_name != job_info["name"]:
                        # 작업 내용이 바뀐 경우(예: 아카이빙 → 개인정보 파기) 표시 이름만 갱신
                        config.job_name = job_info["name"]
                        db.commit()
                    
                    if config.is_active:
                        try:
                            scheduler.add_job(
                                job_info["func"],
                                CronTrigger.from_crontab(config.cron_expression),
                                id=config.job_id,
                                replace_existing=True
                            )
                            logger.info(f"시스템 스케줄러 등록 완료: {config.job_id} ({config.cron_expression})")
                        except ValueError as e:
                            logger.error(f"잘못된 Cron 표현식 (Job ID {config.job_id}): {config.cron_expression} - {e}")

                # 2. SIEM 로그 동기화 동적 등록
                active_siems = db.query(models.SiemConfiguration).filter(
                    models.SiemConfiguration.is_active == True
                ).all()
                
                for siem in active_siems:
                    job_id = f"sync_siem_logs_{siem.siem_id}"
                    cron_expr = siem.cron_expression or "*/30 * * * *" # Default 30 min
                    
                    try:
                        scheduler.add_job(
                            siem_tasks.sync_siem_logs,
                            CronTrigger.from_crontab(cron_expr),
                            id=job_id,
                            args=[siem.siem_id],
                            replace_existing=True
                        )
                        logger.info(f"SIEM 스케줄러 등록 완료: {siem.name} ({cron_expr})")
                    except ValueError as e:
                        logger.error(f"잘못된 Cron 표현식 (SIEM ID {siem.siem_id}): {cron_expr} - {e}")
                        
            finally:
                db.close()
        except Exception as e:
            logger.error(f"스케줄러 초기화 중 오류: {e}")
            
        scheduler.start()
        logger.info("APScheduler 가동 시작 (경량 백그라운드 태스크 시스템)")

def reschedule_job(job_id: str, cron_expr: str):
    """실시간 스케줄 변경 처리"""
    try:
        trigger = CronTrigger.from_crontab(cron_expr)
        if scheduler.get_job(job_id):
            scheduler.reschedule_job(job_id, trigger=trigger)
            logger.info(f"스케줄러 즉지 반영 완료: {job_id} ({cron_expr})")
            return True
        else:
            logger.warning(f"변경하려는 작업을 찾을 수 없습니다: {job_id}")
            return False
    except ValueError as e:
        logger.error(f"잘못된 Cron 표현식으로 변경 시도 실패 ({job_id}): {cron_expr} - {e}")
        return False

def _update_siem_job(siem_id: int, cron_expr: str, is_active: bool):
    """SIEM 설정 변경 시 스케줄러 즉각 업데이트를 위한 헬퍼 함수"""
    job_id = f"sync_siem_logs_{siem_id}"
    
    if not is_active:
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
            logger.info(f"SIEM 스케줄러 비활성화 처리됨: {job_id}")
        return
        
    cron_expr = cron_expr or "*/30 * * * *"
    reschedule_job(job_id, cron_expr)

def stop_scheduler():
    """스케줄러 종료"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("APScheduler 종료")
