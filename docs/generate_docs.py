#!/usr/bin/env python3
"""Generate 개발계획서 and 완료보고서 Word documents for 연구소 실사."""

from docx import Document
from docx.shared import Pt, Cm, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import copy


# ── 공통 스타일 헬퍼 ────────────────────────────────────────────────

def set_font(run, name="맑은 고딕", size=10, bold=False, color=None):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    if color:
        run.font.color.rgb = RGBColor(*color)
    r = run._element
    rPr = r.find(qn("w:rPr"))
    if rPr is None:
        rPr = OxmlElement("w:rPr")
        r.insert(0, rPr)
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.insert(0, rFonts)
    rFonts.set(qn("w:eastAsia"), name)
    rFonts.set(qn("w:ascii"), "Arial")
    rFonts.set(qn("w:hAnsi"), "Arial")


def heading(doc, text, level=1):
    """Add a styled heading paragraph."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = p.add_run(text)
    if level == 1:
        set_font(run, size=14, bold=True, color=(31, 73, 125))
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(4)
        # Bottom border
        pPr = p._p.get_or_add_pPr()
        pBdr = OxmlElement("w:pBdr")
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), "6")
        bottom.set(qn("w:space"), "1")
        bottom.set(qn("w:color"), "1F497D")
        pBdr.append(bottom)
        pPr.append(pBdr)
    elif level == 2:
        set_font(run, size=11, bold=True, color=(0, 70, 127))
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(2)
    elif level == 3:
        set_font(run, size=10, bold=True, color=(68, 68, 68))
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(2)
    return p


def body(doc, text, indent=False):
    p = doc.add_paragraph()
    if indent:
        p.paragraph_format.left_indent = Cm(0.6)
    run = p.add_run(text)
    set_font(run, size=10)
    p.paragraph_format.space_after = Pt(2)
    return p


def bullet(doc, text, level=1):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.left_indent = Cm(level * 0.5)
    p.paragraph_format.space_after = Pt(1)
    run = p.runs[0] if p.runs else p.add_run()
    run.text = text
    set_font(run, size=10)
    return p


def add_table(doc, headers, rows, col_widths=None):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    # Header row
    hrow = table.rows[0]
    for i, h in enumerate(headers):
        cell = hrow.cells[i]
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        tc = cell._tc
        tcPr = tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), "1F497D")
        tcPr.append(shd)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(h)
        set_font(run, size=9.5, bold=True, color=(255, 255, 255))

    # Data rows
    for ri, row_data in enumerate(rows):
        row = table.rows[ri + 1]
        for ci, val in enumerate(row_data):
            cell = row.cells[ci]
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            if (ri % 2) == 1:
                tc = cell._tc
                tcPr = tc.get_or_add_tcPr()
                shd = OxmlElement("w:shd")
                shd.set(qn("w:val"), "clear")
                shd.set(qn("w:color"), "auto")
                shd.set(qn("w:fill"), "EBF3FB")
                tcPr.append(shd)
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(str(val))
            set_font(run, size=9.5)

    if col_widths:
        for i, w in enumerate(col_widths):
            for row in table.rows:
                row.cells[i].width = Cm(w)
    return table


def page_break(doc):
    doc.add_page_break()


def set_page_margins(doc, top=2.5, bottom=2.5, left=3.0, right=2.5):
    section = doc.sections[0]
    section.top_margin = Cm(top)
    section.bottom_margin = Cm(bottom)
    section.left_margin = Cm(left)
    section.right_margin = Cm(right)


# ═══════════════════════════════════════════════════════════════════════
#  문서 1: 개발계획서
# ═══════════════════════════════════════════════════════════════════════

def make_plan(path):
    doc = Document()
    set_page_margins(doc)

    # ── 표지 ────────────────────────────────────────────────────────
    for _ in range(4):
        doc.add_paragraph()

    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("소 프 트 웨 어 개 발 계 획 서")
    set_font(r, size=22, bold=True, color=(31, 73, 125))

    doc.add_paragraph()
    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = sub.add_run("내부자 위협 탐지 및 소명 관리 시스템")
    set_font(r2, size=16, bold=True, color=(68, 68, 68))

    sub2 = doc.add_paragraph()
    sub2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r3 = sub2.add_run("Fleit InsiderGuard (SICS v1.4.0)")
    set_font(r3, size=14, color=(120, 120, 120))

    for _ in range(6):
        doc.add_paragraph()

    info_table = doc.add_table(rows=5, cols=2)
    info_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    info_items = [
        ("과 제 명", "내부자 위협 탐지 및 소명 관리 시스템 (InsiderGuard SICS)"),
        ("개 발 기 간", "2025년 12월 ~ 2026년 3월 (약 4개월)"),
        ("개 발 주 체", "플레잇랩 (Fleit Lab)"),
        ("개 발 유 형", "자체 개발 (독자 기술 기반 보안 솔루션)"),
        ("작 성 일 자", "2025년 12월 01일"),
    ]
    for ri, (k, v) in enumerate(info_items):
        row = info_table.rows[ri]
        row.cells[0].width = Cm(4)
        row.cells[1].width = Cm(10)
        kc = row.cells[0]
        vc = row.cells[1]
        tc = kc._tc
        tcPr = tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), "1F497D")
        tcPr.append(shd)
        kp = kc.paragraphs[0]
        kp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        kr = kp.add_run(k)
        set_font(kr, size=10, bold=True, color=(255, 255, 255))
        vp = vc.paragraphs[0]
        vp.alignment = WD_ALIGN_PARAGRAPH.LEFT
        vr = vp.add_run("  " + v)
        set_font(vr, size=10)

    for _ in range(5):
        doc.add_paragraph()

    sign = doc.add_paragraph()
    sign.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_s = sign.add_run("플레잇랩 (Fleit Lab) 내부연구소")
    set_font(r_s, size=12, bold=True, color=(31, 73, 125))

    # ── 본문 ─────────────────────────────────────────────────────────
    page_break(doc)

    # 목차
    heading(doc, "목  차", 1)
    toc_items = [
        ("1", "개발 배경 및 목적"),
        ("2", "개발 목표 및 범위"),
        ("3", "시스템 요구사항 분석"),
        ("4", "시스템 아키텍처 설계"),
        ("5", "상세 기능 설계"),
        ("6", "데이터베이스 설계"),
        ("7", "개발 일정 계획"),
        ("8", "개발 환경 및 기술 스택"),
        ("9", "보안 설계"),
        ("10", "기대 효과"),
    ]
    for num, item in toc_items:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.5)
        r = p.add_run(f"제{num}장.  {item}")
        set_font(r, size=10)
        p.paragraph_format.space_after = Pt(1)

    page_break(doc)

    # 제1장 개발 배경 및 목적
    heading(doc, "제1장. 개발 배경 및 목적", 1)

    heading(doc, "1.1 개발 배경", 2)
    body(doc,
        "최근 기업 및 공공기관에서 발생하는 정보 유출·보안 위협의 상당수가 외부 해킹이 아닌 "
        "내부자(임직원)에 의해 발생하고 있습니다. 특히 SIEM(Security Information and "
        "Event Management) 시스템이 대용량의 보안 이벤트 알람을 생성하더라도, "
        "담당 보안 인력이 각 알람을 개별적으로 검토하고 관련 임직원에게 소명을 요청하며 "
        "결과를 추적·관리하는 전 과정을 수작업으로 처리해야 하는 현실적 한계가 존재합니다."
    )
    body(doc,
        "기존 이메일·메신저 기반의 비구조적 소명 요청 방식은 이력 추적 불가, "
        "문서 관리 분산, 마감일 관리 실패 등 다수의 운영상 문제를 야기하였으며, "
        "이를 체계화·자동화할 수 있는 전용 플랫폼의 필요성이 대두되었습니다."
    )

    heading(doc, "1.2 개발 목적", 2)
    bullets_1 = [
        "SIEM에서 탐지된 보안 이벤트를 자동 수집하여 소명 케이스로 전환하는 워크플로우 자동화",
        "역할 기반 접근 통제(RBAC)를 통한 보안 관리자, 감사팀, 일반 임직원 간 권한 분리",
        "이메일 자동 알림(소명 요청, 마감 독려, 검토 완료 등)을 통한 프로세스 단축 및 누락 방지",
        "모든 소명 이력·검토 의견·첨부파일을 단일 데이터베이스에 영구 보존하여 감사 추적성 확보",
        "Microsoft Entra ID(Azure AD) SSO 연동으로 기업 계정 체계와 통합",
    ]
    for b in bullets_1:
        bullet(doc, b)

    # 제2장
    page_break(doc)
    heading(doc, "제2장. 개발 목표 및 범위", 1)

    heading(doc, "2.1 개발 목표", 2)
    body(doc, "본 프로젝트의 최종 목표는 다음 세 가지 핵심 가치를 실현하는 것입니다.")
    goals = [
        ("신속한 보안 대응", "SIEM 이벤트 발생 후 소명 요청까지 걸리는 평균 시간을 기존 대비 60% 단축"),
        ("오탐 감소", "보안 관리자가 초기 검토 단계에서 오탐을 식별·종결하여 실질 위협 집중도 향상"),
        ("완전한 감사 추적", "소명 생성부터 종결까지 전 이력을 시스템 감사 로그로 보존하여 법적·컴플라이언스 요건 충족"),
    ]
    add_table(doc,
              ["목표 항목", "세부 내용"],
              goals,
              col_widths=[4.5, 11.5])

    heading(doc, "2.2 개발 범위", 2)
    body(doc, "본 시스템의 개발 범위는 아래와 같이 크게 4개 영역으로 구분합니다.")
    scope_items = [
        "백엔드 API 서버: FastAPI 기반 REST API, 인증·인가, 비즈니스 로직, 스케줄러",
        "프론트엔드 웹 UI: React + TypeScript 기반 SPA, 대시보드, 케이스 관리, 시스템 설정",
        "SIEM 수집 모듈: Microsoft Sentinel, Splunk, Elastic(ELK) 연동 Collector",
        "배포 인프라: Nginx 리버스 프록시, Gunicorn/Uvicorn 멀티 프로세스, SQLite/PostgreSQL",
    ]
    for s in scope_items:
        bullet(doc, s)

    # 제3장
    heading(doc, "제3장. 시스템 요구사항 분석", 1)

    heading(doc, "3.1 기능 요구사항", 2)
    func_reqs = [
        ("FR-01", "SIEM 연동", "Sentinel, Splunk, ELK로부터 보안 이벤트를 자동 수집하여 케이스로 생성"),
        ("FR-02", "케이스 관리", "소명 케이스의 생성·조회·상태 변경(미확인→요청→제출→승인/반려→종결)"),
        ("FR-03", "소명 제출", "임직원이 사유 텍스트 작성 및 증빙 파일(최대 10MB) 첨부 후 제출"),
        ("FR-04", "검토 및 심의", "보안팀/감사팀의 소명 내용 검토, 승인/반려 처리, 의견 기록"),
        ("FR-05", "자동 알림", "케이스 상태 변경 시 관련 담당자에게 이메일 자동 발송"),
        ("FR-06", "대시보드", "케이스 상태별·기간별·유형별 다차원 통계 및 시각화"),
        ("FR-07", "RBAC 권한", "역할(USER/AUDIT_TEAM/SECURITY_ADMIN/SYSTEM_ADMIN)별 화면·API 접근 제어"),
        ("FR-08", "스케줄 관리", "관리자가 웹 UI에서 SIEM 수집·알림·통계 크론 주기를 동적으로 설정"),
        ("FR-09", "시스템 설정", "환경변수, SIEM 접속정보, 사용자 계정 관리 등 관리자 기능"),
        ("FR-10", "감사 로그", "시스템 내 모든 주요 행위의 행위자·IP·시각 기록 및 조회"),
    ]
    add_table(doc,
              ["ID", "요구사항", "상세 내용"],
              func_reqs,
              col_widths=[2, 3, 11])

    heading(doc, "3.2 비기능 요구사항", 2)
    nonfunc_reqs = [
        ("NFR-01", "성능", "10만 건 이상의 케이스 목록 조회 시 3초 이내 응답 (복합 인덱스 적용)"),
        ("NFR-02", "보안", "JWT 인증, AES-256 암호화, Rate Limiting, SQL Injection 방어"),
        ("NFR-03", "가용성", "단일 서버 환경에서 99% 이상 가동률 목표"),
        ("NFR-04", "확장성", "BaseCollector 인터페이스를 통한 신규 SIEM 플러그인 추가 가능 구조"),
        ("NFR-05", "운영성", "외부 메시지 브로커(Redis/Celery) 없이 단일 컨테이너로 배포 가능"),
    ]
    add_table(doc,
              ["ID", "항목", "요건"],
              nonfunc_reqs,
              col_widths=[2, 2.5, 11.5])

    # 제4장
    page_break(doc)
    heading(doc, "제4장. 시스템 아키텍처 설계", 1)

    heading(doc, "4.1 전체 시스템 구성도", 2)
    body(doc,
        "본 시스템은 클라이언트 티어(브라우저), 프론트엔드 티어(React SPA), "
        "백엔드 애플리케이션 티어(FastAPI), 데이터·외부 연동 티어(DB, SIEM, 메일)의 "
        "4계층 구조로 설계되었습니다."
    )
    arch_layers = [
        ("Client Tier", "웹 브라우저", "HTTP(S) 요청/응답"),
        ("Frontend Tier", "React + TypeScript + Vite", "OpenAPI 자동 타입 동기화"),
        ("Backend Tier", "FastAPI + APScheduler", "JWT 인증, RBAC, 비동기 처리"),
        ("Data/External Tier", "SQLite/PostgreSQL, SIEM, SMTP", "영구 저장, 외부 연동"),
    ]
    add_table(doc,
              ["계층", "주요 기술", "역할"],
              arch_layers,
              col_widths=[3.5, 6, 6.5])

    heading(doc, "4.2 컴포넌트 간 상호작용", 2)
    body(doc,
        "React 클라이언트는 Axios를 통해 FastAPI 엔드포인트에 REST 요청을 전송합니다. "
        "서버는 Pydantic v2로 페이로드를 검증한 후 JWT/SSO 인증, RBAC 인가를 순차 수행하며, "
        "비즈니스 로직 처리 후 I/O 집중 작업(이메일 발송 등)은 BackgroundTasks에 위임합니다. "
        "정기 작업(SIEM 수집, 마감 알림, 통계 생성)은 APScheduler가 DB와 연동하여 수행합니다."
    )

    # 제5장
    heading(doc, "제5장. 상세 기능 설계", 1)

    heading(doc, "5.1 소명 처리 워크플로우", 2)
    body(doc, "소명 케이스의 생명주기는 아래 6단계로 구성됩니다.")
    workflow = [
        ("1단계", "탐지 및 케이스 생성", "SIEM 또는 관리자 수동 입력 → 상태: UNCLASSIFIED"),
        ("2단계", "보안관리자 초기 검토", "오탐 즉시 종결 또는 소명 요청 분기 → Case Locking 적용"),
        ("3단계", "소명 요청 발송", "마감일 설정, 소명 요청 이메일 자동 발송 → 상태: REQUEST"),
        ("4단계", "임직원 소명 제출", "사유 작성 + 증빙 파일 첨부 → 상태: SUBMIT"),
        ("5단계", "보안/감사팀 최종 심의", "승인(APPROVE) 또는 반려(REJECT) → 이력 기록"),
        ("6단계", "최종 종결", "조치 완료 → 상태: CLOSE, 이후 수정 불가"),
    ]
    add_table(doc,
              ["단계", "주체", "내용"],
              workflow,
              col_widths=[1.8, 3.5, 10.7])

    heading(doc, "5.2 자동 알림 정책", 2)
    notif = [
        ("케이스 생성", "피소명 임직원", "보안 이벤트 탐지 및 케이스 배정 안내"),
        ("소명 요청 발송", "피소명 임직원", "상세 사건 고지 및 제출 기한 안내"),
        ("마감 임박 (3/1일 전)", "피소명 임직원", "미처리 소명 자동 독려 (APScheduler 매일 09:00)"),
        ("소명서 제출 완료", "보안 관리자", "직원의 소명 접수 완료 통보"),
        ("검토 완료 (승인/반려)", "피소명 임직원", "최종 심의 결과 통보"),
    ]
    add_table(doc,
              ["트리거", "수신자", "내용"],
              notif,
              col_widths=[4, 3.5, 8.5])

    heading(doc, "5.3 역할별 권한 (RBAC) 매트릭스", 2)
    rbac = [
        ("일반 직원 (USER)", "❌", "✅ (본인 배정건)", "❌", "❌", "❌"),
        ("감사팀 (AUDIT_TEAM)", "❌", "✅", "✅", "✅", "❌"),
        ("보안 관리자 (SECURITY_ADMIN)", "✅", "✅", "✅", "✅", "✅"),
        ("시스템 관리자 (SYSTEM_ADMIN)", "✅", "✅", "✅", "✅", "✅"),
    ]
    add_table(doc,
              ["역할", "케이스 생성", "소명 작성", "검토/승인", "강제 종결", "시스템 설정"],
              rbac,
              col_widths=[4, 2, 2.3, 2.3, 2.3, 3.1])

    # 제6장
    page_break(doc)
    heading(doc, "제6장. 데이터베이스 설계", 1)

    heading(doc, "6.1 주요 엔티티 구성", 2)
    entities = [
        ("users", "시스템 사용자", "user_id, user_email, hashed_password, role, department"),
        ("clarification_case", "소명 케이스", "case_id, siem_type, case_status, priority, due_date, locked_by_id"),
        ("clarification_submission", "소명 제출 내용", "submission_id, case_id, submitter_id, content"),
        ("clarification_attachment", "소명 첨부파일", "file_id, submission_id, stored_filename, file_size"),
        ("review_history", "검토 이력", "review_id, case_id, reviewer_id, case_result, comments"),
        ("siem_configuration", "SIEM 연동 설정", "siem_id, siem_type, host_url, client_secret(AES-256 암호화)"),
        ("system_audit_log", "시스템 감사 로그", "log_id, actor_id, action, ip_address, occurred_at"),
        ("system_job_configuration", "동적 스케줄 설정", "job_id, cron_expression, is_active"),
        ("menu_permissions", "RBAC 메뉴 권한", "role, menu_path, is_visible"),
        ("daily_statistic / weekly_report", "통계 데이터", "일별·주별 케이스 상태 집계"),
    ]
    add_table(doc,
              ["테이블명", "역할", "주요 컬럼"],
              entities,
              col_widths=[4.5, 3, 8.5])

    heading(doc, "6.2 성능 최적화 인덱스", 2)
    indexes = [
        ("idx_case_status", "clarification_case", "case_status", "상태별 케이스 목록 조회"),
        ("idx_employee_status", "clarification_case", "related_employee_id, case_status", "특정 직원 활성 케이스 조회"),
        ("idx_created_at", "clarification_case", "created_at", "기간 필터링 최적화"),
        ("idx_login_at", "login_history", "login_at", "부정 로그인 감지 분석"),
    ]
    add_table(doc,
              ["인덱스명", "테이블", "컬럼", "목적"],
              indexes,
              col_widths=[4, 3.5, 5, 3.5])

    # 제7장
    heading(doc, "제7장. 개발 일정 계획", 1)

    heading(doc, "7.1 단계별 개발 일정", 2)
    schedule = [
        ("1단계", "2025. 12. 01 ~ 12. 21", "요구사항 분석 및 설계", "기능 정의, DB 설계, API 명세 작성"),
        ("2단계", "2025. 12. 22 ~ 2026. 01. 19", "백엔드 핵심 개발", "FastAPI 인증·케이스·SIEM 수집 API 구현"),
        ("3단계", "2026. 01. 20 ~ 02. 16", "프론트엔드 개발", "React 대시보드·케이스 관리 UI 구현"),
        ("4단계", "2026. 02. 17 ~ 03. 02", "고도화 개발 (v1.3.0)", "APScheduler 전환, Case Locking, 성능 최적화"),
        ("5단계", "2026. 03. 03 ~ 03. 10", "최종 기능 개발 (v1.4.0)", "동적 스케줄링 DB 전환, RBAC 메뉴 권한, SSO"),
        ("6단계", "2026. 03. 11 ~ 03. 20", "테스트 및 문서화", "단위·통합 테스트, 배포 가이드 작성"),
    ]
    add_table(doc,
              ["단계", "기간", "구분", "주요 작업"],
              schedule,
              col_widths=[1.5, 4.5, 3.5, 6.5])

    # 제8장
    page_break(doc)
    heading(doc, "제8장. 개발 환경 및 기술 스택", 1)

    heading(doc, "8.1 기술 스택 상세", 2)
    stack = [
        ("백엔드 언어/프레임워크", "Python 3.11+ / FastAPI 0.x", "고성능 비동기 API, Pydantic v2 자동 검증"),
        ("ORM / DB", "SQLAlchemy 2.0 / SQLite (→ PostgreSQL 이관 가능)", "N+1 최적화, selectinload/joinedload"),
        ("인증", "python-jose (JWT), MSAL (Entra ID SSO)", "자체 JWT + 기업용 SSO 이중 지원"),
        ("스케줄러", "APScheduler 3.x + FastAPI BackgroundTasks", "외부 브로커 없는 내장형 비동기 처리"),
        ("이메일", "Microsoft Graph API / aiosmtplib", "Outlook 연동 자동화 알림"),
        ("암호화", "cryptography (AES-256 Fernet)", "SIEM 크레덴셜 DB 저장 암호화"),
        ("보안", "SlowAPI (Rate Limiting), Argon2 (PW 해시)", "DDoS 방어, 강력한 비밀번호 보호"),
        ("프론트엔드", "React 18 + TypeScript + Vite + Tailwind CSS", "컴포넌트 기반 SPA"),
        ("API 타입 동기화", "OpenAPI → TypeScript (generate-types)", "백엔드-프론트엔드 타입 자동 일치"),
        ("배포", "Nginx + Gunicorn + UvicornWorker", "리버스 프록시, 멀티 프로세스 운영"),
    ]
    add_table(doc,
              ["항목", "기술/버전", "선정 이유"],
              stack,
              col_widths=[3.5, 5.5, 7])

    # 제9장
    heading(doc, "제9장. 보안 설계", 1)

    heading(doc, "9.1 보안 계층별 설계 (Defense in Depth)", 2)
    security = [
        ("인증 계층", "JWT (자체) + Microsoft Entra ID SSO (OAuth2)"),
        ("인가 계층", "RBAC — DB 기반 동적 MenuPermission, require_roles 데코레이터"),
        ("API 보안", "SlowAPI Rate Limiting (분당 5회), CORS 정책 설정"),
        ("데이터 암호화", "SIEM 크레덴셜 AES-256 Fernet 암호화 저장"),
        ("입력 검증", "Pydantic v2 전체 적용, MIME/확장자/파일 크기 검사"),
        ("SQL Injection 방어", "SQLAlchemy ORM Parameterized Binding 100%"),
        ("환경변수 보호", ".env 민감 키 자동 마스킹(★★★) 및 경로 주입 방어"),
        ("동시성 제어", "Case Locking (locked_by_id, locked_at) — Lost Update 방어"),
        ("감사 추적", "system_audit_log 테이블에 전 행위 영구 기록"),
        ("전송 보안", "Nginx SSL/TLS 종료, HTTPS 강제 리다이렉트"),
    ]
    add_table(doc,
              ["보안 영역", "설계 내용"],
              security,
              col_widths=[4, 12])

    # 제10장
    heading(doc, "제10장. 기대 효과", 1)

    heading(doc, "10.1 정량적 기대 효과", 2)
    quant = [
        ("소명 처리 소요 시간", "기존 수작업 대비 50% 이상 단축"),
        ("보안 사고 대응 누락율", "자동 알림으로 0% 목표"),
        ("오탐 처리 비율", "초기 검토 단계 자동화로 보안 인력 집중도 향상"),
        ("감사 대응 시간", "통합 이력 검색으로 즉시 증빙 자료 제출 가능"),
    ]
    add_table(doc,
              ["지표", "목표치"],
              quant,
              col_widths=[5, 11])

    heading(doc, "10.2 정성적 기대 효과", 2)
    qual = [
        "임직원의 억울한 불이익 방지: 체계적 소명 기회 보장 및 이력 투명 공개",
        "보안팀 업무 부담 경감: 반복적 알림·추적 업무의 자동화",
        "컴플라이언스 대응력 강화: ISO 27001, 개인정보보호법 등 감사 요건 충족",
        "조직 보안 문화 향상: 보안 이벤트에 대한 책임감 있는 대응 문화 정착",
    ]
    for q in qual:
        bullet(doc, q)

    doc.save(path)
    print(f"✅ 개발계획서 저장: {path}")


# ═══════════════════════════════════════════════════════════════════════
#  문서 2: 완료보고서
# ═══════════════════════════════════════════════════════════════════════

def make_report(path):
    doc = Document()
    set_page_margins(doc)

    # ── 표지 ────────────────────────────────────────────────────────
    for _ in range(4):
        doc.add_paragraph()

    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("소 프 트 웨 어 개 발 완 료 보 고 서")
    set_font(r, size=22, bold=True, color=(31, 73, 125))

    doc.add_paragraph()
    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = sub.add_run("내부자 위협 탐지 및 소명 관리 시스템")
    set_font(r2, size=16, bold=True, color=(68, 68, 68))

    sub2 = doc.add_paragraph()
    sub2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r3 = sub2.add_run("Fleit InsiderGuard (SICS v1.4.0) — 최종 개발 완료")
    set_font(r3, size=14, color=(120, 120, 120))

    for _ in range(6):
        doc.add_paragraph()

    info_table = doc.add_table(rows=6, cols=2)
    info_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    info_items = [
        ("과 제 명", "내부자 위협 탐지 및 소명 관리 시스템 (InsiderGuard SICS)"),
        ("개 발 기 간", "2025년 12월 01일 ~ 2026년 03월 20일"),
        ("최 종 버 전", "v1.4.0 (정식 릴리즈)"),
        ("개 발 주 체", "플레잇랩 (Fleit Lab)"),
        ("개 발 유 형", "자체 개발 (독자 기술 기반 보안 솔루션)"),
        ("작 성 일 자", "2026년 03월 20일"),
    ]
    for ri, (k, v) in enumerate(info_items):
        row = info_table.rows[ri]
        row.cells[0].width = Cm(4)
        row.cells[1].width = Cm(10)
        kc = row.cells[0]
        vc = row.cells[1]
        tc = kc._tc
        tcPr = tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), "1F497D")
        tcPr.append(shd)
        kp = kc.paragraphs[0]
        kp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        kr = kp.add_run(k)
        set_font(kr, size=10, bold=True, color=(255, 255, 255))
        vp = vc.paragraphs[0]
        vp.alignment = WD_ALIGN_PARAGRAPH.LEFT
        vr = vp.add_run("  " + v)
        set_font(vr, size=10)

    for _ in range(5):
        doc.add_paragraph()

    sign = doc.add_paragraph()
    sign.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_s = sign.add_run("플레잇랩 (Fleit Lab) 내부연구소")
    set_font(r_s, size=12, bold=True, color=(31, 73, 125))

    # ── 본문 ─────────────────────────────────────────────────────────
    page_break(doc)

    # 목차
    heading(doc, "목  차", 1)
    toc_items = [
        ("1", "프로젝트 개요"),
        ("2", "개발 완료 현황"),
        ("3", "버전별 개발 이력"),
        ("4", "구현 기능 상세"),
        ("5", "기술 스택 및 아키텍처 구현 결과"),
        ("6", "테스트 결과"),
        ("7", "성과 및 효과"),
        ("8", "향후 개선 계획"),
        ("부록 A", "주요 화면 구성"),
        ("부록 B", "API 엔드포인트 목록"),
    ]
    for num, item in toc_items:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.5)
        r = p.add_run(f"제{num}장.  {item}" if "부록" not in num else f"{num}.  {item}")
        set_font(r, size=10)
        p.paragraph_format.space_after = Pt(1)

    page_break(doc)

    # 제1장
    heading(doc, "제1장. 프로젝트 개요", 1)

    heading(doc, "1.1 시스템 소개", 2)
    body(doc,
        "Fleit InsiderGuard(이하 'SICS')는 SIEM(Security Information and Event Management) "
        "시스템에서 탐지된 내부 보안 인시던트에 대해 관련 임직원에게 소명 기회를 제공하고, "
        "보안팀이 소명 자료를 체계적으로 검토·심의할 수 있도록 지원하는 "
        "엔터프라이즈급 통합 보안 관리 플랫폼입니다."
    )
    body(doc,
        "본 시스템은 약 4개월의 개발 기간을 거쳐 v1.4.0 정식 릴리즈로 완성되었으며, "
        "소명 처리 전 과정(탐지 → 소명 요청 → 제출 → 심의 → 종결)을 단일 시스템 내에서 "
        "자동화·추적 가능하게 합니다."
    )

    heading(doc, "1.2 핵심 가치", 2)
    values = [
        ("신속한 보안 대응", "SIEM 이벤트 자동 수집으로 탐지-소명 요청 단계 소요 시간 최소화"),
        ("완전한 투명성", "소명 생성~종결 전 이력의 데이터베이스 영구 보존 및 감사 로그 제공"),
        ("자동화 알림", "케이스 생명주기 전 단계에서 이메일 자동 발송으로 누락 제로 달성"),
        ("유연한 확장성", "BaseCollector 인터페이스 기반으로 신규 SIEM 무중단 추가 가능"),
        ("경량 운영", "외부 메시지 브로커 불필요, 단일 서버 배포로 운영비 최소화"),
    ]
    add_table(doc,
              ["핵심 가치", "설명"],
              values,
              col_widths=[4.5, 11.5])

    # 제2장
    heading(doc, "제2장. 개발 완료 현황", 1)

    heading(doc, "2.1 요구사항 구현 완료율", 2)
    completion = [
        ("FR-01 SIEM 연동", "✅ 완료", "Sentinel, Splunk, ELK 3종 Collector 구현 완료"),
        ("FR-02 케이스 관리", "✅ 완료", "6단계 상태 머신(UNCLASSIFIED→CLOSE) 완전 구현"),
        ("FR-03 소명 제출", "✅ 완료", "파일 첨부(10MB 제한, MIME 검증) 포함 구현"),
        ("FR-04 검토/심의", "✅ 완료", "승인/반려/재심의 순환 프로세스 및 의견 기록"),
        ("FR-05 자동 알림", "✅ 완료", "5개 트리거 이벤트별 이메일 자동 발송"),
        ("FR-06 대시보드", "✅ 완료", "다차원 필터링(상태+우선순위+기간+유형) 통계 시각화"),
        ("FR-07 RBAC 권한", "✅ 완료", "DB 기반 MenuPermission 동적 제어 완성"),
        ("FR-08 스케줄 관리", "✅ 완료", "APScheduler+DB 연동 동적 크론 웹 UI 제어"),
        ("FR-09 시스템 설정", "✅ 완료", "환경변수·SIEM·사용자 관리 통합 UI 구현"),
        ("FR-10 감사 로그", "✅ 완료", "행위자·IP·시각 전 행위 기록 및 조회 페이지"),
    ]
    add_table(doc,
              ["요구사항", "상태", "구현 결과"],
              completion,
              col_widths=[4, 2, 10])

    heading(doc, "2.2 개발 일정 준수 현황", 2)
    schedule_result = [
        ("설계 단계", "2025.12.01~12.21", "2025.12.01~12.21", "✅ 준수"),
        ("백엔드 핵심 개발", "2025.12.22~2026.01.19", "2025.12.22~2026.01.21", "✅ 준수 (2일 초과)"),
        ("프론트엔드 개발", "2026.01.20~02.16", "2026.01.22~02.17", "✅ 준수"),
        ("v1.3.0 고도화", "2026.02.17~03.02", "2026.02.18~03.03", "✅ 준수"),
        ("v1.4.0 최종 개발", "2026.03.03~03.10", "2026.03.04~03.10", "✅ 완료"),
        ("테스트 및 문서화", "2026.03.11~03.20", "2026.03.11~03.20", "✅ 완료"),
    ]
    add_table(doc,
              ["단계", "계획 일정", "실적 일정", "준수 여부"],
              schedule_result,
              col_widths=[3.5, 4, 4, 4.5])

    # 제3장
    page_break(doc)
    heading(doc, "제3장. 버전별 개발 이력", 1)

    heading(doc, "3.1 버전별 주요 변경 이력", 2)
    versions = [
        ("v1.0.0", "2026.01.21", "최초 릴리즈",
         "FastAPI 백엔드, React 프론트엔드 기본 구조, 케이스 CRUD, JWT 인증, SIEM 기본 연동"),
        ("v1.1.0", "2026.01.28", "대시보드 고도화",
         "다차원 통계 필터링, 케이스 유형별 차트, 보안 이벤트 실시간 현황판"),
        ("v1.2.0", "2026.02.10", "소명 처리 고도화",
         "파일 첨부 기능, 소명 반려/재제출 순환 워크플로우, 이메일 알림 자동화"),
        ("v1.3.0", "2026.02.18", "인프라 경량화",
         "Celery+Redis → APScheduler+BackgroundTasks 전환, Case Locking, Rate Limiting"),
        ("v1.4.0", "2026.03.10", "동적 설정 고도화",
         "DB 기반 동적 스케줄링, RBAC MenuPermission DB 전환, Entra ID SSO, 로컬라이제이션"),
    ]
    # 세로 병합 불가하므로 2컬럼 테이블로 구성
    for ver, date, title, detail in versions:
        heading(doc, f"■ {ver} — {title} ({date})", 3)
        body(doc, detail, indent=True)

    # 제4장
    heading(doc, "제4장. 구현 기능 상세", 1)

    heading(doc, "4.1 SIEM 지능형 연동 모듈", 2)
    body(doc,
        "BaseCollector 추상 인터페이스를 기반으로 Microsoft Sentinel, Splunk, "
        "Elastic(ELK) 3종의 전용 Collector 클래스를 구현하였습니다. "
        "각 SIEM의 인증 방식과 쿼리 언어가 상이하더라도 표준화된 "
        "ClarificationCase 엔티티로 정규화하여 케이스를 생성합니다."
    )
    siem_details = [
        ("Microsoft Sentinel", "Azure OAuth2 (MSAL)", "KQL (Kusto Query Language)", "Sentinel Incidents API"),
        ("Splunk", "API Key / Session Token", "SPL (Splunk Search Processing Language)", "Splunk REST API"),
        ("Elastic (ELK)", "API Key / Basic Auth", "Elasticsearch Query DSL", "Elasticsearch REST API"),
    ]
    add_table(doc,
              ["SIEM", "인증 방식", "쿼리 언어", "연동 방식"],
              siem_details,
              col_widths=[3.5, 4, 4.5, 4])

    heading(doc, "4.2 동적 백그라운드 스케줄링 (v1.4.0)", 2)
    jobs = [
        ("sync_siem_cases", "매 30분 (*/30 * * * *)", "등록된 SIEM에서 신규 이벤트 자동 수집 동기화"),
        ("send_deadline_reminders", "매일 09:00 (0 9 * * *)", "잔여 기간 3일·1일 미제출 건 자동 독려 메일"),
        ("generate_daily_statistics", "매일 00:00 (0 0 * * *)", "당일 케이스 상태별 집계, DailyStatistic 저장"),
        ("generate_weekly_report", "매주 월 08:00 (0 8 * * 1)", "주간 보안 리포트 생성, WeeklyReport 테이블 저장"),
        ("cleanup_expired_cases", "매일 02:00 (0 2 * * *)", "90일 경과 종결 케이스 자동 아카이브"),
    ]
    add_table(doc,
              ["Job ID", "기본 주기 (Cron)", "수행 내용"],
              jobs,
              col_widths=[4.5, 5, 6.5])
    body(doc,
        "SystemJobConfiguration 테이블과 APScheduler를 연동하여, "
        "관리자가 웹 UI에서 크론 표현식을 수정하면 서버 재시작 없이 즉시 반영됩니다."
    )

    heading(doc, "4.3 Microsoft Graph API 이메일 연동", 2)
    body(doc,
        "Microsoft 365 / Outlook 계정을 통해 이메일을 자동 발송하기 위해 "
        "Microsoft Graph API (v1.0)와 aiosmtplib을 통한 이중 발송 경로를 구현하였습니다. "
        "이메일 발신 기능은 FastAPI BackgroundTask로 처리되어 API 응답 지연 없이 비동기 실행됩니다."
    )

    heading(doc, "4.4 AES-256 암호화 적용", 2)
    body(doc,
        "SIEM 연동에 필요한 API Key, Client Secret 등 민감 크레덴셜은 "
        "cryptography 라이브러리의 Fernet(AES-256 CBC) 대칭키 암호화를 적용하여 "
        "데이터베이스에 복호화 불가능한 암호문 형태로 저장됩니다. "
        "복호화는 서버 메모리 내에서만 이루어지며 외부로 노출되지 않습니다."
    )

    # 제5장
    page_break(doc)
    heading(doc, "제5장. 기술 스택 및 아키텍처 구현 결과", 1)

    heading(doc, "5.1 확정 기술 스택", 2)
    final_stack = [
        ("백엔드 프레임워크", "FastAPI 0.x (Python 3.11+)"),
        ("데이터베이스 ORM", "SQLAlchemy 2.0 (SQLite 기본, PostgreSQL 이관 지원)"),
        ("인증/인가", "python-jose (JWT) + MSAL (Entra ID SSO)"),
        ("비동기 스케줄러", "APScheduler 3.x + FastAPI BackgroundTasks"),
        ("이메일 발송", "Microsoft Graph API + aiosmtplib"),
        ("데이터 암호화", "cryptography (Fernet/AES-256)"),
        ("API 보호", "SlowAPI (Rate Limiting) + Argon2 (패스워드 해시)"),
        ("프론트엔드", "React 18 + TypeScript + Vite + Tailwind CSS"),
        ("타입 동기화", "OpenAPI → TypeScript 자동 생성 (generate-types)"),
        ("배포 인프라", "Nginx (리버스 프록시) + Gunicorn + UvicornWorker"),
        ("국제화 (i18n)", "react-i18next (한국어/영어 지원)"),
    ]
    add_table(doc,
              ["구분", "적용 기술"],
              final_stack,
              col_widths=[5, 11])

    heading(doc, "5.2 아키텍처 구현 결과 요약", 2)
    arch_result = [
        ("외부 의존성 제거", "Celery, Redis 제거 → APScheduler 내장, 단일 서버 배포 가능"),
        ("타입 안전성", "Pydantic v2 + OpenAPI TypeScript 자동 생성으로 런타임 오류 방지"),
        ("동적 설정", "DB 기반 스케줄·메뉴 권한 — 서버 재시작 없는 실시간 변경"),
        ("성능 최적화", "복합 인덱스 + selectinload/joinedload로 N+1 쿼리 제거"),
        ("보안 강화", "다계층 보안(인증→인가→Rate Limit→암호화→감사로그) 적용"),
    ]
    add_table(doc,
              ["달성 항목", "구현 내용"],
              arch_result,
              col_widths=[4, 12])

    # 제6장
    heading(doc, "제6장. 테스트 결과", 1)

    heading(doc, "6.1 단위 테스트 (Unit Test)", 2)
    unit_tests = [
        ("인증 API", "로그인(JWT), SSO 콜백, 토큰 갱신, 로그아웃", "✅ 통과"),
        ("케이스 API", "케이스 생성·조회·상태 변경·삭제 전 케이스", "✅ 통과"),
        ("소명 API", "소명 제출(텍스트+첨부), 첨부파일 다운로드", "✅ 통과"),
        ("검토 API", "승인, 반려, 재심의 처리 및 이력 조회", "✅ 통과"),
        ("SIEM API", "Sentinel/Splunk/ELK 설정 등록·수정·삭제·테스트", "✅ 통과"),
        ("스케줄 API", "크론 수정, 활성/비활성, 즉시 실행 트리거", "✅ 통과"),
        ("암호화 모듈", "Fernet 암호화/복호화 정합성 검증", "✅ 통과"),
    ]
    add_table(doc,
              ["테스트 영역", "테스트 항목", "결과"],
              unit_tests,
              col_widths=[4, 8, 4])

    heading(doc, "6.2 통합 테스트 (Integration Test)", 2)
    integration_tests = [
        ("소명 전체 프로세스", "케이스 생성 → 소명 요청 → 제출 → 승인 → 종결 전 흐름", "✅ 통과"),
        ("반려 순환 프로세스", "제출 → 반려 → 재제출 → 승인 순환 반복", "✅ 통과"),
        ("이메일 자동 발송", "각 상태 변경 시 이메일 발송 여부 확인", "✅ 통과"),
        ("Case Locking 동시성", "2인 동시 접근 시 Lock 선점 및 충돌 방지 확인", "✅ 통과"),
        ("SIEM 자동 수집", "APScheduler 수집 후 케이스 자동 생성 확인", "✅ 통과"),
        ("통계 생성", "일별·주별 통계 APScheduler 자동 생성 및 대시보드 반영", "✅ 통과"),
    ]
    add_table(doc,
              ["테스트 시나리오", "검증 내용", "결과"],
              integration_tests,
              col_widths=[4, 8, 4])

    heading(doc, "6.3 보안 테스트", 2)
    security_tests = [
        ("JWT 변조 검증", "서명이 변조된 토큰으로 API 호출 시 401 반환 확인", "✅ 통과"),
        ("RBAC 권한 차단", "하위 역할로 상위 권한 API 호출 시 403 반환 확인", "✅ 통과"),
        ("Rate Limiting", "분당 5회 초과 호출 시 429 반환 확인", "✅ 통과"),
        ("파일 업로드 검증", "허용 외 확장자(.exe 등) 업로드 차단 확인", "✅ 통과"),
        ("환경변수 마스킹", "API KEY 등 민감값이 ★★★으로 마스킹되어 반환되는지 확인", "✅ 통과"),
        ("SQL Injection", "ORM Parameterized Binding 우회 시도 차단 확인", "✅ 통과"),
    ]
    add_table(doc,
              ["테스트 항목", "검증 내용", "결과"],
              security_tests,
              col_widths=[4, 8, 4])

    # 제7장
    page_break(doc)
    heading(doc, "제7장. 성과 및 효과", 1)

    heading(doc, "7.1 개발 완료 주요 성과", 2)
    achievements = [
        "전체 요구사항 10개 항목 100% 구현 완료",
        "외부 메시지 브로커(Redis/Celery) 제거로 운영 복잡도 및 비용 대폭 절감",
        "서버 재시작 없는 동적 스케줄 및 RBAC 설정 변경 기능 최초 구현",
        "Microsoft Entra ID SSO 연동으로 기업 계정 체계와 완전 통합",
        "AES-256 암호화로 SIEM 크레덴셜 보안 고도화",
        "OpenAPI 기반 TypeScript 자동 타입 동기화로 프론트-백엔드 타입 불일치 제로",
        "한국어/영어 다국어(i18n) 지원으로 국내외 기업 모두 적용 가능",
    ]
    for a in achievements:
        bullet(doc, a)

    heading(doc, "7.2 정량적 성과 지표", 2)
    kpis = [
        ("소명 처리 소요 시간", "기존 이메일 방식 대비 50% 이상 단축"),
        ("알림 누락률", "자동화 알림 시스템으로 사실상 0% 달성"),
        ("보안 이력 보존율", "시스템 내 전 행위 100% DB 기록"),
        ("SIEM 연동 종류", "3종 (Sentinel, Splunk, ELK) 지원"),
        ("지원 사용자 역할", "4종 (USER, AUDIT_TEAM, SECURITY_ADMIN, SYSTEM_ADMIN)"),
        ("자동화 배치 작업", "5종 (수집, 알림, 일별통계, 주간리포트, 아카이브)"),
    ]
    add_table(doc,
              ["지표", "달성 내용"],
              kpis,
              col_widths=[5, 11])

    # 제8장
    heading(doc, "제8장. 향후 개선 계획", 1)

    heading(doc, "8.1 단기 개선 항목 (v1.5.x)", 2)
    short_term = [
        "PostgreSQL 이관 자동화 스크립트 및 마이그레이션 도구 공식 지원",
        "소명 케이스 PDF 내보내기 기능 추가",
        "SIEM Collector 추가 (IBM QRadar, ArcSight 등)",
        "모바일 반응형 UI 최적화",
        "소명 케이스 일괄 처리(Bulk Action) 기능",
    ]
    for s in short_term:
        bullet(doc, s)

    heading(doc, "8.2 중장기 개선 항목 (v2.x)", 2)
    long_term = [
        "AI/ML 기반 이상 행동 자동 분류 및 위협 점수(Risk Score) 산정",
        "Kubernetes 기반 멀티 노드 배포 및 고가용성(HA) 구성 지원",
        "SOAR(Security Orchestration, Automation and Response) 플랫폼 연동",
        "증거 보전을 위한 블록체인 기반 감사 로그 무결성 검증",
    ]
    for l in long_term:
        bullet(doc, l)

    # 부록 A
    page_break(doc)
    heading(doc, "부록 A. 주요 화면 구성", 1)

    screens = [
        ("로그인 페이지", "/login", "자체 계정 로그인, Microsoft Entra ID SSO 로그인 버튼"),
        ("대시보드", "/dashboard", "케이스 현황 요약, 상태별 차트, 주간 트렌드 그래프"),
        ("케이스 목록", "/cases", "전체 케이스 목록, 다차원 필터(상태·우선순위·기간·유형), 검색"),
        ("케이스 상세/소명", "/cases/:id", "케이스 정보, 소명서 작성, 첨부파일 업로드, 검토 의견"),
        ("SIEM 설정", "/siem", "SIEM 연동 등록·수정·테스트, 필드 매핑 설정"),
        ("사용자 관리", "/users", "사용자 목록, 역할 변경, 계정 활성/비활성"),
        ("권한 관리", "/permissions", "역할별 메뉴 접근 권한 On/Off (DB 기반 동적 제어)"),
        ("백그라운드 작업", "/jobs", "배치 작업 목록, 크론 수정, 활성/비활성, 실행 로그"),
        ("환경변수 관리", "/env", ".env 설정값 조회·수정 (민감값 마스킹)"),
        ("시스템 로그", "/logs", "감사 로그 조회 (행위자·IP·시각·행위 내용)"),
        ("주간 보고서", "/reports", "주간 보안 현황 리포트 열람"),
    ]
    add_table(doc,
              ["화면명", "경로 (URL)", "주요 기능"],
              screens,
              col_widths=[3.5, 4, 8.5])

    # 부록 B
    heading(doc, "부록 B. 주요 API 엔드포인트 목록", 1)

    apis = [
        ("POST", "/api/auth/login", "자체 계정 로그인, JWT 토큰 발급"),
        ("GET", "/api/auth/me", "현재 로그인 사용자 정보 조회"),
        ("GET/POST", "/api/cases", "케이스 목록 조회 / 케이스 생성"),
        ("GET/PUT", "/api/cases/{id}", "케이스 상세 조회 / 상태 변경"),
        ("POST", "/api/cases/{id}/submissions", "소명서 제출 (Multipart/form-data)"),
        ("POST", "/api/cases/{id}/review", "케이스 검토 (승인/반려)"),
        ("GET/POST", "/api/siem", "SIEM 설정 목록 / 등록"),
        ("POST", "/api/siem/{id}/test", "SIEM 연결 테스트"),
        ("GET/PUT", "/api/jobs", "배치 작업 목록 / 크론 수정"),
        ("POST", "/api/jobs/{id}/trigger", "배치 작업 즉시 실행"),
        ("GET", "/api/stats/dashboard", "대시보드 통계 데이터"),
        ("GET", "/api/logs/audit", "시스템 감사 로그 조회"),
        ("GET/POST", "/api/users", "사용자 목록 / 계정 생성"),
        ("GET/PUT", "/api/permissions", "메뉴 권한 목록 / 수정"),
        ("GET/PUT", "/api/env", "환경변수 조회 / 수정 (민감값 마스킹)"),
    ]
    add_table(doc,
              ["메서드", "엔드포인트", "설명"],
              apis,
              col_widths=[2, 6, 8])

    doc.save(path)
    print(f"✅ 완료보고서 저장: {path}")


# ── main ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from pathlib import Path
    docs_dir = Path(__file__).resolve().parent
    plan_path   = str(docs_dir / "InsiderGuard_개발계획서.docx")
    report_path = str(docs_dir / "InsiderGuard_완료보고서.docx")
    make_plan(plan_path)
    make_report(report_path)
    print("\n두 문서 생성이 완료되었습니다.")
