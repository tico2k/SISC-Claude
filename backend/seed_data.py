from sqlalchemy.orm import Session
from sqlalchemy import func
from .core.database import SessionLocal, engine
from .core.dependencies import get_password_hash
from .core.logging_config import get_logger
from . import models
from .models import UserRole, SiemType, CaseType, CaseStatus, CasePriority, CaseResult
from datetime import datetime, timedelta
import random
from typing import Optional

logger = get_logger(__name__)

# Create tables if not exist
models.Base.metadata.create_all(bind=engine)

def clear_data(db: Optional[Session] = None):
    """
    기존 케이스 및 관련 대시보드 집계 데이터를 모두 삭제합니다.
    사용자 계정과 시스템 설정은 유지됩니다.
    """
    own_session = db is None
    session = db or SessionLocal()
    try:
        logger.info("기존 케이스 및 대시보드 데이터 초기화(삭제) 시작...")
        session.query(models.ReviewHistory).delete()
        session.query(models.ClarificationAttachment).delete()
        session.query(models.ClarificationSubmission).delete()
        session.query(models.ClarificationCase).delete()
        session.query(models.DailyStatistic).delete()
        session.query(models.WeeklyReport).delete()
        session.commit()
        logger.info("기존 케이스 및 대시보드 데이터 초기화 완료.")
    except Exception as e:
        session.rollback()
        logger.error(f"데이터 초기화 실패: {e}", exc_info=True)
        raise e
    finally:
        if own_session:
            session.close()

def sync_dashboard_metrics(session: Session, start_date: datetime, end_date: datetime):
    """
    생성된 케이스 데이터를 바탕으로 대시보드 지표(DailyStatistic 및 WeeklyReport)를 자동 계산/적재합니다.
    Swagger POST /system/seed 호출 시 대시보드 일일 추이 차트와 주간 보고서가 즉시 동기화됩니다.
    """
    logger.info("대시보드 통계 지표(DailyStatistic, WeeklyReport) 동기화 시작...")

    # 1. 일일 통계 (DailyStatistic) 생성 (최근 20일간의 각 날짜)
    cur = (end_date - timedelta(days=20)).date()
    end = end_date.date()
    
    while cur <= end:
        cur_dt_start = datetime.combine(cur, datetime.min.time())
        cur_dt_end = datetime.combine(cur, datetime.max.time())

        # 해당 일자 생성 건수별 상태 집계
        unclassified_count = session.query(func.count(models.ClarificationCase.case_id)).filter(
            models.ClarificationCase.created_at >= cur_dt_start,
            models.ClarificationCase.created_at <= cur_dt_end,
            models.ClarificationCase.case_status == CaseStatus.UNCLASSIFIED
        ).scalar() or 0

        request_count = session.query(func.count(models.ClarificationCase.case_id)).filter(
            models.ClarificationCase.created_at >= cur_dt_start,
            models.ClarificationCase.created_at <= cur_dt_end,
            models.ClarificationCase.case_status == CaseStatus.REQUEST
        ).scalar() or 0

        submit_count = session.query(func.count(models.ClarificationCase.case_id)).filter(
            models.ClarificationCase.created_at >= cur_dt_start,
            models.ClarificationCase.created_at <= cur_dt_end,
            models.ClarificationCase.case_status == CaseStatus.SUBMIT
        ).scalar() or 0

        reviewed_count = session.query(func.count(models.ClarificationCase.case_id)).filter(
            models.ClarificationCase.created_at >= cur_dt_start,
            models.ClarificationCase.created_at <= cur_dt_end,
            models.ClarificationCase.case_status.in_([CaseStatus.APPROVE, CaseStatus.REJECT, CaseStatus.CLOSE])
        ).scalar() or 0

        stat_date_val = datetime.combine(cur, datetime.min.time())
        existing_stat = session.query(models.DailyStatistic).filter(
            func.date(models.DailyStatistic.stat_date) == cur
        ).first()

        if existing_stat:
            existing_stat.unclassified_count = unclassified_count
            existing_stat.request_count = request_count
            existing_stat.submit_count = submit_count
            existing_stat.reviewed_count = reviewed_count
        else:
            new_stat = models.DailyStatistic(
                stat_date=stat_date_val,
                unclassified_count=unclassified_count,
                request_count=request_count,
                submit_count=submit_count,
                reviewed_count=reviewed_count
            )
            session.add(new_stat)

        cur += timedelta(days=1)

    # 2. 주간 보고서 (WeeklyReport) 생성 (최근 5주차)
    today = datetime.now().date()
    days_since_monday = today.weekday()
    this_monday = today - timedelta(days=days_since_monday)

    for i in range(5):
        w_start = this_monday - timedelta(weeks=i)
        w_end = w_start + timedelta(days=6)
        w_start_dt = datetime.combine(w_start, datetime.min.time())
        w_end_dt = datetime.combine(w_end, datetime.max.time())

        # 해당 주차 발생 케이스 수
        created_cnt = session.query(func.count(models.ClarificationCase.case_id)).filter(
            models.ClarificationCase.created_at >= w_start_dt,
            models.ClarificationCase.created_at <= w_end_dt
        ).scalar() or 0

        # 해당 주차 승인 케이스 수
        approved_cnt = session.query(func.count(models.ClarificationCase.case_id)).filter(
            models.ClarificationCase.created_at >= w_start_dt,
            models.ClarificationCase.created_at <= w_end_dt,
            models.ClarificationCase.case_status == CaseStatus.APPROVE
        ).scalar() or 0

        # 해당 주차 반려 케이스 수
        rejected_cnt = session.query(func.count(models.ClarificationCase.case_id)).filter(
            models.ClarificationCase.created_at >= w_start_dt,
            models.ClarificationCase.created_at <= w_end_dt,
            models.ClarificationCase.case_status == CaseStatus.REJECT
        ).scalar() or 0

        existing_report = session.query(models.WeeklyReport).filter(
            models.WeeklyReport.week_start == w_start
        ).first()

        if existing_report:
            existing_report.week_end = w_end
            existing_report.created_count = created_cnt
            existing_report.approved_count = approved_cnt
            existing_report.rejected_count = rejected_cnt
            existing_report.generated_at = datetime.now()
        else:
            new_report = models.WeeklyReport(
                week_start=w_start,
                week_end=w_end,
                created_count=created_cnt,
                approved_count=approved_cnt,
                rejected_count=rejected_cnt,
                generated_at=datetime.now()
            )
            session.add(new_report)

    session.commit()
    logger.info("대시보드 통계 지표(DailyStatistic, WeeklyReport) 동기화 완료.")

def create_single_case(session: Session, c_status: CaseStatus, c_result: Optional[CaseResult], target_user: models.User, requester: models.User, created_at: datetime, template: dict):
    """단일 케이스 및 관련 첨부파일/소명서/검토이력 레코드를 생성합니다."""
    due_date = created_at + timedelta(days=3)
    c_type = random.choice(list(CaseType))
    c_priority = random.choice(list(CasePriority))

    case = models.ClarificationCase(
        siem_type=random.choice(list(SiemType)),
        rule_title=template["title"],
        rule_description=template["desc"],
        incident_num=random.randint(10000, 99999),
        case_type=c_type,
        related_employee_id=target_user.user_id,
        requester_id=requester.user_id,
        created_at=created_at,
        due_date=due_date,
        case_status=c_status,
        priority=c_priority,
        summary=template["admin_req"] if c_status != CaseStatus.UNCLASSIFIED else "SIEM 실시간 보안 관제에서 자동 수집된 이상 징후 이벤트입니다.",
        original_log_link=f"https://siem.example.com/incidents/{random.randint(100000, 999999)}"
    )

    if c_status in [CaseStatus.APPROVE, CaseStatus.REJECT, CaseStatus.CLOSE]:
        case.case_result = c_result
        case.final_reviewer_id = requester.user_id
        case.final_review_date = created_at + timedelta(days=1, hours=random.randint(2, 6))

    session.add(case)
    session.flush()

    # 관리자 첨부파일 추가 (소명 요청, 제출, 승인, 반려 케이스)
    if c_status != CaseStatus.UNCLASSIFIED and template.get("admin_files"):
        for f_name in template["admin_files"]:
            admin_att = models.ClarificationAttachment(
                case_id=case.case_id,
                submission_id=None,
                original_filename=f_name,
                stored_filename=f"admin_{case.case_id}_{f_name}",
                file_path=f"uploads/{case.case_id}/{f_name}",
                file_size=random.randint(45000, 850000)
            )
            session.add(admin_att)

    # 사용자 소명 제출물 생성 (SUBMIT, APPROVE, REJECT 상태인 경우에만 생성!)
    if c_status in [CaseStatus.SUBMIT, CaseStatus.APPROVE, CaseStatus.REJECT]:
        sub_time = created_at + timedelta(hours=random.randint(4, 20))
        sub = models.ClarificationSubmission(
            case_id=case.case_id,
            submitter_id=target_user.user_id,
            submitted_at=sub_time,
            content=template["sub_content"],
            classification=template["sub_class"]
        )
        session.add(sub)
        session.flush()

        # 사용자 소명 첨부파일 추가
        if template.get("user_files"):
            for f_name in template["user_files"]:
                user_att = models.ClarificationAttachment(
                    case_id=case.case_id,
                    submission_id=sub.submission_id,
                    original_filename=f_name,
                    stored_filename=f"sub_{sub.submission_id}_{f_name}",
                    file_path=f"uploads/{case.case_id}/{sub.submission_id}/{f_name}",
                    file_size=random.randint(120000, 2400000)
                )
                session.add(user_att)

    # 검토 이력 생성 (APPROVE, REJECT, CLOSE)
    if c_status in [CaseStatus.APPROVE, CaseStatus.REJECT, CaseStatus.CLOSE]:
        if case.case_result == CaseResult.JUSTIFIED:
            comment = "고객사 기술지원 및 긴급 배포 목적이 객관적 증빙으로 소명되어 정당 사유로 승인 처리합니다."
        elif case.case_result == CaseResult.MINOR_VIOLATION:
            comment = "업무 연관성은 인정되나 보안 사전 승인 절차를 미준수하였습니다. 1회 경고 주의 후 승인 종결합니다."
        elif case.case_result == CaseResult.INSUFFICIENT:
            comment = "제출된 소명 내용에 부서장 사전 승인 공문이 누락되었습니다. 관련 결재 내역을 보완하여 재제출 바랍니다."
        elif case.case_result == CaseResult.EDUCATION_NEEDED:
            comment = "사내 정보보안 규정 위반이 확인되었습니다. 2026 보안 가이드라인 숙지 및 보안 준수 서약서를 필히 제출하세요."
        elif case.case_result == CaseResult.DISCIPLINARY_ACTION:
            comment = "사내 핵심 기술자료 및 대외비 문서의 외부 반출 건으로 중대 위반에 해당하여 감사팀 및 인사위원회로 공식 이관합니다."
        elif case.case_result == CaseResult.FALSE_POSITIVE:
            comment = "사내 정기 보안 점검 스크립트 실행에 의한 트래픽으로 확인되어 오탐 종결 처리합니다."
        else:
            comment = "검토 완료"

        rev = models.ReviewHistory(
            case_id=case.case_id,
            reviewer_id=requester.user_id,
            reviewed_at=case.final_review_date,
            case_status=c_status,
            case_result=case.case_result,
            comments=comment
        )
        session.add(rev)

    return case

def generate_sample_data(db: Optional[Session] = None, target_total_cases: int = 200):
    """
    현재 프로세스에 최적화된 샘플 데이터 200건 및 대시보드 통계를 생성합니다.
    특히 demo@fleitlab.com 사용자는 모든 요청/제출/승인/반려/종결 상태의 케이스를 보유하며,
    반려의 3대 세부 유형(소명 불충분, 교육 필요, 징계 요청)이 최근 14일 이내에 모두 배치됩니다.
    """
    own_session = db is None
    session = db or SessionLocal()
    try:
        logger.info(f"현재 보안 소명 프로세스 기반 샘플 데이터 생성 시작 (목표: {target_total_cases}건)...")

        # 1. 사용자 계정 생성 (demo@fleitlab.com 포함)
        users_data = [
            {"email": "system@fleitlab.com", "name": "시스템관리자", "role": UserRole.SYSTEM_ADMIN, "company": "플레잇랩", "dept": "시스템보안팀"},
            {"email": "security@fleitlab.com", "name": "보안관리자", "role": UserRole.SECURITY_ADMIN, "company": "플레잇랩", "dept": "정보보안실"},
            {"email": "audit@fleitlab.com", "name": "감사팀", "role": UserRole.AUDIT_TEAM, "company": "플레잇랩", "dept": "경영진단감사팀"},
            {"email": "demo@fleitlab.com", "name": "데모사용자", "role": UserRole.USER, "company": "플레잇랩", "dept": "보안혁신팀"},
            {"email": "user@fleitlab.com", "name": "장영미", "role": UserRole.USER, "company": "플레잇랩", "dept": "플랫폼개발1팀"},
            {"email": "user2@fleitlab.com", "name": "김민준", "role": UserRole.USER, "company": "플레잇랩", "dept": "영업마케팅팀"},
            {"email": "user3@fleitlab.com", "name": "이서연", "role": UserRole.USER, "company": "플레잇랩", "dept": "인사총무팀"},
            {"email": "user4@fleitlab.com", "name": "박지훈", "role": UserRole.USER, "company": "플레잇랩", "dept": "데이터플랫폼팀"},
            {"email": "user5@fleitlab.com", "name": "최유진", "role": UserRole.USER, "company": "플레잇랩", "dept": "클라우드인프라팀"},
            {"email": "user6@fleitlab.com", "name": "정우성", "role": UserRole.USER, "company": "플레잇랩", "dept": "재무회계팀"},
            {"email": "user7@fleitlab.com", "name": "한지민", "role": UserRole.USER, "company": "플레잇랩", "dept": "전략기획실"},
            {"email": "user8@fleitlab.com", "name": "강동원", "role": UserRole.USER, "company": "플레잇랩", "dept": "모바일개발팀"},
            {"email": "user9@fleitlab.com", "name": "송혜교", "role": UserRole.USER, "company": "플레잇랩", "dept": "디자인팀"},
            {"email": "user10@fleitlab.com", "name": "이병헌", "role": UserRole.USER, "company": "플레잇랩", "dept": "법무지원팀"},
        ]

        users = {}
        default_password_hash = get_password_hash("password123")

        for u in users_data:
            existing = session.query(models.User).filter(models.User.user_email == u["email"]).first()
            if not existing:
                new_user = models.User(
                    user_email=u["email"],
                    user_name=u["name"],
                    hashed_password=default_password_hash,
                    company=u["company"],
                    department=u["dept"],
                    role=u["role"]
                )
                session.add(new_user)
                session.flush()
                users[u["email"]] = new_user
            else:
                users[u["email"]] = existing
        
        session.commit()

        requester = users.get("security@fleitlab.com") or session.query(models.User).filter(models.User.role == UserRole.SECURITY_ADMIN).first()
        demo_user = users.get("demo@fleitlab.com") or session.query(models.User).filter(models.User.user_email == "demo@fleitlab.com").first()
        other_target_users = [u for u in session.query(models.User).filter(models.User.role == UserRole.USER).all() if u.user_email != "demo@fleitlab.com"]
        if not other_target_users:
            other_target_users = [demo_user]

        # 2. 케이스 시나리오 템플릿 풀
        templates_pool = [
            {
                "title": "대외비 설계 문서 대량 출력",
                "desc": "사내 복합기에서 신규 플랫폼 아키텍처 관련 50페이지 분량의 대외비 문서 인쇄 탐지",
                "admin_req": "대외비 인쇄 시 부서장 승인 필요 규정에 따라 출력 목적 및 사전 승인 번호를 기재 바랍니다.",
                "sub_content": "외부 고객사 현장 기술 미팅 시 보안 네트워크 연결이 불가하여 부득이 출력하였습니다. 미팅 종료 후 현장 파쇄 완료하였습니다.",
                "sub_class": "BUSINESS",
                "admin_files": ["EDR_PrintLog_Capture.csv"],
                "user_files": ["고객사_기술지원_요청서.pdf"]
            },
            {
                "title": "개인 메일(Gmail)로 소스코드 압축파일 전송",
                "desc": "DLP 에이전트 탐지: 사내 GitLab 저장소 백엔드 서비스 코드가 포함된 zip 파일 외부 전송",
                "admin_req": "사내 핵심 소스코드의 외부 이메일 전송 사유 및 수신처, 보관 목적에 대해 상세히 소명 바랍니다.",
                "sub_content": "재택근무 중 사내 VPN 연결 오류로 긴급 핫픽스 패치 검토를 위해 개인 메일로 임시 전송하였습니다. 코드 유출은 없었습니다.",
                "sub_class": "URGENT",
                "admin_files": ["DLP_Email_NetworkLog.pcap"],
                "user_files": ["VPN장애_헬프데스크_접수증.png"]
            },
            {
                "title": "비인가 퍼블릭 클라우드 스토리지(Dropbox) 업로드",
                "desc": "사내 승인되지 않은 외부 드롭박스 URL로 1.2GB 크기의 데이터셋 업로드 트래픽 발생",
                "admin_req": "대용량 데이터의 비인가 스토리지 업로드 행위가 확인되었습니다. 업로드된 파일 상세 내역과 사유를 소명하세요.",
                "sub_content": "마케팅 프로모션 홍보 영상 고화질 원본 파일로, 외주 제작사와 공유하기 위한 업무용 자료였습니다. 고객 개인정보는 포함되지 않았습니다.",
                "sub_class": "BUSINESS",
                "admin_files": ["Cloud_Traffic_Proxy_Log.csv"],
                "user_files": ["외주사_콘텐츠_제작_품의서.pdf"]
            },
            {
                "title": "비인가 미등록 USB 저장매체 연결 및 파일 복사",
                "desc": "매체제어 솔루션 탐지: 시리얼 미등록 Sandisk USB 드라이브 마운트 및 파일 이동 시도",
                "admin_req": "보안 승인되지 않은 외장 USB 연결 정황이 확인되었습니다. 반출 목적 및 보안 결재 내역을 제출하세요.",
                "sub_content": "공공기관 제출용 오프라인 서류를 담기 위해 임시 연결하였으나, 보안 경고 확인 후 즉시 분리하였습니다.",
                "sub_class": "BUSINESS",
                "admin_files": ["USB_Device_Mount_Trace.log"],
                "user_files": ["공공사업_제안서_제출_안내문.pdf"]
            },
            {
                "title": "사내 단말 불법 P2P/토렌트 프로그램 프로세스 실행",
                "desc": "호스트 보안 모니터링: utorrent.exe 프로세스 기동 및 비정상 인바운드 포트 바인딩 탐지",
                "admin_req": "사내 보안 규정상 금지된 P2P 프로그램 설치 및 실행 경위를 소명 바랍니다.",
                "sub_content": "오픈소스 AI 모델 가중치 파일(LLM weights) 공식 다운로드 링크가 토렌트 프로토콜만 지원하여 다운로드 후 즉시 삭제하였습니다.",
                "sub_class": "BUSINESS",
                "admin_files": ["Process_Execution_Detail.json"],
                "user_files": ["HuggingFace_Torrent_Download_URL.png"]
            },
            {
                "title": "심야 비업무 시간(새벽 3시) 해외 IP VPN 원격 접속",
                "desc": "SSL-VPN 접근 로그: 미국 버지니아 리전 AWS IP 대역에서 사내 내부망 인증 성공 탐지",
                "admin_req": "평소 접속하지 않는 해외 IP 대역 및 새벽 시간대 VPN 접속 경위에 대해 확인 바랍니다.",
                "sub_content": "해외 클라우드 인프라 긴급 배포 작업 중 로컬 터널링 설정으로 인해 해외 IP가 경유된 것입니다. 본인이 직접 수행한 작업입니다.",
                "sub_class": "BUSINESS",
                "admin_files": ["VPN_Auth_GeoIP_Log.csv"],
                "user_files": ["AWS_긴급배포_승인_Slack대화캡처.png"]
            },
            {
                "title": "운영 데이터베이스(DB) 고객 개인정보 대량 쿼리 실행",
                "desc": "DB 접근제어 탐지: 회원 테이블 SELECT * LIMIT 100,000 실행 및 마스킹 해제 조회",
                "admin_req": "개인정보보호법에 의거하여 대량 개인정보 조회 목적 및 CPO 사전 승인 내역을 소명하세요.",
                "sub_content": "연말 정산 소득공제 영수증 발행 배치 처리를 위한 사전 데이터 정합성 검증 쿼리였습니다. CPO 사전 승인 결재 문서를 첨부합니다.",
                "sub_class": "BUSINESS",
                "admin_files": ["DB_Query_Audit_Trace.sql"],
                "user_files": ["CPO_대량개인정보조회_승인결재.pdf"]
            },
            {
                "title": "단기간 내 반복적인 비밀번호 오입력 (Brute-Force 의심)",
                "desc": "통합 인증 서버 탐지: 동일 계정에 대해 10분 내 20회 연속 비밀번호 인증 실패",
                "admin_req": "비밀번호 반복 오류 발생 원인 및 타인에 의한 계정 탈취 시도 여부를 확인하세요.",
                "sub_content": "PC 패스워드 변경 후 모바일 메일 클라이언트의 자동 로그인 정보가 갱신되지 않아 백그라운드 재시도가 누적된 것으로 파악되었습니다.",
                "sub_class": "FALSE_POSITIVE",
                "admin_files": ["IAM_Failed_Logins.csv"],
                "user_files": ["스마트폰_비밀번호_재설정_확인화면.png"]
            },
            {
                "title": "퇴사 예정자 계정의 관리자 권한 상승(sudo) 시도",
                "desc": "서버 감사 로그: 퇴사 예정 직원의 계정으로 리눅스 root 권한 상승 명령어 다수 실행",
                "admin_req": "인수인계 기간 중 시스템 관리자 권한 상승 시도 목적 및 작업 내용을 소명 바랍니다.",
                "sub_content": "후임자에게 인수인계하기 위해 시스템 환경 설정 및 데몬 설정 파일을 백업하는 과정에서 sudo 명령어를 사용하였습니다.",
                "sub_class": "BUSINESS",
                "admin_files": ["Linux_Audit_Sudo_Log.txt"],
                "user_files": ["업무인수인계_점검표.pdf"]
            }
        ]

        # 3. [핵심] demo@fleitlab.com 전용 케이스 생성 (최근 14일 이내 완벽 배치)
        # 나의 소명 관리 기본 필터(최근 14일)에서 모든 탭에 숫자가 풍성하게 뜨도록 보장:
        # - 요청: 4건
        # - 제출: 4건
        # - 승인: 4건 (정당 사유 2건, 경미한 위반 2건)
        # - 반려: 6건 (소명 불충분 2건, 교육 필요 2건, 징계 요청 2건 - 프로세스 3종 모두 포함!)
        # - 종결: 2건 (오탐 2건)
        # 총 20건
        demo_plan = [
            (CaseStatus.REQUEST, None),
            (CaseStatus.REQUEST, None),
            (CaseStatus.REQUEST, None),
            (CaseStatus.REQUEST, None),
            (CaseStatus.SUBMIT, None),
            (CaseStatus.SUBMIT, None),
            (CaseStatus.SUBMIT, None),
            (CaseStatus.SUBMIT, None),
            (CaseStatus.APPROVE, CaseResult.JUSTIFIED),
            (CaseStatus.APPROVE, CaseResult.JUSTIFIED),
            (CaseStatus.APPROVE, CaseResult.MINOR_VIOLATION),
            (CaseStatus.APPROVE, CaseResult.MINOR_VIOLATION),
            (CaseStatus.REJECT, CaseResult.INSUFFICIENT),      # 방안 A: 보완 재소명
            (CaseStatus.REJECT, CaseResult.INSUFFICIENT),      # 방안 A: 보완 재소명
            (CaseStatus.REJECT, CaseResult.EDUCATION_NEEDED),   # 방안 B: 교육 및 서약
            (CaseStatus.REJECT, CaseResult.EDUCATION_NEEDED),   # 방안 B: 교육 및 서약
            (CaseStatus.REJECT, CaseResult.DISCIPLINARY_ACTION), # 방안 C: 징계 및 감사 이관
            (CaseStatus.REJECT, CaseResult.DISCIPLINARY_ACTION), # 방안 C: 징계 및 감사 이관
            (CaseStatus.CLOSE, CaseResult.FALSE_POSITIVE),
            (CaseStatus.CLOSE, CaseResult.FALSE_POSITIVE),
        ]

        now = datetime.now()
        total_created = 0

        logger.info(f"demo@fleitlab.com 전용 케이스 {len(demo_plan)}건 생성 시작...")
        for idx, (st, res) in enumerate(demo_plan):
            # 최근 1~12일 전으로 골고루 분산
            days_ago = (idx % 11) + 1
            case_time = (now - timedelta(days=days_ago)).replace(hour=random.randint(9, 17), minute=random.randint(0, 59), second=0)
            tpl = templates_pool[idx % len(templates_pool)]
            create_single_case(session, st, res, demo_user, requester, case_time, tpl)
            total_created += 1

        # 4. 나머지 케이스 (target_total_cases - len(demo_plan) = 180건)를 타 직원들에게 분배
        remaining_count = target_total_cases - total_created
        logger.info(f"일반 케이스 {remaining_count}건 생성 시작 (최근 35일 분산)...")

        # 180건 상태 플랜:
        # - SUBMIT: 46건
        # - REQUEST: 36건
        # - APPROVE: 36건 (정당사유 23, 경미한위반 13)
        # - REJECT: 24건 (세부 3종 각 8건씩)
        # - UNCLASSIFIED: 30건 (관리자 스크리닝 대기)
        # - CLOSE: 8건
        other_plan = []
        other_plan += [(CaseStatus.SUBMIT, None)] * 46
        other_plan += [(CaseStatus.REQUEST, None)] * 36
        other_plan += [(CaseStatus.APPROVE, CaseResult.JUSTIFIED)] * 23
        other_plan += [(CaseStatus.APPROVE, CaseResult.MINOR_VIOLATION)] * 13
        other_plan += [(CaseStatus.REJECT, CaseResult.INSUFFICIENT)] * 8
        other_plan += [(CaseStatus.REJECT, CaseResult.EDUCATION_NEEDED)] * 8
        other_plan += [(CaseStatus.REJECT, CaseResult.DISCIPLINARY_ACTION)] * 8
        other_plan += [(CaseStatus.UNCLASSIFIED, None)] * 30
        other_plan += [(CaseStatus.CLOSE, CaseResult.FALSE_POSITIVE)] * 8

        # 수량 보정
        if len(other_plan) < remaining_count:
            other_plan += [(CaseStatus.SUBMIT, None)] * (remaining_count - len(other_plan))
        elif len(other_plan) > remaining_count:
            other_plan = other_plan[:remaining_count]

        random.shuffle(other_plan)

        # 최근 35일간 분산
        total_days = 35
        start_date = now - timedelta(days=total_days)
        base_per_day = remaining_count // total_days
        remainder = remaining_count % total_days
        counts_per_day = [base_per_day + (1 if i < remainder else 0) for i in range(total_days)]
        random.shuffle(counts_per_day)

        case_idx = 0
        for day_offset, daily_count in enumerate(counts_per_day):
            current_date = start_date + timedelta(days=day_offset)

            for _ in range(daily_count):
                if case_idx >= len(other_plan):
                    break

                st, res = other_plan[case_idx]
                case_idx += 1

                target_u = random.choice(other_target_users)
                tpl = random.choice(templates_pool)

                created_hour = random.randint(8, 18)
                created_minute = random.randint(0, 59)
                case_time = current_date.replace(hour=created_hour, minute=created_minute, second=0)

                create_single_case(session, st, res, target_u, requester, case_time, tpl)
                total_created += 1

        session.commit()

        # 5. 대시보드 통계 지표(DailyStatistic 및 WeeklyReport) 즉시 연동 계산 및 적재
        sync_dashboard_metrics(session, start_date, now)

        logger.info(f"샘플 데이터 생성 및 대시보드 동기화 완료 (총 {total_created}건 생성, demo@fleitlab.com 전용 케이스 20건 포함)")
        return total_created

    except Exception as e:
        session.rollback()
        logger.error(f"샘플 데이터 생성 실패: {e}", exc_info=True)
        raise e
    finally:
        if own_session:
            session.close()

if __name__ == "__main__":
    clear_data()
    generate_sample_data(target_total_cases=200)
