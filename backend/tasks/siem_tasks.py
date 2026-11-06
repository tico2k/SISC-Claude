"""
SIEM 연동 Celery 태스크

주기적으로 활성화된 SIEM 설정을 조회하고,
지정된 쿼리로 로그를 수집하여 소명 케이스로 자동 변환합니다.
"""


from sqlalchemy.orm import Session
from datetime import datetime
from ..core.database import SessionLocal
from .. import models
from ..modules.siem.services import apply_dynamic_mapping
from ..core.logging_config import get_logger
from ..services.collector_factory import CollectorFactory
import json

from .batch_tasks import record_job_log

logger = get_logger(__name__)


def sync_siem_logs(config_id: int, is_manual: bool = False):
    """
    주기적으로 특정 SIEM 설정에서 로그 수집하여
    ClarificationCase로 변환하고 SiemSyncHistory 및 BackgroundJobLog에 결과 기록.
    """
    db = SessionLocal()
    execution_start = datetime.now()
    job_id = f"sync_siem_logs_{config_id}"
    execution_type = "MANUAL" if is_manual else "AUTO"
    
    # 1. SIEM 설정 조회 (Job Name 확보용)
    config = db.query(models.SiemConfiguration).filter(
        models.SiemConfiguration.siem_id == config_id
    ).first()
    job_name = f"SIEM 보안 로그 수집 및 분석 ({config.name if config else 'ID:' + str(config_id)})"

    history_record = models.SiemSyncHistory(
        siem_id=config_id,
        execution_time=execution_start,
        status="RUNNING",
        records_fetched=0
    )
    
    try:
        # 시스템 어드민 등 기본 작성자용 시스템 유저 조회 (없으면 첫번째 어드민)
        system_user = db.query(models.User).filter(models.User.role == models.UserRole.SYSTEM_ADMIN).first()
        if not system_user:
            system_user = db.query(models.User).first()
            if not system_user:
                error_msg = f"[{execution_type} 실행] 실패: 시스템 유저를 찾을 수 없어 SIEM 동기화를 중단합니다."
                logger.error(error_msg)
                history_record.status = "FAILED"
                history_record.error_message = error_msg
                db.add(history_record)
                db.commit()
                record_job_log(db, job_id, job_name, "FAILED", execution_type, 0, error_msg)
                return {"status": "error", "message": error_msg}

        if not config or not config.is_active:
            error_msg = f"[{execution_type} 실행] 실패: 활성화된 SIEM 설정(ID: {config_id})을 찾을 수 없습니다."
            logger.warning(error_msg)
            history_record.status = "FAILED"
            history_record.error_message = error_msg
            db.add(history_record)
            db.commit()
            record_job_log(db, job_id, job_name, "FAILED", execution_type, 0, error_msg)
            return {"status": "error", "message": error_msg}

        logger.info(f"SIEM 설정({config.name}, ID: {config_id}) 동기화 시작")
        total_created = 0
        total_fetched = 0
        
        try:
            # 2. 맵핑 로드
            mapping = config.field_mapping or {
                "rule_title": "AppDisplayName",
                "summary": "LocationDetails.state",
                "related_employee_id": "UserPrincipalName"
            }
            
            # 3. Collector 초기화 (Factory 활용)
            try:
                collector = CollectorFactory.get_collector(config)
            except (ValueError, NotImplementedError) as e:
                error_msg = f"[{execution_type} 실행] 실패: SIEM {config.name} 콜렉터 초기화 실패 - {str(e)}"
                logger.warning(error_msg)
                history_record.status = "FAILED"
                history_record.error_message = error_msg
                db.add(history_record)
                db.commit()
                record_job_log(db, job_id, job_name, "FAILED", execution_type, 0, error_msg)
                return {"status": "error", "message": str(e)}
                
            # 4. 쿼리 실행 (스케줄러용)
            query = config.test_query or "SecurityIncident | take 10"
            
            results = collector.execute_query(query)
            if not isinstance(results, list):
                results = [results]
            
            total_fetched = len(results)
            history_record.records_fetched = total_fetched
            
            for log_data in results:
                # 5. 중복 체크
                rule_title_key = mapping.get("rule_title") or "UnknownRule"
                title = log_data.get(rule_title_key) if isinstance(log_data, dict) else "Unknown" 
                if not title:
                    title = "알 수 없는 보안 행위 감지"
                full_title = f"[SIEM 탐지] {title}"
                
                today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                existing_case = db.query(models.ClarificationCase).filter(
                    models.ClarificationCase.rule_title == full_title,
                    models.ClarificationCase.created_at >= today_start
                ).first()
                
                if existing_case:
                    continue

                # 6. 케이스 생성 로직 적용
                new_case = apply_dynamic_mapping(db, log_data, mapping, system_user, config.siem_type)
                db.add(new_case)
                db.commit() 
                total_created += 1
            
            msg = f"[{execution_type} 실행] 정상 처리 완료. (조회: {total_fetched}건, 생성: {total_created}건)"
            history_record.status = "SUCCESS"
            history_record.error_message = msg
            db.add(history_record)
            db.commit()
            record_job_log(db, job_id, job_name, "SUCCESS", execution_type, total_fetched, msg)
            
        except Exception as e:
            error_msg = f"[{execution_type} 실행] 실패: SIEM {config.name} 동기화 중 오류 발생 - {str(e)}"
            logger.error(error_msg, exc_info=True)
            db.rollback()
            
            history_record.status = "FAILED"
            history_record.error_message = error_msg[:1000]
            db.add(history_record)
            db.commit()
            record_job_log(db, job_id, job_name, "FAILED", execution_type, 0, error_msg)
            return {"status": "error", "message": str(e)}
            
        logger.info(f"SIEM {config.name} 동기화 완료 ({execution_type}): 총 {total_fetched}건 조회, {total_created}건 생성")
        return {"status": "success", "total_created": total_created, "total_fetched": total_fetched}
        
    except Exception as e:
        logger.error(f"SIEM 스케줄러 오류 (History 저장 실패 가능): {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}
    finally:
        db.close()
