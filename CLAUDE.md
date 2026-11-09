# CLAUDE.md — Fleit InsiderGuard (SICS)

SIEM에서 탐지된 내부자 보안 인시던트에 대해 임직원 소명을 받고 보안팀이 심의하는 시스템.
응답·주석·커밋 메시지는 **한국어**로 작성한다.

## 기술 스택
- Backend: FastAPI, SQLAlchemy, Pydantic v2, JWT(python-jose), APScheduler, slowapi, msal — `backend/`
- Frontend: React 18 + TypeScript + Vite, TailwindCSS, TanStack Query, axios, i18next — `frontend/`
- DB: SQLite (`.env`의 `DATABASE_URL`, 기본 `sqlite:///./sql_app.db`, 루트 기준). 스키마는 Alembic(`backend/migrations/`)으로 관리. PostgreSQL 이관 예정
- 패키지 import는 항상 `backend.` 접두사 사용 (루트에서 실행)

## 자주 쓰는 명령 (모두 프로젝트 루트 기준)
```bash
# 가상환경: 프로젝트 루트의 .venv 하나만 사용 (Python 3.12.3)
source .venv/bin/activate && pip install -r backend/requirements-dev.txt
# 백엔드 실행 (HTTPS)
uvicorn backend.main:app --reload --host 0.0.0.0 --ssl-keyfile key.pem --ssl-certfile cert.pem
# 백엔드 테스트
python -m pytest backend/test_main.py -q
# 프론트엔드
cd frontend && npm run dev        # 개발 서버
cd frontend && npm run build      # tsc -b && vite build (완료 조건)
cd frontend && npm run lint
# DB 마이그레이션 (DB URL은 .env의 DATABASE_URL)
alembic upgrade head
alembic revision --autogenerate -m "변경 내용"   # 생성 파일 반드시 검토
alembic check                                  # 모델과 DB 차이 확인
# API 변경 후 타입 동기화
python backend/scripts/generate_openapi.py && cd frontend && npm run generate-types
```

## 구조
- `backend/main.py` — 앱 생성, 미들웨어, 라우터 등록, lifespan(초기 시딩·스케줄러)
- `backend/models.py`, `backend/schemas.py` — 공용 ORM 모델 / Pydantic 스키마
- `backend/modules/<도메인>/router.py` — API (auth, users, cases, submissions, reviews, siem, system, audit, reports, integrations, notifications)
- `backend/core/` — config, database, dependencies(인증), permissions(RBAC), security(Fernet), scheduler, mail
- 메일은 `backend/core/mail/services.py`의 `send_template_mail` 하나로 발송 (템플릿 목록·기본 제목 `core/mail/templates.py`, 기본 본문 `backend/templates/email/`, 관리자 수정본은 DB `notification_template`이 우선하며 Jinja2 샌드박스로 렌더링. SMTP/Outlook은 `MAIL_SENDER_TYPE`). 새 메일은 `TEMPLATES`에 등록하고 제목을 하드코딩하지 말 것
- `backend/services/` — SIEM 수집기 (`BaseCollector` → `SentinelCollector`, `collector_factory`)
- `backend/tasks/` — 배치/메일/SIEM 동기화 작업
- `frontend/src/pages/` 화면, `services/` API 클라이언트, `components/`, `locales/{ko,en}/translation.json`
- `docs/` — 아키텍처, 소명 프로세스, ERD, API 가이드, 선택 연동 가이드(`INTEGRATION_GUIDE.md`) (도메인 규칙이 필요하면 먼저 읽을 것)

## 도메인 핵심 규칙 (깨뜨리지 말 것)
- 케이스 상태: `UNCLASSIFIED → REQUEST → SUBMIT → APPROVE | REJECT(A 재소명 / B 교육·서약 / C 감사이관) → CLOSE`
- 일반 사용자는 **본인 케이스만**, 그리고 `UNCLASSIFIED`/`CLOSE` 상태는 API·UI 모두에서 볼 수 없다
- 관리자 역할: `SECURITY_ADMIN`, `SYSTEM_ADMIN`, `AUDIT_TEAM`. 심의 중에는 Case Lock 사용
- 주요 행위는 `SystemAuditLog`에 기록한다 (관리자 열람 `CASE_VIEWED`, 첨부 다운로드, CSV 내보내기 포함)
- 기한 초과는 상태가 아니라 표시(`is_overdue` = 요청 상태 + 기한 경과). 첨부는 업로드 시 SHA-256 저장·다운로드 시 검증. 보존기간 파기는 익명화 방식이며 `legal_hold` 케이스 제외 (`backend/modules/cases/retention.py`)
- 부서장(`users.manager_id`)은 참조 메일 수신자일 뿐 권한이 없다. Teams 알림에는 직원 이름·소명 내용을 넣지 않는다
- Entra ID·SIEM은 **선택 연동**: 설치 후 관리자 화면에서 설정하고 DB에 저장(`integration_setting`, `siem_configuration`, 시크릿 Fernet 암호화). `.env`·`VITE_*`·코드에 테넌트/클라이언트 ID·시크릿을 두지 말 것. 연동 미설정 시 관련 기능은 꺼진 상태로 동작해야 함 (`backend/modules/integrations/services.py`의 `get_entra_config`로 판단)
- UI 문자열 추가 시 `ko`/`en` 번역 파일 **둘 다** 갱신

## 코딩 규칙
- 시크릿·URL·키 하드코딩 금지 → `backend/core/config.py`의 `settings` 또는 환경 변수 사용
- 예외는 `backend/core/exceptions.py`의 커스텀 예외 사용, 로깅은 `logging_config` 로거 사용
- 새 비즈니스 로직은 라우터가 아닌 `services.py`에 작성 (기존 대형 라우터는 점진 분리 중)
- 권한 검사를 생략하지 말 것. 파일 경로 검사는 `Path.resolve()` + `is_relative_to()` 사용
- 변경은 요청 범위로 최소화. 무관한 리팩터링·포매팅 금지
- 불확실한 API/라이브러리 동작은 추측하지 말고 "확인 필요"로 표시

## 작업 흐름
1. 관련 코드·문서 확인 → 2. 변경 계획 공유 → 3. 구현 → 4. 테스트·빌드 실행 → 5. 결과 보고
- 완료 조건: `pytest` 통과(기존 실패 제외) + `npm run build` 성공
- 기능 변경 시 `docs/` 해당 문서 동시 갱신
- 저장소: `origin` = https://github.com/tico2k/SISC-Claude.git (유일한 저장소. 이전 SICS.git은 이 프로젝트에서 사용하지 않음 — 연결·push·참조 금지)
- 브랜치: `main` 직접 수정 금지, `feature/<내용>`, `fix/<내용>` 브랜치에서 작업. 커밋은 사용자가 요청할 때만

## 수정 금지 / 주의
- `uploads/`(실제 첨부), `_archive/`(이전 DB 백업) — 읽기만
- `.env`, `*.pem`, `*.db` — 내용 출력·커밋 금지
- `scripts/legacy/`는 Alembic 도입 전 일회성 스크립트 보관소. 새 스키마 변경은 반드시 Alembic 마이그레이션으로
- ORM 모델을 새 모듈에 추가하면 `backend/migrations/env.py`의 모델 등록 import에도 추가
- `main.py`의 `create_all`은 과도기용으로 유지 중(신규 테이블만 생성, 컬럼·인덱스 변경은 반영 안 됨)

## Phase 1 진행 현황
- 완료: 첨부 경로 검사, `/new-skill` 템플릿 라우터 등록 해제(모듈 폴더는 예시로 보존), 복호화 실패 시 `DecryptionError` 발생, .env 관리(민감값 완전 마스킹·`ENCRYPTION_KEY`/`DATABASE_URL` 민감 분류·키 형식 검증·신규 키 추가 차단), 버전 2.1.0 단일화(`settings.APP_VERSION`)
- 완료(2차): `backup_backend/`·`plan/` 삭제, git 추적 DB·pyc 제거, 미사용 DB는 `_archive/db/`로 이동, 일회성 스크립트 `scripts/legacy/`로 이동, `database.py`가 `DATABASE_URL`을 읽도록 수정(기존엔 `SICS_DATABASE_URL`만 읽음), Alembic 도입(0001 baseline, 0002 레거시 인덱스 정렬) 및 운영 DB 적용
- 보류: 관리자 기본 비밀번호 변경 강제(사용자 요청으로 제외)

## 현재 기준선 (2026-11-09 확인)
- pytest: 80개 전체 통과 (Phase 1 보안 회귀 + Phase 2 케이스 워크플로우: 상태 전이, 사용자 격리, Case Lock, 감사로그, 메일 작업 호출·링크 주소, 메일 프로바이더 통합 + 선택 연동: Entra 설정 저장·마스킹·검증, ID 토큰 검증, 메뉴 권한 시딩, SIEM 매핑 필수 + 소명 개선: 기한 초과·무결성·파기·증거 보존·부서장 참조·직원 이력·CSV·템플릿 샌드박스·Teams·본인 역할 변경 차단)
- 테스트는 autouse 픽스처에서 메일 발송을 끄고 메일 작업과 `core.database.SessionLocal`을 테스트 DB로 교체함 (운영 DB 접근 방지)
- 케이스 상태 전이 규칙은 `backend/modules/cases/services.py`에 집중. 새 상태 변경 API도 반드시 이 함수들을 거칠 것
- Alembic head: `0004` (소명 기능 개선)
- frontend build: 성공 (번들 1.1MB, 코드 분할 경고)
- frontend lint: 오류 0 / 경고 7 (`react-hooks/exhaustive-deps` 6건 등, 동작 영향 검토 후 정리 예정). 새 코드에 `any` 금지 — API 응답 타입은 `src/types/index.ts`, catch 절은 `unknown` + `src/utils/error.ts` 헬퍼 사용
- Pydantic 설정은 `model_config = ConfigDict(...)` / `SettingsConfigDict(...)` 사용 (`class Config` 금지). pytest 경고는 외부 라이브러리(passlib crypt, TestClient httpx) 2건만 남음
- 알려진 개선 과제: 프로젝트 문서 `InsiderGuard_Claude_개발계획.md`의 Phase 1~3 참고
