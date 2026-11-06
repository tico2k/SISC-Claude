from fastapi import APIRouter, Depends, Request, status, File, UploadFile, Form, Query, BackgroundTasks
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional
import os
from pathlib import Path
from datetime import datetime, timedelta
from ... import models, schemas
from ...core import dependencies
from ...core.database import get_db
from ...utils.file_upload import validate_and_save_file
from ...core.exceptions import AuthorizationException, NotFoundException, ValidationException, DatabaseException, FileUploadException
from ...core.logging_config import get_logger
from ...core.mail import services as mail_services
from . import services as case_services

logger = get_logger(__name__)
router = APIRouter(tags=["Clarification Cases"])


@router.post("/cases", response_model=schemas.CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(
    case: schemas.CaseCreate,
    request: Request,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    """소명 케이스 생성"""
    if current_user.role not in [models.UserRole.SECURITY_ADMIN, models.UserRole.SYSTEM_ADMIN]:
        logger.warning(f"권한 없는 케이스 생성 시도: {current_user.user_email}")
        raise AuthorizationException("케이스를 생성할 권한이 없습니다")
    
    try:
        new_case = models.ClarificationCase(
            siem_type=case.siem_type,
            rule_title=case.rule_title,
            rule_description=case.rule_description,
            incident_num=case.incident_num,
            summary=case.summary,
            case_type=case.case_type,
            related_employee_id=case.related_employee_id,
            requester_id=current_user.user_id,
            due_date=case.due_date,
            priority=case.priority
        )
        db.add(new_case)
        db.flush()
        case_services.add_audit_log(
            db, current_user,
            f"CASE_CREATED: Case {new_case.case_id} (Employee {case.related_employee_id})",
            request,
        )
        db.commit()
        db.refresh(new_case)
        
        logger.info(
            f"케이스 생성 성공: Case ID {new_case.case_id}, "
            f"Type: {case.case_type}, Employee: {case.related_employee_id}, Requester: {current_user.user_email}"
        )
        
        # 백그라운드에서 이메일 발송
        try:
            from ...tasks.email_tasks import send_case_created_email
            if background_tasks:
                background_tasks.add_task(send_case_created_email, new_case.case_id)
            logger.info(f"케이스 생성 이메일 태스크 등록: Case ID {new_case.case_id}")
        except Exception as e:
            # 이메일 발송 실패는 케이스 생성 자체를 실패시키지 않음
            logger.warning(f"케이스 생성 이메일 태스크 등록 실패: {str(e)}")
        
        return new_case
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"케이스 생성 실패: {str(e)}", exc_info=True)
        raise DatabaseException("케이스 생성 중 오류가 발생했습니다")

@router.get("/cases", response_model=schemas.PaginatedCaseResponse)
def get_cases(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100000),
    case_status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    case_type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None),
    order: Optional[str] = Query("desc"),
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """케이스 목록 조회 (서버사이드 페이징 및 필터링)"""
    logger.info(f"케이스 목록 조회: {current_user.user_email} (역할: {current_user.role})")
    
    # 1. 개수 조회를 위한 기본 쿼리 (JOIN/로딩 옵션 제외)
    base_query = db.query(models.ClarificationCase)

    if current_user.role not in [models.UserRole.SECURITY_ADMIN, models.UserRole.SYSTEM_ADMIN, models.UserRole.AUDIT_TEAM]:
        # 일반 사용자는 본인에게 요청된 건만 조회 가능 (미확인 건은 관리자 스크리닝 전, 종결 건은 오탐 자체종결이므로 비노출)
        base_query = base_query.filter(
            models.ClarificationCase.related_employee_id == current_user.user_id,
            models.ClarificationCase.case_status.notin_([models.CaseStatus.UNCLASSIFIED, models.CaseStatus.CLOSE])
        )
        
    if case_status:
        base_query = base_query.filter(models.ClarificationCase.case_status == case_status)
    if priority:
        base_query = base_query.filter(models.ClarificationCase.priority == priority)
    if case_type:
        base_query = base_query.filter(models.ClarificationCase.case_type == case_type)
    if start_date:
        base_query = base_query.filter(models.ClarificationCase.created_at >= datetime.combine(datetime.strptime(start_date, "%Y-%m-%d"), datetime.min.time()))
    if end_date:
        base_query = base_query.filter(models.ClarificationCase.created_at <= datetime.combine(datetime.strptime(end_date, "%Y-%m-%d"), datetime.max.time()))
    
    if search:
        search_term = f"%{search}%"
        from sqlalchemy import or_, String
        base_query = base_query.filter(
            or_(
                models.ClarificationCase.rule_title.ilike(search_term),
                models.ClarificationCase.summary.ilike(search_term),
                models.ClarificationCase.incident_num.cast(String).ilike(search_term)
            )
        )

    logger.debug(f"Query filters - status: {case_status}, priority: {priority}, type: {case_type}, search: {search}")

    # 전체 개수 계산 (Eager loading 및 정렬 이전에 수행하여 SQL 경량화)
    total = base_query.count()

    # 2. 데이터 배치를 위한 실행 쿼리 구성 (JOIN/로딩/정렬 추가)
    query = base_query.options(
        joinedload(models.ClarificationCase.related_employee),
        selectinload(models.ClarificationCase.submissions),
        selectinload(models.ClarificationCase.attachments)
    )

    # 정렬 처리
    sort_map = {
        "priority": models.ClarificationCase.priority,
        "incident_num": models.ClarificationCase.incident_num,
        "case_type": models.ClarificationCase.case_type,
        "rule_title": models.ClarificationCase.rule_title,
        "created_at": models.ClarificationCase.created_at,
        "due_date": models.ClarificationCase.due_date,
        "final_review_date": models.ClarificationCase.final_review_date,
        "case_status": models.ClarificationCase.case_status,
        "case_result": models.ClarificationCase.case_result,
        "related_employee": models.User.user_name,
    }

    sort_col = sort_map.get(sort_by, models.ClarificationCase.created_at)
    
    # 조인이 필요한 컬럼 처리
    if sort_by == "related_employee":
        query = query.join(models.ClarificationCase.related_employee)
    
    # Priority는 특별 정렬 필요 (높음 > 보통 > 낮음 순)
    if sort_by == "priority":
        from sqlalchemy import case as sql_case
        sort_col = sql_case(
            (models.ClarificationCase.priority == models.CasePriority.HIGH, 1),
            (models.ClarificationCase.priority == models.CasePriority.MEDIUM, 2),
            (models.ClarificationCase.priority == models.CasePriority.LOW, 3),
            else_=4
        )
    
    if order == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    # 기본 정렬 추가 (동일한 정렬 기준일 경우 최신순으로)
    if sort_by != "created_at":
        query = query.order_by(models.ClarificationCase.created_at.desc())

    items = query.offset(skip).limit(limit).all()
    
    pages = (total + limit - 1) // limit if limit > 0 else 0
    page = (skip // limit) + 1 if limit > 0 else 1

    return {
        "items": items,
        "total": total,
        "page": page,
        "size": limit,
        "pages": pages
    }

@router.get("/cases/history", response_model=List[schemas.CaseResponse])
def get_case_history(
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """승인된 케이스 이력 조회 (자동 분류 참고용)"""
    logger.info(f"케이스 이력 조회: {current_user.user_email}")
    return db.query(models.ClarificationCase).options(
        joinedload(models.ClarificationCase.related_employee),
        selectinload(models.ClarificationCase.submissions),
        selectinload(models.ClarificationCase.attachments)
    ).filter(
        models.ClarificationCase.related_employee_id == current_user.user_id,
        models.ClarificationCase.case_status == models.CaseStatus.APPROVE
    ).all()

@router.get("/cases/stats")
def get_case_stats(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    case_status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    case_type: Optional[str] = Query(None),
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """대시보드 통계 조회 (날짜 및 필터 적용 가능)"""
    query = db.query(models.ClarificationCase)
    
    if current_user.role not in [models.UserRole.SECURITY_ADMIN, models.UserRole.SYSTEM_ADMIN, models.UserRole.AUDIT_TEAM]:
        query = query.filter(
            models.ClarificationCase.related_employee_id == current_user.user_id,
            models.ClarificationCase.case_status.notin_([models.CaseStatus.UNCLASSIFIED, models.CaseStatus.CLOSE])
        )
        
    if start_date:
        query = query.filter(models.ClarificationCase.created_at >= datetime.combine(datetime.strptime(start_date, "%Y-%m-%d"), datetime.min.time()))
    if end_date:
        query = query.filter(models.ClarificationCase.created_at <= datetime.combine(datetime.strptime(end_date, "%Y-%m-%d"), datetime.max.time()))

    # 상호 작용 필터 적용
    if case_status:
        query = query.filter(models.ClarificationCase.case_status == case_status)
    if priority:
        query = query.filter(models.ClarificationCase.priority == priority)
    if case_type:
        query = query.filter(models.ClarificationCase.case_type == case_type)

    # Calculate overall stats
    total = query.count()
    
    # Status stats
    status_counts = query.with_entities(
        models.ClarificationCase.case_status, 
        func.count(models.ClarificationCase.case_id)
    ).group_by(models.ClarificationCase.case_status).all()
    
    status_dict = {status.value: count for status, count in status_counts}
    
    # Priority stats
    priority_counts = query.with_entities(
        models.ClarificationCase.priority, 
        func.count(models.ClarificationCase.case_id)
    ).group_by(models.ClarificationCase.priority).all()
    
    priority_dict = {priority.value if priority else "보통": count for priority, count in priority_counts}
    
    # Case type stats
    type_counts = query.with_entities(
        models.ClarificationCase.case_type, 
        func.count(models.ClarificationCase.case_id)
    ).group_by(models.ClarificationCase.case_type).all()
    
    type_dict = {ctype.value: count for ctype, count in type_counts}
    
    # Chart Data (Last 20 days by Case Type)
    recent_cases = query.with_entities(
        func.date(models.ClarificationCase.created_at).label('date'),
        models.ClarificationCase.case_type,
        func.count(models.ClarificationCase.case_id)
    ).group_by(
        func.date(models.ClarificationCase.created_at),
        models.ClarificationCase.case_type
    ).all()
    
    chart_data = [{"date": str(r[0]), "case_type": r[1].value if r[1] else None, "count": r[2]} for r in recent_cases]

    return {
        "total": total,
        "status": {
            "unclassified": status_dict.get(models.CaseStatus.UNCLASSIFIED.value, 0),
            "requested": status_dict.get(models.CaseStatus.REQUEST.value, 0),
            "submitted": status_dict.get(models.CaseStatus.SUBMIT.value, 0),
            "approved": status_dict.get(models.CaseStatus.APPROVE.value, 0),
            "rejected": status_dict.get(models.CaseStatus.REJECT.value, 0),
            "closed": status_dict.get(models.CaseStatus.CLOSE.value, 0),
        },
        "priority": {
            "high": priority_dict.get(models.CasePriority.HIGH.value, 0),
            "medium": priority_dict.get(models.CasePriority.MEDIUM.value, 0),
            "low": priority_dict.get(models.CasePriority.LOW.value, 0),
        },
        "case_type": {
            "leak": type_dict.get(models.CaseType.INFO_LEAK.value, 0),
            "violation": type_dict.get(models.CaseType.SECURITY_VIOLATION.value, 0),
            "system": type_dict.get(models.CaseType.SYSTEM_ACCESS.value, 0),
            "abuse": type_dict.get(models.CaseType.AUTH_ABUSE.value, 0),
        },
        "chart_data": chart_data
    }

@router.get("/cases/daily-stats")
def get_daily_stats(
    days: int = Query(14, ge=1, le=90),
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """일간 발생/처리 통계 트렌드 조회 (관리자 및 감사팀 전용 대시보드 지표)"""
    # 일반 권한은 전사 통계 조회 불가
    if current_user.role not in [models.UserRole.SECURITY_ADMIN, models.UserRole.SYSTEM_ADMIN, models.UserRole.AUDIT_TEAM]:
        return []

    logger.info(f"일간 통계 트렌드 조회: 최근 {days}일, User: {current_user.user_email}")
    
    start_date = datetime.now().date() - timedelta(days=days)
    
    # DailyStatistic에서 데이터 조회
    daily_stats = db.query(models.DailyStatistic).filter(
        func.date(models.DailyStatistic.stat_date) >= start_date
    ).order_by(models.DailyStatistic.stat_date.asc()).all()
    
    result = []
    for stat in daily_stats:
        result.append({
            "date": stat.stat_date.strftime("%Y-%m-%d"),
            "unclassified": stat.unclassified_count,
            "request": stat.request_count,
            "submit": stat.submit_count,
            "reviewed": stat.reviewed_count
        })
        
    return result


@router.get("/cases/weekly-reports")
def get_weekly_reports(
    limit: int = Query(5, ge=1, le=20),
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """최근 주간 보안 보고서 조회 (관리자 및 감사팀 전용 대시보드 지표)"""
    # 일반 권한은 전사 보고서 조회 불가
    if current_user.role not in [models.UserRole.SECURITY_ADMIN, models.UserRole.SYSTEM_ADMIN, models.UserRole.AUDIT_TEAM]:
        return []

    logger.info(f"주간 보고서 조회: 최근 {limit}주, User: {current_user.user_email}")
    
    # WeeklyReport에서 최근 데이터 조회 (생성일 역순)
    weekly_reports = db.query(models.WeeklyReport).order_by(
        models.WeeklyReport.week_start.desc()
    ).limit(limit).all()
    
    result = []
    for report in weekly_reports:
        result.append({
            "report_id": report.report_id,
            "week_start": report.week_start.strftime("%Y-%m-%d"),
            "week_end": report.week_end.strftime("%Y-%m-%d"),
            "created": report.created_count,
            "approved": report.approved_count,
            "rejected": report.rejected_count,
            "generated_at": report.generated_at.strftime("%Y-%m-%d %H:%M:%S") if report.generated_at else None
        })
        
    return result

@router.get("/cases/{case_id}", response_model=schemas.CaseResponse)
def get_case(
    case_id: int,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """케이스 상세 조회"""
    case = db.query(models.ClarificationCase).filter(
        models.ClarificationCase.case_id == case_id
    ).first()
    
    if not case:
        logger.warning(f"존재하지 않는 케이스 조회 시도: Case ID {case_id}")
        raise NotFoundException("케이스를 찾을 수 없습니다")
    
    # 리뷰 정보 추가 (승인/반려된 경우)
    if case.case_status in [models.CaseStatus.APPROVE, models.CaseStatus.REJECT]:
        latest_review = db.query(models.ReviewHistory)\
            .filter(models.ReviewHistory.case_id == case_id)\
            .order_by(models.ReviewHistory.reviewed_at.desc())\
            .first()
        
        if latest_review:
            case.review_comment = latest_review.comments
            case.final_review_date = latest_review.reviewed_at
            if latest_review.reviewer:
                case.reviewer_name = latest_review.reviewer.user_name

    # 잠금 정보 처리
    if case.locked_by_id:
        locked_user = db.query(models.User).filter(models.User.user_id == case.locked_by_id).first()
        if locked_user:
            case.locked_by_name = locked_user.user_name

    # 권한 확인: 관리자이거나 본인에게 요청된 케이스 (미확인 및 종결 건은 일반 사용자 접근 차단)
    if current_user.role not in [models.UserRole.SECURITY_ADMIN, models.UserRole.SYSTEM_ADMIN, models.UserRole.AUDIT_TEAM]:
        if case.related_employee_id != current_user.user_id or case.case_status in [models.CaseStatus.UNCLASSIFIED, models.CaseStatus.CLOSE]:
            logger.warning(
                f"권한 없는 케이스 조회: User {current_user.user_email}, Case ID {case_id}, "
                f"Owner ID {case.related_employee_id}, Status: {case.case_status}"
            )
            raise AuthorizationException("이 케이스를 조회할 권한이 없습니다")

    logger.info(f"케이스 조회: Case ID {case_id}, User: {current_user.user_email}")
    return case

@router.put("/cases/{case_id}/status", response_model=schemas.CaseResponse)
def update_case_status(
    case_id: int,
    status: str,
    request: Request,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """케이스 상태 업데이트"""
    if current_user.role not in [models.UserRole.SECURITY_ADMIN, models.UserRole.SYSTEM_ADMIN, models.UserRole.AUDIT_TEAM]:
        logger.warning(f"권한 없는 케이스 상태 변경 시도: {current_user.user_email}")
        raise AuthorizationException("케이스 상태를 변경할 권한이 없습니다")
    
    case = db.query(models.ClarificationCase).filter(
        models.ClarificationCase.case_id == case_id
    ).first()
    
    if not case:
        logger.warning(f"존재하지 않는 케이스 상태 변경 시도: Case ID {case_id}")
        raise NotFoundException("케이스를 찾을 수 없습니다")

    try:
        old_status = case.case_status
        
        if status == "요청":
            case_services.ensure_can_request(case, current_user)
            case.case_status = models.CaseStatus.REQUEST
        else:
            raise ValidationException(f"지원하지 않는 상태값입니다: {status}")

        case_services.add_audit_log(
            db, current_user, f"CASE_REQUESTED: Case {case_id} ({old_status.value} -> {case.case_status.value})", request
        )
        db.commit()
        db.refresh(case)
        
        logger.info(
            f"케이스 상태 변경: Case ID {case_id}, {old_status} -> {case.case_status}, "
            f"User: {current_user.user_email}"
        )
        return case
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"케이스 상태 변경 실패: {str(e)}", exc_info=True)
        raise DatabaseException("케이스 상태 변경 중 오류가 발생했습니다")

@router.post("/cases/{case_id}/request", response_model=schemas.CaseResponse, status_code=status.HTTP_201_CREATED)
async def request_clarification(
    case_id: int,
    request: Request,
    due_date: str = Form(...),
    request_reason: str = Form(...),
    files: Optional[List[UploadFile]] = File(None),
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    """소명 요청 및 파일 업로드"""
    # 권한 확인
    if current_user.role not in [models.UserRole.SECURITY_ADMIN, models.UserRole.SYSTEM_ADMIN, models.UserRole.AUDIT_TEAM]:
        logger.warning(f"권한 없는 소명 요청 시도: {current_user.user_email}")
        raise AuthorizationException("소명을 요청할 권한이 없습니다")

    # 케이스 조회 (메일 발송을 위해 related_employee 미리 로드)
    case = db.query(models.ClarificationCase).options(
        joinedload(models.ClarificationCase.related_employee)
    ).filter(
        models.ClarificationCase.case_id == case_id
    ).first()
    
    if not case:
        logger.warning(f"존재하지 않는 케이스에 소명 요청: Case ID {case_id}")
        raise NotFoundException("케이스를 찾을 수 없습니다")

    # 상태 전이·잠금 검사 (UNCLASSIFIED → REQUEST)
    case_services.ensure_can_request(case, current_user)

    try:
        # 케이스 업데이트
        case.case_status = models.CaseStatus.REQUEST
        
        # 날짜 파싱
        try:
            # Handle YYYY-MM-DD format from frontend input[type=date]
            if len(due_date) == 10:
                case.due_date = datetime.strptime(due_date, "%Y-%m-%d")
            else:
                case.due_date = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
        except ValueError as e:
            logger.warning(f"잘못된 날짜 형식: {due_date} - {str(e)}")
            raise ValidationException(f"잘못된 날짜 형식입니다: {due_date}")
        
        case.summary = request_reason
        
        # 파일 업로드 처리
        file_count = 0
        if files:
            upload_dir = Path(f"uploads/{case_id}/request")

            for file in files:
                if not file.filename:
                    continue
                
                try:
                    # 파일 검증 및 저장
                    original_filename, safe_filename, file_size = await validate_and_save_file(
                        file=file,
                        upload_dir=upload_dir
                    )
                    
                    file_location = upload_dir / safe_filename
                    
                    # 첨부파일 레코드 생성
                    attachment = models.ClarificationAttachment(
                        case_id=case_id,
                        original_filename=original_filename,
                        stored_filename=safe_filename,
                        file_path=str(file_location),
                        file_size=file_size
                    )
                    db.add(attachment)
                    file_count += 1
                    
                except FileUploadException as e:
                    db.rollback()
                    logger.error(f"파일 업로드 실패: {original_filename if 'original_filename' in locals() else file.filename} - {str(e)}")
                    raise

        case_services.add_audit_log(
            db, current_user, f"CASE_REQUESTED: Case {case_id} (Due {case.due_date:%Y-%m-%d}, Files {file_count})", request
        )
        db.commit()
        db.refresh(case)
        
        logger.info(
            f"소명 요청 성공: Case ID {case_id}, Due Date: {case.due_date}, "
            f"Files: {file_count}, Requester: {current_user.user_email}"
        )

        # 소명 요청 알림 메일 발송 (비동기)
        if background_tasks and case.related_employee:
            background_tasks.add_task(
                mail_services.send_request_notification,
                to_email=case.related_employee.user_email,
                user_name=case.related_employee.user_name,
                priority=case.priority.value if hasattr(case.priority, 'value') else str(case.priority),
                incident_num=str(case.incident_num or case.case_id),
                rule_title=case.rule_title,
                due_date=case.due_date,
                request_reason=request_reason,
                case_id=case_id
            )

        return case
        
    except ValidationException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"소명 요청 실패: {str(e)}", exc_info=True)
        raise DatabaseException("소명 요청 중 오류가 발생했습니다")


@router.post("/cases/{case_id}/close", response_model=schemas.CaseResponse)
def close_case(
    case_id: int,
    request: schemas.CaseCloseRequest,
    http_request: Request,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    """케이스 종료 처리"""
    # 권한 확인
    if current_user.role not in [models.UserRole.SECURITY_ADMIN, models.UserRole.SYSTEM_ADMIN, models.UserRole.AUDIT_TEAM]:
        logger.warning(f"권한 없는 케이스 종료 시도: {current_user.user_email}")
        raise AuthorizationException("케이스를 종료할 권한이 없습니다")

    # 케이스 조회
    case = db.query(models.ClarificationCase).filter(
        models.ClarificationCase.case_id == case_id
    ).first()
    
    if not case:
        logger.warning(f"존재하지 않는 케이스 종료 시도: Case ID {case_id}")
        raise NotFoundException("케이스를 찾을 수 없습니다")

    # 이미 종결된 케이스 재종결 방지 및 잠금 검사
    case_services.ensure_can_close(case, current_user)

    try:
        # 케이스 종료 처리
        case.case_status = models.CaseStatus.CLOSE
        case.case_result = request.case_result
        case.final_reviewer_id = current_user.user_id
        case.final_review_date = datetime.now()

        # 리뷰 이력 추가
        review = models.ReviewHistory(
            case_id=case_id,
            reviewer_id=current_user.user_id,
            reviewed_at=datetime.now(),
            case_status=models.CaseStatus.CLOSE,
            case_result=request.case_result,
            comments=request.close_reason
        )
        db.add(review)

        case_services.add_audit_log(
            db, current_user,
            f"CASE_CLOSED: Case {case_id} ({request.case_result.value})",
            http_request,
        )
        db.commit()
        db.refresh(case)
        
        # 응답용 리뷰 정보 추가
        case.review_comment = request.close_reason
        case.reviewer_name = current_user.user_name
        
        logger.info(
            f"케이스 종료 성공: Case ID {case_id}, Result: {request.case_result}, "
            f"Reviewer: {current_user.user_email}"
        )
        
        # 백그라운드에서 이메일 발송
        try:
            from ...tasks.email_tasks import send_case_reviewed_email
            if background_tasks:
                background_tasks.add_task(send_case_reviewed_email, case_id)
            logger.info(f"케이스 검토 완료 이메일 태스크 등록: Case ID {case_id}")
        except Exception as e:
            # 이메일 발송 실패는 케이스 종료 자체를 실패시키지 않음
            logger.warning(f"케이스 검토 완료 이메일 태스크 등록 실패: {str(e)}")
        
        return case
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"케이스 종료 실패: {str(e)}", exc_info=True)
        raise DatabaseException("케이스 종료 중 오류가 발생했습니다")

@router.post("/cases/{case_id}/lock", response_model=schemas.CaseResponse)
def lock_case(
    case_id: int,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """케이스 편집 잠금 설정"""
    if current_user.role not in [models.UserRole.SECURITY_ADMIN, models.UserRole.SYSTEM_ADMIN, models.UserRole.AUDIT_TEAM]:
        raise AuthorizationException("케이스를 잠글 권한이 없습니다")

    case = db.query(models.ClarificationCase).filter(models.ClarificationCase.case_id == case_id).first()
    if not case:
        raise NotFoundException("케이스를 찾을 수 없습니다")

    # 자동 잠금 해제 체크 (30분 경과 시)
    if case.locked_by_id and case.locked_at:
        expiry = datetime.now() - timedelta(minutes=30)
        if case.locked_at < expiry:
            logger.info(f"케이스 잠금 만료 자동 해제: Case ID {case_id}, Previous User: {case.locked_by_id}")
            case.locked_by_id = None
            case.locked_at = None

    if case.locked_by_id and case.locked_by_id != current_user.user_id:
        locked_user = db.query(models.User).filter(models.User.user_id == case.locked_by_id).first()
        user_name = locked_user.user_name if locked_user else "알 수 없음"
        raise ValidationException(f"이 케이스는 현재 {user_name}님에 의해 편집 중입니다")

    try:
        case.locked_by_id = current_user.user_id
        case.locked_at = datetime.now()
        db.commit()
        db.refresh(case)
        
        # 응답용 가상 필드 설정
        case.locked_by_name = current_user.user_name
        
        logger.info(f"케이스 잠금 설정: Case ID {case_id}, User: {current_user.user_email}")
        return case
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"케이스 잠금 실패: {str(e)}")
        raise DatabaseException("케이스 잠금 중 오류가 발생했습니다")

@router.post("/cases/{case_id}/unlock", response_model=schemas.CaseResponse)
def unlock_case(
    case_id: int,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """케이스 편집 잠금 해제"""
    case = db.query(models.ClarificationCase).filter(models.ClarificationCase.case_id == case_id).first()
    if not case:
        raise NotFoundException("케이스를 찾을 수 없습니다")

    if case.locked_by_id and case.locked_by_id != current_user.user_id and current_user.role != models.UserRole.SYSTEM_ADMIN:
        raise AuthorizationException("본인이 잠근 케이스만 해제할 수 있습니다")

    try:
        case.locked_by_id = None
        case.locked_at = None
        db.commit()
        db.refresh(case)
        
        logger.info(f"케이스 잠금 해제: Case ID {case_id}, User: {current_user.user_email}")
        return case
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"케이스 잠금 해제 실패: {str(e)}")
        raise DatabaseException("케이스 잠금 해제 중 오류가 발생했습니다")
