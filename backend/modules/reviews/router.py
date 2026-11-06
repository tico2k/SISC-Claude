from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from ... import models, schemas
from ...core import dependencies
from ...core.database import get_db
from ...core.exceptions import AuthorizationException, NotFoundException, DatabaseException
from ...core.logging_config import get_logger
from ..cases import services as case_services

logger = get_logger(__name__)
router = APIRouter(tags=["Reviews"])

@router.post("/reviews", response_model=schemas.ReviewResponse, status_code=status.HTTP_201_CREATED)
def create_review(
    review: schemas.ReviewCreate,
    request: Request,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """리뷰 생성 및 케이스 상태 업데이트"""
    # 권한 확인
    if current_user.role not in [models.UserRole.SECURITY_ADMIN, models.UserRole.AUDIT_TEAM, models.UserRole.SYSTEM_ADMIN]:
        logger.warning(f"권한 없는 리뷰 생성 시도: {current_user.user_email}")
        raise AuthorizationException("리뷰를 생성할 권한이 없습니다")
        
    # 케이스 조회
    case = db.query(models.ClarificationCase).filter(models.ClarificationCase.case_id == review.case_id).first()
    if not case:
        logger.warning(f"존재하지 않는 케이스에 대한 리뷰 시도: Case ID {review.case_id}")
        raise NotFoundException("케이스를 찾을 수 없습니다")

    # 상태 전이·심의 결과·잠금 검사 (SUBMIT → APPROVE | REJECT)
    case_services.ensure_can_review(case, current_user, review.case_status, review.case_result)

    try:
        # 리뷰 생성
        new_review = models.ReviewHistory(
            case_id=review.case_id,
            reviewer_id=current_user.user_id,
            case_status=review.case_status,
            case_result=review.case_result,
            comments=review.comments
        )
        db.add(new_review)
        
        # 케이스 상태 및 결과 업데이트
        case.case_status = review.case_status
        case.case_result = review.case_result
        case.final_reviewer = current_user
        case.final_reviewer_id = current_user.user_id
        case.final_review_date = new_review.reviewed_at

        case_services.add_audit_log(
            db, current_user,
            f"CASE_REVIEWED: Case {case.case_id} -> {review.case_status.value} ({review.case_result.value})",
            request,
        )
        db.commit()
        db.refresh(new_review)
        
        logger.info(
            f"리뷰 생성 성공: Case ID {review.case_id}, "
            f"Reviewer: {current_user.user_email}, Status: {review.case_status}, Result: {review.case_result}"
        )
        return new_review
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"리뷰 생성 실패: {str(e)}", exc_info=True)
        raise DatabaseException("리뷰 생성 중 오류가 발생했습니다")
