import json
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ... import models
from ...core.logging_config import get_logger

logger = get_logger(__name__)

def extract_value(data: dict, key_path: str):
    """Simple dot-notation dict extractor, e.g., 'LocationDetails.state'. 
       Supports constant strings if wrapped in quotes e.g., \"Matched\" or 'STATIC'."""
    if not key_path:
        return None
        
    # Check for constant string
    if (key_path.startswith('"') and key_path.endswith('"')) or (key_path.startswith("'") and key_path.endswith("'")):
        if len(key_path) >= 2:
            return key_path[1:-1]
            
    keys = key_path.split('.')
    val = data
    for k in keys:
        if isinstance(val, dict):
            val = val.get(k)
        else:
            return None
    return val

def apply_dynamic_mapping(db: Session, log_data: dict, mapping: dict, requester: models.User, siem_type: models.SiemType = models.SiemType.SENTINEL) -> models.ClarificationCase:
    """
    Applies the provided field mapping to the SIEM log JSON (log_data)
    and constructs a ClarificationCase model instance.
    """
    # support both old and new mapping structures for safety
    user_identifier_key = mapping.get("related_employee_id") or mapping.get("user_identifier_key")
    rule_title_key = mapping.get("rule_title") or mapping.get("rule_title_key")
    summary_key = mapping.get("summary") or mapping.get("summary_key")
    
    # 1. 대상 사용자 식별
    target_email = extract_value(log_data, user_identifier_key) if user_identifier_key else None
    
    user = None
    if target_email:
        user = db.query(models.User).filter(models.User.user_email == target_email).first()
        
    if not user:
        if target_email:
            # 1.1 미등록 사용자인 경우 자동 생성 (Shadow User)
            try:
                user = models.User(
                    user_email=target_email,
                    user_name=target_email.split('@')[0],
                    hashed_password=f"SIEM_AUTO_{uuid.uuid4().hex}", # 로그인 불가한 난수 해시
                    role=models.UserRole.USER,
                    department="미지정",
                    company="SIEM 자동생성"
                )
                db.add(user)
                db.flush() # ID 생성을 위해 flush
                logger.info(f"SIEM 미등록 사용자 자동 생성: {target_email} (ID: {user.user_id})")
            except Exception as e:
                db.rollback()
                user = requester
                logger.error(f"SIEM 사용자 자동 생성 실패: {e}. 요청자 ID({requester.user_id}) 임시 할당.")
        else:
            # 이메일 정보가 없는 경우 요청자(관리자)를 임시 할당
            user = requester
            logger.warning(f"SIEM 로그 매칭 실패: 이메일 정보 없음. 요청자 ID({requester.user_id}) 임시 할당.")
        
    # 2. 필수 기본 필드 추출 및 포맷팅
    title = extract_value(log_data, rule_title_key) if rule_title_key else None
    if not title: 
        title = "알 수 없는 보안 행위 감지"
        
    summary = extract_value(log_data, summary_key) if summary_key else None
    if not summary: 
        summary = "로그에서 요약 정보를 추출할 수 없습니다."
    
    # rule_description은 전체 JSON을 파싱해서 보관
    try:
        rule_desc = json.dumps(log_data, indent=2, ensure_ascii=False)
    except:
        rule_desc = str(log_data)
    
    # 기본 인자
    case_kwargs = {
        "siem_type": siem_type,
        "rule_title": f"[SIEM 탐지] {title}",
        "summary": str(summary)[:500], # 최대 500자까지 자름
        "rule_description": rule_desc,
        "case_type": models.CaseType.SYSTEM_ACCESS,
        "related_employee_id": user.user_id,
        "requester_id": requester.user_id,
        "due_date": datetime.now() + timedelta(days=7),
        "case_status": models.CaseStatus.UNCLASSIFIED
    }
    
    # 3. 추가 동적 매핑 필드 적용 (UI table fields)
    valid_columns = ["incident_num", "case_type", "original_log_link", "priority", "rule_description", "case_status", "case_result"]
    for col in valid_columns:
        key = mapping.get(col)
        if key:
            val = extract_value(log_data, key)
            if val is not None:
                # Type conversions
                if col == "incident_num":
                    try: val = int(val)
                    except: continue
                elif col == "priority":
                    try: val = models.CasePriority[str(val).upper()]
                    except: continue
                elif col == "case_type":
                    try: val = models.CaseType[str(val).upper()]
                    except: continue
                elif col == "case_status":
                    try: val = models.CaseStatus[str(val).upper()]
                    except: continue
                elif col == "case_result":
                    try: val = models.CaseResult[str(val).upper()]
                    except: continue
                
                case_kwargs[col] = val
                
    # 날짜 필드 파싱
    for date_col in ["created_at", "due_date"]:
        key = mapping.get(date_col)
        if key:
            val = extract_value(log_data, key)
            if val:
                try:
                    # ISO 포맷 변환 시도
                    case_kwargs[date_col] = datetime.fromisoformat(str(val).replace("Z", "+00:00")).replace(tzinfo=None)
                except Exception as e:
                    logger.warning(f"날짜 형식 변환 실패 ({date_col}): {val} - {e}")

    new_case = models.ClarificationCase(**case_kwargs)
    return new_case
