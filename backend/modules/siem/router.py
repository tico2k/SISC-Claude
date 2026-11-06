from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List
from ... import models, schemas
from ...core import dependencies
from ...core.database import get_db
from ...core.exceptions import AuthorizationException, NotFoundException, DatabaseException, ExternalServiceException, ValidationException
from ...core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["SIEM Integration"])

from ...core.security import encrypt_secret, decrypt_secret, DecryptionError
from ...services.collector_factory import CollectorFactory
from ...core.scheduler import _update_siem_job

@router.post("/siem/config", response_model=schemas.SiemConfigResponse, status_code=status.HTTP_201_CREATED)
def create_siem_config(
    config: schemas.SiemConfigCreate,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """SIEM 설정 생성"""
    if current_user.role not in [models.UserRole.SECURITY_ADMIN, models.UserRole.SYSTEM_ADMIN]:
        logger.warning(f"권한 없는 SIEM 설정 생성 시도: {current_user.user_email}")
        raise AuthorizationException("SIEM을 설정할 권한이 없습니다")
    
    try:
        new_config = models.SiemConfiguration(
            siem_type=config.siem_type,
            name=config.name,
            host_url=config.host_url,
            tenant_id=config.tenant_id,
            client_id=config.client_id,
            client_secret=encrypt_secret(config.client_secret) if config.client_secret else None,
            subscription_id=config.subscription_id,
            resource_group=config.resource_group,
            workspace_name=config.workspace_name,
            api_key=encrypt_secret(config.api_key) if config.api_key else None,
            test_query=config.test_query,
            field_mapping=config.field_mapping,
            cron_expression=config.cron_expression,
            is_active=config.is_active
        )
        db.add(new_config)
        db.commit()
        db.refresh(new_config)
        
        logger.info(f"SIEM 설정 생성 성공: {config.name} ({config.siem_type}) by {current_user.user_email}")
        
        # 동적 스케줄러 등록
        _update_siem_job(new_config.siem_id, new_config.cron_expression, new_config.is_active)
        
        # 보안을 위해 마스킹하여 반환
        response_data = schemas.SiemConfigResponse.from_orm(new_config).dict()
        if response_data.get("client_secret"):
            response_data["client_secret"] = "********"
        if response_data.get("api_key"):
            response_data["api_key"] = "********"
        return response_data
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"SIEM 설정 생성 실패: {str(e)}", exc_info=True)
        raise DatabaseException("SIEM 설정 생성 중 오류가 발생했습니다")

@router.get("/siem/config", response_model=List[schemas.SiemConfigResponse])
def get_siem_configs(
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """SIEM 설정 목록 조회 (보안을 위해 시크릿 마스킹)"""
    if current_user.role not in [models.UserRole.SECURITY_ADMIN, models.UserRole.SYSTEM_ADMIN]:
        logger.warning(f"권한 없는 SIEM 설정 조회 시도: {current_user.user_email}")
        raise AuthorizationException("SIEM 설정을 조회할 권한이 없습니다")
    
    logger.info(f"SIEM 설정 조회: {current_user.user_email}")
    configs = db.query(models.SiemConfiguration).all()
    
    # 응답 시 민감 정보 마스킹 (복사본 생성하여 마스킹)
    response_configs = []
    for cfg in configs:
        cfg_dict = schemas.SiemConfigResponse.from_orm(cfg).dict()
        if cfg_dict.get("client_secret"):
            cfg_dict["client_secret"] = "********"
        if cfg_dict.get("api_key"):
            cfg_dict["api_key"] = "********"
        response_configs.append(cfg_dict)
        
    return response_configs

@router.post("/siem/test-connection")
def test_siem_connection(
    config: schemas.SiemTestConnectionRequest,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """SIEM 연결 테스트"""
    if current_user.role not in [models.UserRole.SECURITY_ADMIN, models.UserRole.SYSTEM_ADMIN]:
        logger.warning(f"권한 없는 SIEM 연결 테스트 시도: {current_user.user_email}")
        raise AuthorizationException("SIEM 연결 테스트 권한이 없습니다")

    # 만약 시크릿이 마스크('********')로 왔다면, 실제 DB에서 가져온 값을 사용해야 함 (업데이트 모드)
    db_config = None
    if config.siem_id:
        db_config = db.query(models.SiemConfiguration).filter(models.SiemConfiguration.siem_id == config.siem_id).first()

    secret = config.client_secret
    if secret == "********" and db_config:
        try:
            secret = decrypt_secret(db_config.client_secret) if db_config.client_secret else None
        except DecryptionError as e:
            raise ValidationException(str(e))
    elif secret and secret.startswith("gAAAA"):
        try:
            secret = decrypt_secret(secret)
        except:
            pass # 복호화 실패 시 원본 사용
            
    api_key = config.api_key
    if api_key == "********" and db_config:
        try:
            api_key = decrypt_secret(db_config.api_key) if db_config.api_key else None
        except DecryptionError as e:
            raise ValidationException(str(e))
    elif api_key and api_key.startswith("gAAAA"):
        try:
            api_key = decrypt_secret(api_key)
        except:
            pass

    if config.siem_type in [models.SiemType.SENTINEL, models.SiemType.ELK, models.SiemType.SPLUNK]:
        try:
            logger.info(f"{config.siem_type} 연결 테스트 시작: {config.name} by {current_user.user_email}")
            
            # Create a temporary config object for the factory
            temp_config = models.SiemConfiguration(
                siem_type=config.siem_type,
                tenant_id=config.tenant_id,
                client_id=config.client_id,
                client_secret=secret,
                workspace_name=config.workspace_name, # Also used for Workspace ID
                api_key=api_key,
                host_url=config.host_url
            )
            
            collector = CollectorFactory.get_collector(temp_config)

            if config.test_query and config.test_query.strip():
                result = collector.execute_query(config.test_query)
                logger.info(f"{config.siem_type} 커스텀 쿼리 실행 성공: {config.name}")
                return {
                    "status": "success",
                    "message": "쿼리가 성공적으로 실행되었습니다",
                    "data": result
                }
            else:
                # Default connection check
                test_query = "Usage | take 1" if config.siem_type == models.SiemType.SENTINEL else "*"
                collector.execute_query(test_query)
                logger.info(f"{config.siem_type} 연결 테스트 성공: {config.name}")
                return {
                    "status": "success",
                    "message": f"{config.siem_type}에 성공적으로 연결되었습니다"
                }

        except NotImplementedError as e:
            return {"status": "error", "message": f"지원되지 않는 기능: {str(e)}"}
        except Exception as e:
            logger.error(f"{config.siem_type} 연결 실패: {config.name} - {str(e)}", exc_info=True)
            return {"status": "error", "message": f"연결 실패: {str(e)}"}
    
    elif config.siem_type == models.SiemType.ELK:
        logger.info(f"ELK 연결 테스트 (시뮬레이션): {config.name}")
        return {"status": "success", "message": "ELK 연결 시뮬레이션 성공"}
    
    logger.warning(f"알 수 없는 SIEM 타입: {config.siem_type}")
    return {"status": "unknown", "message": "알 수 없는 SIEM 유형입니다"}

@router.delete("/siem/config/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_siem_config(
    config_id: int,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """SIEM 설정 삭제"""
    if current_user.role not in [models.UserRole.SECURITY_ADMIN, models.UserRole.SYSTEM_ADMIN]:
        logger.warning(f"권한 없는 SIEM 설정 삭제 시도: {current_user.user_email}")
        raise AuthorizationException("SIEM 설정을 삭제할 권한이 없습니다")
    
    config = db.query(models.SiemConfiguration).filter(models.SiemConfiguration.siem_id == config_id).first()
    if not config:
        logger.warning(f"존재하지 않는 SIEM 설정 삭제 시도: Config ID {config_id}")
        raise NotFoundException("SIEM 설정을 찾을 수 없습니다")
    
    try:
        config_name = config.name
        db.delete(config)
        db.commit()
        
        # 삭제 시 스케줄러에서도 등록된 해당 SIEM 작업 제거
        _update_siem_job(config_id, None, False)
        
        logger.info(f"SIEM 설정 삭제 성공: {config_name} (ID: {config_id}) by {current_user.user_email}")
        return None
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"SIEM 설정 삭제 실패: {str(e)}", exc_info=True)
        raise DatabaseException("SIEM 설정 삭제 중 오류가 발생했습니다")

@router.put("/siem/config/{config_id}", response_model=schemas.SiemConfigResponse)
def update_siem_config(
    config_id: int,
    config_update: schemas.SiemConfigUpdate,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """SIEM 설정 수정"""
    if current_user.role not in [models.UserRole.SECURITY_ADMIN, models.UserRole.SYSTEM_ADMIN]:
        logger.warning(f"권한 없는 SIEM 설정 수정 시도: {current_user.user_email}")
        raise AuthorizationException("SIEM 설정을 수정할 권한이 없습니다")
    
    db_config = db.query(models.SiemConfiguration).filter(models.SiemConfiguration.siem_id == config_id).first()
    if not db_config:
        logger.warning(f"존재하지 않는 SIEM 설정 수정 시도: Config ID {config_id}")
        raise NotFoundException("SIEM 설정을 찾을 수 없습니다")
    
    try:
        original_name = db_config.name
        
        update_data = config_update.dict(exclude_unset=True)
        if "client_secret" in update_data:
            if update_data["client_secret"] == "********":
                # 마스킹된 값이면 무시 (기존 값 유지)
                del update_data["client_secret"]
            elif update_data["client_secret"]:
                update_data["client_secret"] = encrypt_secret(update_data["client_secret"])
                
        if "api_key" in update_data:
            if update_data["api_key"] == "********":
                # 마스킹된 값이면 무시 (기존 값 유지)
                del update_data["api_key"]
            elif update_data["api_key"]:
                update_data["api_key"] = encrypt_secret(update_data["api_key"])
            
        for key, value in update_data.items():
            setattr(db_config, key, value)
        
        db.commit()
        db.refresh(db_config)
        
        # 동적 스케줄러 업데이트 반영
        _update_siem_job(db_config.siem_id, db_config.cron_expression, db_config.is_active)
        
        logger.info(f"SIEM 설정 수정 성공: {original_name} -> {db_config.name} (ID: {config_id}) by {current_user.user_email}")
        
        # 보안을 위해 마스킹하여 반환
        response_data = schemas.SiemConfigResponse.from_orm(db_config).dict()
        if response_data.get("client_secret"):
            response_data["client_secret"] = "********"
        if response_data.get("api_key"):
            response_data["api_key"] = "********"
        return response_data
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"SIEM 설정 수정 실패: {str(e)}", exc_info=True)
        raise DatabaseException("SIEM 설정 수정 중 오류가 발생했습니다")

import json
from datetime import datetime, timedelta
from .services import apply_dynamic_mapping

@router.post("/siem/convert-case", status_code=status.HTTP_201_CREATED)
def convert_siem_log_to_case(
    request: schemas.SiemCaseConvertRequest,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """SIEM 로그(JSON)를 기반으로 수동 소명 케이스 생성 (동적 맵핑 적용)"""
    if current_user.role not in [models.UserRole.SECURITY_ADMIN, models.UserRole.SYSTEM_ADMIN]:
        logger.warning(f"권한 없는 케이스 수동 생성 시도: {current_user.user_email}")
        raise AuthorizationException("케이스를 수동으로 생성할 권한이 없습니다")
    
    log_data = request.log_data
    mapping = {}
    
    # 1. Provide mapping from override (UI test) or from saved config
    if request.mapping_override:
        mapping = request.mapping_override
    elif request.config_id:
        db_config = db.query(models.SiemConfiguration).filter(models.SiemConfiguration.siem_id == request.config_id).first()
        if db_config and db_config.field_mapping:
            mapping = db_config.field_mapping
            
    # Default fallback mapping if none provided
    if not mapping:
        mapping = {
            "rule_title_key": "AppDisplayName" if "AppDisplayName" in log_data else "OperationName",
            "summary_key": "LocationDetails.state",
            "user_identifier_key": "UserPrincipalName" if "UserPrincipalName" in log_data else "userPrincipalName"
        }
    
    # 2. Extract and create via Service
    new_case = apply_dynamic_mapping(db, log_data, mapping, current_user, models.SiemType.SENTINEL)
    
    try:
        db.add(new_case)
        db.commit()
        db.refresh(new_case)
        logger.info(f"SIEM 수동 케이스 생성 완료 (Case ID: {new_case.case_id})")
        return {"status": "success", "case_id": new_case.case_id, "message": "성공적으로 소명 건을 생성했습니다!"}
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"SIEM 수동 케이스 생성 실패: {str(e)}", exc_info=True)
        raise DatabaseException("소명 케이스 생성 중 오류가 발생했습니다")

@router.get("/siem/history", response_model=List[schemas.SiemSyncHistoryResponse])
def get_siem_history(
    config_id: int = None,
    limit: int = 50,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """SIEM 동기화 기록 조회"""
    if current_user.role not in [models.UserRole.SECURITY_ADMIN, models.UserRole.SYSTEM_ADMIN]:
        raise AuthorizationException("동기화 기록을 조회할 권한이 없습니다")
        
    query = db.query(models.SiemSyncHistory)
    if config_id:
        query = query.filter(models.SiemSyncHistory.siem_id == config_id)
        
    history = query.order_by(models.SiemSyncHistory.execution_time.desc()).limit(limit).all()
    return history
