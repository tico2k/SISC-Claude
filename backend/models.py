from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, ForeignKey, Text, Enum, Index, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, false as sa_false
import enum
from datetime import datetime
from .core.database import Base

# Enums based on SQL constraints
class UserRole(str, enum.Enum):
    USER = "일반"
    SECURITY_ADMIN = "보안관리자"
    AUDIT_TEAM = "감사팀"
    SYSTEM_ADMIN = "시스템관리자"

class SiemType(str, enum.Enum):
    SENTINEL = "Sentinel"
    ELK = "ELK"
    SPLUNK = "Splunk"

class CaseType(str, enum.Enum): # Mapped from SQL 'status' check constraint which seemed to be case type
    INFO_LEAK = "정보유출"
    SECURITY_VIOLATION = "보안위반"
    SYSTEM_ACCESS = "시스템접근"
    AUTH_ABUSE = "권한오남용"

class CaseStatus(str, enum.Enum):
    UNCLASSIFIED = "미확인"
    REQUEST = "요청"
    SUBMIT = "제출"
    APPROVE = "승인"
    REJECT = "반려"
    CLOSE = "종결"

class CaseResult(str, enum.Enum):
    JUSTIFIED = "정당 사유"
    FALSE_POSITIVE = "오탐" # Added
    MINOR_VIOLATION = "경미한 위반" # Added
    INSUFFICIENT = "소명 불충분" # Added
    EDUCATION_NEEDED = "교육 필요"
    DISCIPLINARY_ACTION = "징계 요청"

class CasePriority(str, enum.Enum):
    LOW = "낮음"
    MEDIUM = "보통"
    HIGH = "높음"

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String(150), unique=True, index=True, nullable=False)
    user_name = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    company = Column(String(100))
    department = Column(String(100))
    role = Column(Enum(UserRole), nullable=False)
    last_login = Column(DateTime, nullable=True)  # 마지막 로그인 시간
    # 부서장(참조 알림 수신자). 결재 권한은 없고 소명 제출·기한 초과 시 참조 메일만 받는다
    manager_id = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    idate = Column(DateTime)
    udate = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    clarification_cases_related = relationship("ClarificationCase", foreign_keys="ClarificationCase.related_employee_id", back_populates="related_employee")
    clarification_cases_requested = relationship("ClarificationCase", foreign_keys="ClarificationCase.requester_id", back_populates="requester")
    submissions = relationship("ClarificationSubmission", back_populates="submitter")
    reviews = relationship("ReviewHistory", back_populates="reviewer")
    audit_logs = relationship("SystemAuditLog", back_populates="actor")
    login_history = relationship("LoginHistory", back_populates="user")
    final_reviews = relationship("ClarificationCase", foreign_keys="ClarificationCase.final_reviewer_id", back_populates="final_reviewer")
    manager = relationship("User", remote_side=[user_id], foreign_keys=[manager_id])



class ClarificationCase(Base):
    __tablename__ = "clarification_case"

    case_id = Column(Integer, primary_key=True, index=True)
    siem_type = Column(Enum(SiemType), default=SiemType.SENTINEL)
    rule_title = Column(String(200), nullable=False)
    rule_description = Column(Text)
    incident_num = Column(Integer)
    summary = Column(Text)
    case_type = Column(Enum(CaseType), nullable=False)
    related_employee_id = Column(Integer, ForeignKey("users.user_id"))
    requester_id = Column(Integer, ForeignKey("users.user_id"))
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    due_date = Column(DateTime, nullable=False)
    case_status = Column(Enum(CaseStatus), nullable=False, default=CaseStatus.UNCLASSIFIED)
    case_result = Column(Enum(CaseResult), nullable=True)
    priority = Column(Enum(CasePriority), default=CasePriority.MEDIUM)
    final_review_date = Column(DateTime)
    final_reviewer_id = Column(Integer, ForeignKey("users.user_id"))
    original_log_link = Column(Text, nullable=True)
    locked_by_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    locked_at = Column(DateTime, nullable=True)
    # 기한 초과 알림 발송 시각 (중복 발송 방지)
    overdue_notified_at = Column(DateTime, nullable=True)
    # 증거 보존(legal hold): 지정된 케이스는 보존기간이 지나도 파기하지 않음
    legal_hold = Column(Boolean, default=False, server_default=sa_false(), nullable=False)
    legal_hold_reason = Column(Text, nullable=True)
    # 보존기간 경과로 개인정보를 익명화한 시각
    anonymized_at = Column(DateTime, nullable=True)

    # 성능 최적화를 위한 인덱스
    __table_args__ = (
        Index('idx_case_status', 'case_status'),
        Index('idx_employee_status', 'related_employee_id', 'case_status'),
        Index('idx_created_at', 'created_at'),
    )

    # Relationships
    related_employee = relationship("User", foreign_keys=[related_employee_id], back_populates="clarification_cases_related")
    requester = relationship("User", foreign_keys=[requester_id], back_populates="clarification_cases_requested")
    final_reviewer = relationship("User", foreign_keys=[final_reviewer_id], back_populates="final_reviews")
    locked_by = relationship("User", foreign_keys=[locked_by_id])
    submissions = relationship("ClarificationSubmission", back_populates="case", cascade="all, delete-orphan")
    review_history = relationship("ReviewHistory", back_populates="case", cascade="all, delete-orphan")
    attachments = relationship("ClarificationAttachment", back_populates="case", cascade="all, delete-orphan")

    @property
    def is_overdue(self) -> bool:
        """소명 요청 상태에서 기한이 지난 경우 (상태는 바꾸지 않고 표시·알림에만 사용)"""
        return (
            self.case_status == CaseStatus.REQUEST
            and self.due_date is not None
            and self.due_date < datetime.now()
        )


class ClarificationSubmission(Base):
    __tablename__ = "clarification_submission"

    submission_id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("clarification_case.case_id", ondelete="CASCADE"))
    submitter_id = Column(Integer, ForeignKey("users.user_id"))
    submitted_at = Column(DateTime, server_default=func.now(), nullable=False)
    content = Column(Text, nullable=False)
    classification = Column(String(50))

    # 성능 최적화를 위한 인덱스
    __table_args__ = (
        Index('idx_submission_case_id', 'case_id'),
        Index('idx_submission_submitter_id', 'submitter_id'),
        Index('idx_submitted_at', 'submitted_at'),
    )

    # Relationships
    case = relationship("ClarificationCase", back_populates="submissions")
    submitter = relationship("User", back_populates="submissions")
    attachments = relationship("ClarificationAttachment", back_populates="submission", cascade="all, delete-orphan")


class ClarificationAttachment(Base):
    __tablename__ = "clarification_attachment"

    file_id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("clarification_submission.submission_id", ondelete="CASCADE"), nullable=True)
    case_id = Column(Integer, ForeignKey("clarification_case.case_id", ondelete="CASCADE"), nullable=True)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)
    file_size = Column(Integer)
    sha256 = Column(String(64), nullable=True)  # 업로드 시점 해시 (다운로드 시 무결성 검증, 기존 파일은 NULL)
    uploaded_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    submission = relationship("ClarificationSubmission", back_populates="attachments")
    case = relationship("ClarificationCase", back_populates="attachments")


class ReviewHistory(Base):
    __tablename__ = "review_history"

    review_id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("clarification_case.case_id", ondelete="CASCADE"))
    reviewer_id = Column(Integer, ForeignKey("users.user_id"))
    reviewed_at = Column(DateTime, server_default=func.now(), nullable=False)
    case_status = Column(Enum(CaseStatus), nullable=False)
    case_result = Column(Enum(CaseResult), nullable=False)
    comments = Column(Text)

    # 성능 최적화를 위한 인덱스
    __table_args__ = (
        Index('idx_review_case_id', 'case_id'),
        Index('idx_review_reviewer_id', 'reviewer_id'),
        Index('idx_reviewed_at', 'reviewed_at'),
    )

    # Relationships
    case = relationship("ClarificationCase", back_populates="review_history")
    reviewer = relationship("User", back_populates="reviews")


class SystemAuditLog(Base):
    __tablename__ = "system_audit_log"

    log_id = Column(Integer, primary_key=True, index=True)
    occurred_at = Column(DateTime, server_default=func.now(), nullable=False)
    actor_id = Column(Integer, ForeignKey("users.user_id"))
    action = Column(Text, nullable=False)
    ip_address = Column(String(45)) # String for IP, supports IPv6

    # Relationships
    actor = relationship("User", back_populates="audit_logs")


class LoginHistory(Base):
    __tablename__ = "login_history"

    login_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    login_at = Column(DateTime, server_default=func.now(), nullable=False)
    ip_address = Column(String(45))
    status = Column(String(20), default="SUCCESS")

    # 성능 최적화를 위한 인덱스
    __table_args__ = (
        Index('idx_login_user_id', 'user_id'),
        Index('idx_login_at', 'login_at'),
    )

    # Relationships
    user = relationship("User", back_populates="login_history")


class SiemConfiguration(Base):
    __tablename__ = "siem_configuration"

    siem_id = Column(Integer, primary_key=True, index=True)
    siem_type = Column(Enum(SiemType), nullable=False)
    name = Column(String(100), nullable=False)
    host_url = Column(String(255), nullable=False) # SIEM 관리 API 주소 (SIEM 종류별)
    tenant_id = Column(String(100)) # For Sentinel
    client_id = Column(String(100)) # For Sentinel
    client_secret = Column(String(255)) # For Sentinel (Encrypted ideally)
    subscription_id = Column(String(100)) # For Sentinel
    resource_group = Column(String(100)) # For Sentinel
    workspace_name = Column(String(100)) # For Sentinel
    api_key = Column(String(255)) # For others like Splunk/ELK
    test_query = Column(Text, nullable=True) # Custom KQL query for testing
    field_mapping = Column(JSON, nullable=True) # Dynamic key-to-column mapping for SIEM events
    is_active = Column(Boolean, default=True)
    cron_expression = Column(String(50), nullable=True) # Schedule expression
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

class IntegrationSetting(Base):
    """설치 후 관리자가 설정하는 외부 연동 정보 (provider별 1행, 예: ENTRA)"""
    __tablename__ = "integration_setting"

    provider = Column(String(50), primary_key=True)
    is_enabled = Column(Boolean, default=False, nullable=False)
    tenant_id = Column(String(100))
    client_id = Column(String(100))
    client_secret = Column(String(500))  # Fernet 암호문
    mail_sender = Column(String(150))  # Outlook(Graph) 메일 발송용 공용 사서함
    webhook_url = Column(String(1000))  # Teams 채널 웹훅 URL (Fernet 암호문, provider=TEAMS)
    updated_by = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

class NotificationTemplate(Base):
    """관리자가 화면에서 수정한 알림 메일 템플릿 (행이 없으면 기본 파일 템플릿 사용)"""
    __tablename__ = "notification_template"

    template_key = Column(String(100), primary_key=True)  # 예: case_created.html
    subject = Column(String(500), nullable=False)
    body_html = Column(Text, nullable=False)
    updated_by = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

class SiemSyncHistory(Base):
    __tablename__ = "siem_sync_history"
    
    history_id = Column(Integer, primary_key=True, index=True)
    siem_id = Column(Integer, ForeignKey("siem_configuration.siem_id", ondelete="CASCADE"), nullable=False)
    execution_time = Column(DateTime, server_default=func.now(), nullable=False)
    status = Column(String(20), nullable=False) # SUCCESS / FAILED
    records_fetched = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    __table_args__ = (
        Index('idx_siem_sync_history_time', 'execution_time'),
    )

    # Relationships
    siem_config = relationship("SiemConfiguration", backref="sync_history")

class DailyStatistic(Base):
    __tablename__ = "daily_statistic"
    
    stat_date = Column(DateTime, primary_key=True, index=True) # Date type instead of DateTime as we just need the day
    unclassified_count = Column(Integer, default=0, nullable=False)
    request_count = Column(Integer, default=0, nullable=False)
    submit_count = Column(Integer, default=0, nullable=False)
    reviewed_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

class WeeklyReport(Base):
    __tablename__ = "weekly_report"
    
    report_id = Column(Integer, primary_key=True, index=True)
    week_start = Column(Date, nullable=False, index=True)
    week_end = Column(Date, nullable=False)
    created_count = Column(Integer, default=0, nullable=False)
    approved_count = Column(Integer, default=0, nullable=False)
    rejected_count = Column(Integer, default=0, nullable=False)
    generated_at = Column(DateTime, server_default=func.now(), nullable=False)

class BackgroundJobLog(Base):
    """모든 백그라운드 작업의 통합 실행 로그"""
    __tablename__ = "background_job_log"

    log_id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(100), index=True, nullable=False) # 예: sync_siem_logs_4, generate_daily_statistics
    job_name = Column(String(100), nullable=False) # 한글 명칭
    status = Column(String(20), nullable=False) # SUCCESS / FAILED / RUNNING
    execution_type = Column(String(20), nullable=False) # AUTO / MANUAL
    execution_time = Column(DateTime, server_default=func.now(), nullable=False)
    records_processed = Column(Integer, default=0)
    message = Column(Text, nullable=True)

class SystemJobConfiguration(Base):
    """시스템 기본 백그라운드 작업의 크론 설정 저장"""
    __tablename__ = "system_job_configuration"

    job_id = Column(String(100), primary_key=True)  # 운영 DB 실제 길이(VARCHAR(100))에 맞춤
    job_name = Column(String(100), nullable=False)
    cron_expression = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class MenuPermission(Base):
    __tablename__ = "menu_permissions"

    permission_id = Column(Integer, primary_key=True, index=True)
    role = Column(Enum(UserRole), nullable=False)
    menu_path = Column(String(100), nullable=False)
    is_visible = Column(Boolean, default=True)
    
    __table_args__ = (
        Index('idx_role_menu', 'role', 'menu_path', unique=True),
    )
