from fastapi import APIRouter, Depends, Request, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List
import os
from pathlib import Path
from ... import models, schemas
from ...core import dependencies
from ...core.database import get_db
from ...utils.file_upload import validate_and_save_file
from ...core.exceptions import AuthorizationException, NotFoundException, DatabaseException, FileUploadException
from ...core.logging_config import get_logger
from ..cases import services as case_services

logger = get_logger(__name__)
router = APIRouter(tags=["Submissions"])

UPLOAD_DIR = Path("uploads").resolve()

@router.post("/submissions", response_model=schemas.SubmissionResponse, status_code=status.HTTP_201_CREATED)
async def create_submission(
    request: Request,
    case_id: int = Form(...),
    content: str = Form(...),
    classification: str = Form(...),
    files: List[UploadFile] = File(None),
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """소명 제출 및 파일 업로드"""
    # ... (기존 코드와 동일)
    # 61번 라인 부근 수정: submission_dir = UPLOAD_DIR / str(case_id) / str(new_submission.submission_id)
    # resolve()된 UPLOAD_DIR를 사용하므로 안전함.
    """소명 제출 및 파일 업로드"""
    # 케이스 조회
    case = db.query(models.ClarificationCase).filter(models.ClarificationCase.case_id == case_id).first()
    if not case:
        logger.warning(f"존재하지 않는 케이스에 소명 제출 시도: Case ID {case_id}")
        raise NotFoundException("케이스를 찾을 수 없습니다")

    # 권한·상태 확인: 관리자 또는 본인(숨김 상태 제외), 상태는 REQUEST 또는 반려 A(재소명)
    try:
        case_services.ensure_can_submit(case, current_user)
    except AuthorizationException:
        logger.warning(
            f"권한 없는 소명 제출 시도: User {current_user.user_email} (ID: {current_user.user_id}), "
            f"Case Owner ID: {case.related_employee_id}, Status: {case.case_status}"
        )
        raise
    
    try:
        # 소명 생성
        new_submission = models.ClarificationSubmission(
            case_id=case_id,
            submitter_id=current_user.user_id,
            content=content,
            classification=classification
        )
        db.add(new_submission)
        db.flush()
        
        # 파일 업로드 처리
        file_count = 0
        if files:
            submission_dir = UPLOAD_DIR / str(case_id) / str(new_submission.submission_id)
            
            for file in files:
                if not file.filename:
                    continue
                
                try:
                    # 파일 검증 및 저장
                    original_filename, safe_filename, file_size = await validate_and_save_file(
                        file=file,
                        upload_dir=submission_dir
                    )
                    
                    file_path = submission_dir / safe_filename
                    
                    # 첨부파일 레코드 생성
                    attachment = models.ClarificationAttachment(
                        submission_id=new_submission.submission_id,
                        original_filename=original_filename,
                        stored_filename=safe_filename,
                        file_path=str(file_path),
                        file_size=file_size
                    )
                    db.add(attachment)
                    file_count += 1
                    
                except FileUploadException as e:
                    db.rollback()
                    logger.error(f"파일 업로드 실패: {original_filename if 'original_filename' in locals() else file.filename} - {str(e)}")
                    raise

        # 케이스 상태를 '제출'로 자동 변경
        case.case_status = models.CaseStatus.SUBMIT

        case_services.add_audit_log(
            db, current_user,
            f"CASE_SUBMITTED: Case {case_id} (Submission {new_submission.submission_id}, Files {file_count})",
            request,
        )
        db.commit()
        db.refresh(new_submission)
        
        logger.info(
            f"소명 제출 성공: Case ID {case_id}, Submission ID {new_submission.submission_id}, "
            f"Submitter: {current_user.user_email}, Files: {file_count}"
        )
        return new_submission
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"소명 제출 실패: {str(e)}", exc_info=True)
        raise DatabaseException("소명 제출 중 오류가 발생했습니다")

@router.get("/attachments/{file_id}")
def download_attachment(
    file_id: int,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """첨부파일 다운로드"""
    # 첨부파일 조회
    attachment = db.query(models.ClarificationAttachment).filter(
        models.ClarificationAttachment.file_id == file_id
    ).first()
    
    if not attachment:
        logger.warning(f"존재하지 않는 첨부파일 다운로드 시도: File ID {file_id}")
        raise NotFoundException("첨부파일을 찾을 수 없습니다")
    
    # 연관된 케이스 확인
    if attachment.submission:
        case = attachment.submission.case
    elif attachment.case:
        case = attachment.case
    else:
        logger.error(f"케이스가 연관되지 않은 첨부파일: File ID {file_id}")
        raise NotFoundException("연관된 케이스를 찾을 수 없습니다")
    
    # 권한 확인: 관리자 또는 본인(미확인·종결 케이스 제외)
    if not case_services.can_user_access_case(current_user, case):
        logger.warning(
            f"권한 없는 파일 다운로드 시도: User {current_user.user_email}, "
            f"File ID {file_id}, Case ID {case.case_id}"
        )
        raise AuthorizationException("이 파일에 접근할 권한이 없습니다")
    
    # 파일 존재 확인
    target_path = Path(attachment.file_path).resolve()
    
    # Path Traversal 방지: target_path가 UPLOAD_DIR 하위에 있는지 확인
    # (문자열 접두사 비교는 'uploads_evil/' 같은 형제 폴더를 통과시키므로 경로 단위로 비교)
    if not target_path.is_relative_to(UPLOAD_DIR):
        logger.error(f"보안 경고: 의도되지 않은 파일 접근 시도 (Path Traversal)! User: {current_user.user_email}, Path: {target_path}")
        raise AuthorizationException("잘못된 파일 경로입니다.")

    if not target_path.exists():
        logger.error(f"서버에서 파일을 찾을 수 없음: File ID {file_id}, Path: {target_path}")
        raise NotFoundException("서버에서 파일을 찾을 수 없습니다")
    
    logger.info(
        f"파일 다운로드: File ID {file_id}, User: {current_user.user_email}, "
        f"Filename: {attachment.original_filename}"
    )
    
    return FileResponse(
        path=str(target_path),
        filename=attachment.original_filename,
        media_type='application/octet-stream'
    )
