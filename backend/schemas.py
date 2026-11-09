from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime
from .models import UserRole, SiemType, CaseType, CaseStatus, CaseResult, CasePriority

# --- User Schemas ---
class UserBase(BaseModel):
    user_email: str
    user_name: str
    company: Optional[str] = None
    department: Optional[str] = None
    role: UserRole
    manager_id: Optional[int] = None  # 부서장(참조 알림 수신자)

class UserCreate(UserBase):
    password: str

class UserUpdate(UserBase):
    password: Optional[str] = None

class UserLogin(BaseModel):
    user_email: str
    password: str

class EntraLoginRequest(BaseModel):
    id_token: str  # MSAL 로그인 결과의 ID 토큰 (서버에서 서명·aud·tid 검증)

class UserResponse(UserBase):
    user_id: int
    idate: Optional[datetime] = None
    udate: datetime

    model_config = ConfigDict(from_attributes=True)

class PasswordChange(BaseModel):
    old_password: str
    new_password: str

# --- Token Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_email: Optional[str] = None
    role: Optional[str] = None

class AuthConfigResponse(BaseModel):
    allow_local: bool
    allow_entra: bool
    default_method: str
    # Entra 연동이 활성화된 경우에만 채워짐 (공개 값, 프론트 MSAL 초기화용)
    entra_client_id: Optional[str] = None
    entra_tenant_id: Optional[str] = None

# --- Integration Schemas ---
class EntraIntegrationUpdate(BaseModel):
    is_enabled: bool = False
    tenant_id: Optional[str] = None
    client_id: Optional[str] = None
    # None 또는 '********': 기존 값 유지 / '': 삭제 / 그 외: 새 값으로 교체
    client_secret: Optional[str] = None
    mail_sender: Optional[str] = None

class EntraIntegrationResponse(BaseModel):
    is_enabled: bool
    tenant_id: Optional[str] = None
    client_id: Optional[str] = None
    client_secret_set: bool
    mail_sender: Optional[str] = None
    updated_at: Optional[datetime] = None

class TeamsIntegrationUpdate(BaseModel):
    is_enabled: bool = False
    # None 또는 '********': 기존 값 유지 / '': 삭제 / 그 외: 새 URL(https)로 교체
    webhook_url: Optional[str] = None

class TeamsIntegrationResponse(BaseModel):
    is_enabled: bool
    webhook_url_set: bool
    updated_at: Optional[datetime] = None

class NotificationTemplateResponse(BaseModel):
    template_key: str
    name: str
    description: str
    variables: List[str]
    subject: str
    body_html: str
    is_customized: bool
    updated_at: Optional[datetime] = None

class NotificationTemplateUpdate(BaseModel):
    subject: str
    body_html: str

class NotificationPreviewResponse(BaseModel):
    subject: str
    body_html: str

class IntegrationTestResponse(BaseModel):
    status: str  # success / error
    message: str

# --- Attachment Schemas (Moved up) ---
class AttachmentResponse(BaseModel):
    file_id: int
    original_filename: str
    file_size: Optional[int] = None
    sha256: Optional[str] = None  # 업로드 시점 해시 (없으면 무결성 미검증 파일)
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Case Schemas ---
class CaseBase(BaseModel):
    siem_type: Optional[SiemType] = SiemType.SENTINEL
    rule_title: str
    rule_description: Optional[str] = None
    incident_num: Optional[int] = None
    summary: Optional[str] = None
    case_type: CaseType
    due_date: datetime
    priority: Optional[CasePriority] = CasePriority.MEDIUM

class CaseCreate(CaseBase):
    related_employee_id: int
    original_log_link: Optional[str] = None # Added for SIEM link

class CaseResponse(CaseBase):
    case_id: int
    requester_id: Optional[int] = None
    related_employee_id: Optional[int] = None
    created_at: datetime
    case_status: CaseStatus
    case_result: Optional[CaseResult] = None
    final_review_date: Optional[datetime] = None
    final_reviewer_id: Optional[int] = None
    related_employee: Optional[UserBase] = None # Added for UI display
    submissions: List['SubmissionResponse'] = [] # Is populated by ORM default if lazy=joined or manual
    attachments: List[AttachmentResponse] = [] # Admin attachments
    review_comment: Optional[str] = None
    reviewer_name: Optional[str] = None
    original_log_link: Optional[str] = None # Added for UI display
    locked_by_id: Optional[int] = None
    locked_at: Optional[datetime] = None
    locked_by_name: Optional[str] = None # For UI display
    is_overdue: bool = False  # 소명 요청 상태에서 기한 경과
    legal_hold: bool = False  # 증거 보존 지정 (보존기간 경과 후에도 파기 제외)
    legal_hold_reason: Optional[str] = None
    anonymized_at: Optional[datetime] = None  # 보존기간 경과로 개인정보 익명화된 시각

    model_config = ConfigDict(from_attributes=True)

class PaginatedCaseResponse(BaseModel):
    items: List[CaseResponse]
    total: int
    page: int
    size: int
    pages: int

class LegalHoldRequest(BaseModel):
    hold: bool
    reason: Optional[str] = None

class EmployeeCaseSummary(BaseModel):
    case_id: int
    rule_title: str
    case_type: CaseType
    case_status: CaseStatus
    case_result: Optional[CaseResult] = None
    priority: Optional[CasePriority] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class EmployeeHistoryResponse(BaseModel):
    """심의 참고용: 같은 직원의 다른 케이스 이력 (현재 케이스 제외)"""
    employee_id: Optional[int] = None
    employee_name: Optional[str] = None
    total: int
    rejected: int          # 반려 건수
    disciplinary: int      # 징계 요청(감사 이관) 건수
    by_status: dict
    by_result: dict
    recent: List[EmployeeCaseSummary]

class CaseCloseRequest(BaseModel):
    case_result: CaseResult
    close_reason: str

# --- Submission Schemas ---
class SubmissionBase(BaseModel):
    content: str
    classification: Optional[str] = None

class SubmissionCreate(SubmissionBase):
    case_id: int

class SubmissionResponse(SubmissionBase):
    submission_id: int
    case_id: int
    submitter_id: Optional[int] = None
    submitted_at: datetime
    attachments: List[AttachmentResponse] = []

    model_config = ConfigDict(from_attributes=True)

# --- Review Schemas ---
class ReviewCreate(BaseModel):
    case_id: int
    case_status: CaseStatus
    case_result: CaseResult
    comments: Optional[str] = None

class ReviewResponse(ReviewCreate):
    review_id: int
    reviewer_id: int
    reviewed_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Log Schemas ---
class LoginHistoryResponse(BaseModel):
    login_id: int
    user_id: int
    login_at: datetime
    ip_address: Optional[str]
    status: str

    model_config = ConfigDict(from_attributes=True)

class SystemAuditLogResponse(BaseModel):
    log_id: int
    user_id: Optional[int] = None
    # Model has actor_id. Relationship 'actor'.
    actor_id: Optional[int]
    action: str
    ip_address: Optional[str]
    occurred_at: datetime
    actor: Optional[UserBase] = None

    model_config = ConfigDict(from_attributes=True)

class BackgroundJobLogResponse(BaseModel):
    log_id: int
    job_id: str
    job_name: str
    status: str
    execution_type: str
    execution_time: datetime
    records_processed: int
    message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

# --- SIEM Schemas ---
class SiemConfigBase(BaseModel):
    siem_type: 'SiemType'
    name: str
    host_url: str
    tenant_id: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    subscription_id: Optional[str] = None
    resource_group: Optional[str] = None
    workspace_name: Optional[str] = None
    api_key: Optional[str] = None
    test_query: Optional[str] = None
    field_mapping: Optional[dict] = None
    cron_expression: Optional[str] = None
    is_active: bool = True

class SiemConfigCreate(SiemConfigBase):
    pass

class SiemTestConnectionRequest(SiemConfigBase):
    siem_id: Optional[int] = None

class SiemCaseConvertRequest(BaseModel):
    config_id: Optional[int] = None
    log_data: dict
    mapping_override: Optional[dict] = None

class SiemConfigUpdate(BaseModel):
    siem_type: Optional['SiemType'] = None
    name: Optional[str] = None
    host_url: Optional[str] = None
    tenant_id: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    subscription_id: Optional[str] = None
    resource_group: Optional[str] = None
    workspace_name: Optional[str] = None
    api_key: Optional[str] = None
    test_query: Optional[str] = None
    field_mapping: Optional[dict] = None
    cron_expression: Optional[str] = None
    is_active: Optional[bool] = None

class SiemConfigResponse(SiemConfigBase):
    siem_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class SiemSyncHistoryBase(BaseModel):
    siem_id: int
    execution_time: datetime
    status: str
    records_fetched: int
    error_message: Optional[str] = None

class SiemSyncHistoryResponse(SiemSyncHistoryBase):
    history_id: int

    model_config = ConfigDict(from_attributes=True)


# --- Environment Config Schemas ---
class EnvEntry(BaseModel):
    key: str
    value: str
    is_sensitive: bool = False
    category: str = "General"
    description: str = ""

class EnvResponse(BaseModel):
    backend: List[EnvEntry]
    frontend: List[EnvEntry]

class EnvUpdateRequest(BaseModel):
    file_type: str  # "backend" or "frontend"
    key: str
    value: str

# --- Job Schemas ---
class JobResponse(BaseModel):
    id: str
    name: str
    next_run_time: Optional[datetime] = None
    status: str
    cron_expression: Optional[str] = None

class JobRescheduleRequest(BaseModel):
    cron_expression: str

# --- Menu Permission Schemas ---
class MenuPermissionBase(BaseModel):
    role: UserRole
    menu_path: str
    is_visible: bool

class MenuPermissionResponse(MenuPermissionBase):
    permission_id: int

    model_config = ConfigDict(from_attributes=True)

class MenuPermissionUpdate(BaseModel):
    is_visible: bool

# Resolve forward references
CaseResponse.model_rebuild()
