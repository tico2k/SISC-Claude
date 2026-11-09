# 시스템 설계 및 프로세스 분석서 (System Design & Process Analysis)

본 문서는 **SICS (Security Incident Clarification System)**의 시스템 아키텍처, 데이터 흐름, 보안 및 성능 최적화 전략을 기술한 설계 명세서입니다.

---

## 1. 개발 의도 및 목적 (Development Objectives)

본 프로젝트는 현대적인 웹 기술 스택인 **FastAPI (Backend)**와 **React (Frontend)**를 기반으로 구축되었으며, 외부 인프라 의존성을 최소화한 **초경량 내장형 스케줄러(APScheduler)** 와 **비동기 처리(BackgroundTasks)** 를 활용한 고성능 아키텍처를 자랑합니다.

### 🛠️ 기술 선정 배경 (Tech Stack Rationales)

| 기술 스택 | 선정 이유 및 장점 |
| :--- | :--- |
| **FastAPI (Python)** | **1. 고성능 비동기 처리**: Python 3.6+의 `async`/`await`를 기본 지원하며, 최신 `lifespan` 핸들러를 통해 서버 생명주기를 안전하게 관리합니다.<br>**2. 생산성 및 안정성**: Pydantic v2를 이용한 강력한 데이터 검증과 Type Hinting을 통해 런타임 오류를 사전에 방지합니다.<br>**3. 자동 타입 동기화**: OpenAPI 명세를 프론트엔드 TypeScript Interface로 완벽히 변환하는 파이프라인(`generate-types`) 연계에 최적화되어 있습니다. |
| **React (TypeScript)** | **1. 컴포넌트 기반 아키텍처**: 커스텀 훅과 모듈화된 UI를 통해 개발 속도와 유지보수성을 극대화합니다.<br>**2. 풍부한 생태계**: Vite, Tailwind CSS 등 모던 도구들과 통합되어 직관적이고 일관성 있는 UX를 제공합니다.<br>**3. 타입 안정성**: 백엔드와 완벽히 일치하는 정적 타입 검사를 통해 런타임 크래시를 방지합니다. |
| **APScheduler & BackgroundTasks** | **1. 인프라 경량화 (v1.3.0)**: 기존 Celery+Redis 아키텍처를 걷어내어, 별도의 메시지 브로커 설치 없이 애플리케이션 수명주기 내에서 정기/단기 비동기 작업을 모두 소화합니다.<br>**2. 지연 없는 이벤트**: 이메일 알림, SIEM 크롤링 등을 메인 스레드 블로킹 없이 FastAPI 백그라운드 워커에서 즉시 분산 처리합니다.<br>**3. 운영 비용 절감**: 온프레미스/클라우드 등 어떤 환경에서도 단일 컨테이너(Single Node)로 즉시 배포가 가능합니다. |

### 💎 핵심 비즈니스 가치 (Core Business Values)

1. **신속한 보안 대응**: 대시보드의 다차원 교차(Synergistic) 필터링을 통해 위반 사례를 실시간 시각화하고, 보안 공백을 즉각 식별합니다.
2. **충돌 없는 워크플로우**: 임직원(소명 제출)과 관리자(검토) 간 역할 분담은 물론, **Case Locking** 기술을 통해 복수 관리자의 중복 심의를 원천 방어합니다.
3. **투명한 추적성**: 시스템 내 모든 주요 행위는 데이터베이스의 Audit Log 이력으로 영구 보존됩니다.
4. **자동화된 알림 체계**: 위협 탐지, 마감 임박, 처리 완료 등 각 생명주기 병목 구간마다 지정된 대상에게 자동 알림 메일을 발송합니다.
5. **표준화된 SIEM 연동**: `BaseCollector` 인터페이스를 거쳐 Sentinel, Splunk, Elastic 등 다기종 SIEM 소스를 코드 변경 없이 유연하게 수용합니다.
6. **중앙 집중형 통합 관리**: 시스템 핵심 설정(`.env`) 및 암호화 기법(AES-256)을 웹 UI와 통합하여 안전한 서버 운영을 돕습니다.

---

## 2. 시스템 아키텍처 및 프로세스 (System Architecture)

### 🏗️ 전체 아키텍처 다이어그램 (v2.1.0)

```mermaid
graph TB
    subgraph "Client Tier (React + Vite)"
        Browser[웹 브라우저]
        Lang[i18n Context / 다국어 사전]
        SmartNav[Smart Navigation & State Controller]
        MultiFilter[Multi-Status OR Filtering Engine]
        EscalationModal[Audit Escalation Report Print Engine]
    end
    
    subgraph "Frontend Security & UI Layer"
        React[React 18 + TypeScript + TailwindCSS]
        UserView[User View: Direct /cases/{id} Access]
        AdminView[Admin View: Review & Audit /reviews]
        React --> SmartNav
        React --> MultiFilter
        React --> EscalationModal
        React --> Lang
    end
    
    subgraph "Backend Application (FastAPI)"
        Core[Lifespan & Middleware]
        Auth[JWT / SSO 인증 & Data Isolation Guard]
        Router[API Routers (Cases, Reviews, System, Auth)]
        Service[Service & Clarification Engine]
        Exception[Custom Exception Handlers]
        Logging[Structured JSON Logging]
        
        subgraph "Internal Task Manager"
            BTasks[FastAPI BackgroundTasks]
            Scheduler[APScheduler - Dynamic DB Sync]
        end
    end
    
    subgraph "Data & External Tier"
        DB[(SQLite / PostgreSQL)]
        SeedEngine[Enterprise Realistic Seeding Engine]
        Files[Local File Storage (Audit Attachments)]
        SIEM[(External SIEMs - Sentinel/Splunk/ELK, 선택)]
        SMTP[(Mail Server - SMTP / Graph 선택)]
    end
    
    Browser --> React
    SmartNav --> UserView
    SmartNav --> AdminView
    UserView --> Core
    AdminView --> Core
    Core --> Auth
    Auth --> Router
    Router --> Service
    Service --> DB
    Service --> Files
    SeedEngine --> DB
    Router --> Exception
    Router --> Logging
    
    Service -.- BTasks
    Core -.- Scheduler
    
    BTasks -.-> SMTP
    Scheduler -.-> Service
    Scheduler -.-> SIEM
```

### 🔄 Frontend & Backend 상호작용 (Interaction Flow)

React 클라이언트와 FastAPI 서버는 OpenAPI 기반으로 완벽히 타입이 동기화된 REST API를 교환합니다.

1. **요청 (Client)**: 사용자가 React UI에서 액션을 수행하면, 동기화된 API 클라이언트(`Axios`)가 지정된 엔드포인트로 요청을 송신합니다.
2. **검증 (Server)**: FastAPI는 Pydantic v2 모델로 Payload의 유효성을 1차 검사합니다 (`RequestValidationError` -> 422 반환).
3. **인증 / 인가 (Auth)**: 헤더의 JWT 무결성을 검증(`get_current_user`)하고, 라우터 레벨에서 `require_roles` 데코레이터를 통해 RBAC 인가를 판별합니다.
4. **처리 (Service)**: 유효한 요청은 Service Layer로 인계되어 RDB 트랜잭션 등 비즈니스 로직을 수행합니다.
5. **비동기 이관 (Background)**: 이메일 전송과 같은 I/O 바운드 작업은 `BackgroundTasks.add_task()`를 통해 즉시 위임됩니다.
   - 메일은 `backend/core/mail/services.py` 하나로 발송합니다. `backend/templates/email/*.html`(Jinja2, HTML 자동 이스케이프)을 렌더링한 뒤, `MAIL_SENDER_TYPE`(SMTP 또는 OUTLOOK)에 따라 `MailFactory`가 고른 프로바이더로 보냅니다.
   - 발송 함수는 blocking I/O이므로 동기 함수로 두어 BackgroundTasks·스케줄러의 스레드에서 실행됩니다 (이벤트 루프를 막지 않음).
6. **응답 (Response)**: 직렬화된 JSON 결과가 클라이언트로 반환되며 성공/실패 여부에 따라 UI가 반응합니다.

### 🌊 데이터 트랜잭션 흐름도 (ex. 소명 제출)

1. **Frontend View**: 사용자가 소명 사유 작성 및 다중 증빙 파일 첨부 후 '제출'.
2. **API Client**: `POST /submissions` (Multipart/form-data) 규격 전송.
3. **Security Check**:
    - JWT 토큰 변조 여부 검사.
    - Path Traversal 및 업로드 파일 포맷(MIME/Size) 무결성 체크.
4. **Service Layer**:
    - 물리 스토리지에 파일 안전 저장 (`/uploads/...`).
    - DB 세션 획득 후 `ClarificationSubmission`, `ClarificationAttachment` 엔티티 생성.
    - 부모인 `ClarificationCase`의 결재 상태를 `'SUBMIT'`으로 승급 업데이트.
5. **Database**: All-or-Nothing (try-except-rollback) 트랜잭션 Commit.
6. **Background Task**: 메인 쓰레드 해제 후, 권한 있는 관리자에게 소명 접수 알림 이메일 비동기 발송.
7. **Response**: 200 OK 와 함께 업로드된 엔티티 형상 클라이언트 반환.

---

## 3. 내부 백그라운드 태스크 아키텍처 (In-Process Automation)

v1.3.0부터 외부 메세지 큐(Celery/Redis)를 제거하고 **APScheduler**를 서버 수명주기에 내장했습니다. 나아가 **v1.4.0 업데이트**를 통해 기존 코드에 하드코딩되어 있던 크론 규칙을 **데이터베이스 기반 동적 스케줄링(Dynamic Scheduling)** 으로 전환했습니다.

### 📧 이벤트 트리거 (FastAPI BackgroundTasks)

단발성으로 발생하는 지연 작업들은 라우터 단에서 즉각 위임됩니다:

- **케이스 생성 시**: `send_case_created_email`
- **검토 완료 시**: `send_case_reviewed_email`
- **소명 요청 발송 시**: `send_clarification_request_email`

### 🔄 정기 배치 작업 (APScheduler DB 연동)

관리자는 프론트엔드 UI를 통해 정기 작업들의 일정을 변경하거나, 임시 중지/재개할 수 있으며 APScheduler는 이를 즉시 반영합니다.

| 등록된 Job (`job_id`) | 디폴트 패턴 | 수행 내용 (Task Function) |
|------|-------|---------------|
| `cleanup_expired_cases` | `0 2 * * *` | 90일 지난 종결 데이터를 조회 후 자동 보관(Archive) |
| `send_deadline_reminders` | `0 9 * * *` | 마감이 3일/1일 남은 미제출자에게 안내 메일 발송 |
| `generate_daily_statistics` | `0 0 * * *` | 당일 생성 케이스의 현재 상태별 정산 및 DB 저장 로직 |
| `generate_weekly_report` | `0 8 * * 1` | 주간 통계 집계 및 `WeeklyReport` 테이블 저장 (대시보드 노출) |
| `sync_siem_cases` | `*/30 * * * *` | SIEM 모듈별 수집 스케줄 (각 SIEM 설정 테이블 내에 명시됨) |

> **동적 갱신 메커니즘**: 사용자가 `SystemJobConfiguration` 레코드를 변경하는 API를 호출하면, 서버 내부적으로 할당되어 구동중인 APScheduler 객체의 `reschedule_job` 또는 `pause_job` / `resume_job`을 직접 파이프라인으로 호출하여 재시작 없는 즉시 적용을 보장합니다.

---

## 4. 보안 및 성능 최적화 (Security & Performance)

### 🔒 보안 방벽 설계 (Defense in Depth)

1. **인증 및 인가 (Authentication / SSO)**:
    - **Local JWT & Microsoft Entra ID (선택)**: 자체 JWT 로그인이 기본이며, 설치 후 관리자가 `외부 연동 설정`에서 Entra를 활성화하면 OIDC SSO를 지원. 서버는 ID 토큰의 서명(JWKS)·aud·tid·만료를 검증하며, 연동 정보는 DB(`integration_setting`)에 암호화 저장되어 재시작·재빌드 없이 반영.
    - **역할 기반 데이터 격리 (Data Isolation Policy - v2.1.0)**:
      - 일반 사용자(`USER` / `일반`) 권한의 경우 미검토 상태인 `UNCLASSIFIED(미확인)` 및 내부 정리용 `CLOSE(종결)` 건에 대한 API 접근 및 프론트 노출을 원천 격리/차단.
      - 대시보드의 전사 트렌드 통계 차트 및 주간 리포트 위젯은 일반 사용자 세션에서 렌더링되지 않도록 보안 은닉 처리.
    - **동시성 제어 (Case Locking)**: 두 명의 관리자가 동일 케이스 심의 시 `locked_by_id`, `locked_at`으로 상태를 선점하여 덮어쓰기 무결성(Lost Update) 원천 방어.
    - **동적 권한 제어 (RBAC Menu Permissions)**: 역할(Role)별 접근 가능 메뉴가 프론트엔드 하드코딩 상태에서 백엔드 단의 DB(`MenuPermission`) 기반으로 통제되도록 격상하여, 중앙 관리자가 실시간으로 페이지 노출 여부를 조작할 수 있습니다.
2. **반려 3대 분기 및 감사 연계 (Audit Escalation Architecture)**:
    - 소명 반려 시 단순 텍스트 거절이 아닌 **유형 A(재소명), 유형 B(교육/서약), 유형 C(징계/감사이관)** 로 서브 분기 제어.
    - 중대 위반건 이관 시 즉시 활용 가능한 브라우저 프린트 최적화 `보안 감사 보고서(Audit Escalation Report)` 팝업 모달 제공.
3. **API & 런타임 보안**:
    - **SlowAPI (Rate Limiting)**: 엔드포인트 무차별 대입 및 DDoS성 호출 제어 (분당 5회 등 설정).
    - **안전한 환경 변수 지퍼 (Safety Zipper)**: `.env` 조회/수정 기능 제공 시 민감 KEY(토큰 등)는 별표(`******`) 자동 마스킹 및 경로 주입 방어 적용.
    - **SIEM 시크릿 암호화**: 연결 정보(Secret, API Key) 등은 RDB 쓰기 전 **AES-256 Fernet** 대칭키로 암호화 보관.
4. **데이터 보호**:
    - **초기 부트스트랩**: 처음 구동되는 서버는 미리 선언된 고유 식별자(`INITIAL_ADMIN_EMAIL`) 외 시스템 접근을 통제.
    - **SQL Injection 방어**: SQLAlchemy ORM을 통한 Parameterized Binding 100% 적용.

### ⚡ 성능 및 UX 최적화 (Performance & UX Optimizations)

1. **프론트엔드 네비게이션 & 상태 보존 (Smart Navigation)**:
    - `useNavigate`의 `state: { from: 'dashboard' }` 및 `navigate(-1)` 기반 스마트 복귀 엔진을 구축하여 이전 필터 상태와 작업 맥락 보존.
    - 일반 사용자의 경우 대시보드 사건 클릭 시 즉시 `/cases/{id}`로, 관리자는 `/reviews?caseId={id}`로 자동 분기 처리.
2. **다중 상태(OR) 필터링 엔진**:
    - `Set<string>`을 이용한 복수 상태 토글 및 `RotateCcw` 일괄 초기화 버튼을 통해 100% 클라이언트 사이드 즉시 필터링(무지연) 구현.
3. **완벽한 다국어(i18n) 및 렌더링 무결성**:
    - 전 화면 다국어 사전 통일 및 텍스트 오버플로우 방지를 위한 테이블 헤더 고정 너비(`w-[130px]`) 및 반응형 최소폭(`min-w-[1220px]`) 가드 적용.
    - 보안 관제 표준 용어 준수: 우선순위 표기를 `Normal` 대신 `Medium(보통)`으로 통일.
4. **대용량 실감형 시드 데이터 엔진 (Seed Generator Engine)**:
    - 200건의 다채로운 실사 SIEM 케이스, 20일간의 연속 `DailyStatistic`, 5주간의 `WeeklyReport` 데이터를 클릭 한 번(`POST /system/seed`)으로 안전하게 인입.

---

## 5. 관리 및 진단 (DevOps & Monitoring)

### 시스템 확장을 위한 구조 (Extensibility)

- **SIEM Collector Factory**: `BaseCollector` 인터페이스만 상속(`implement`)하면 어떤 써드파티 보안 장비 모듈이라도 코어 로직 훼손 없이 Plugin-Play 방식으로 증설 도입 가능합니다.

### 로그 분석 지수 (Observability)

- **구조적 로깅**: `logging_config.py`에 의해 모든 시스템 에러, DB 크래시, HTTP 트랜잭션은 추론 가능한 JSON-like 포맷과 Exc_info 스택트레이스를 동반해 `logs/` 디렉토리에 일자별 롤링 아카이브 됩니다.

---

**작성일**: 2026-02-15  
**최종 수정**: 2026-11-06 (v2.1.0 데이터 격리, 반려 3대 분기, 감사 보고서 엔진, 스마트 네비게이션, 다중 필터 반영)  
**작성자**: Senior AI System Architect
