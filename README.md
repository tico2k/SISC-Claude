# Fleit InsiderGuard - SICS (Security Incident Clarification System)

**내부자 보안 인시던트 소명·심의 관리 시스템 (v2.1.0)**

SIEM에서 탐지된 내부자 보안 인시던트에 대해 관련 임직원에게 소명을 받고, 보안팀이 심의·조치하는 과정을 관리합니다.
외부 연동 없이 설치 후 바로 사용할 수 있으며, Microsoft Entra ID와 SIEM 연동은 조직 상황에 맞춰 **설치 후 관리자 화면에서** 설정합니다.

---

## 📋 주요 기능

- ⚖️ **소명 워크플로우**: `미확인 → 요청 → 제출 → 승인 | 반려 → 종결`. 반려는 **재소명(A)**, **보안교육·서약(B)**, **감사 이관(C)** 3가지 후속 조치로 구분
- 🔐 **역할 기반 접근 제어**: 일반 사용자는 본인 케이스만 볼 수 있고 `미확인`·`종결` 상태는 API·UI 모두에서 차단. 역할별 메뉴 권한은 화면에서 조정
- 🔒 **심의 잠금(Case Lock)·감사로그**: 관리자 간 동시 심의 충돌을 막고, 주요 행위를 시스템 감사로그에 기록
- 🖨️ **감사 이관 보고서 인쇄**: 사건 개요, 탐지 로그, 소명 내역, 심의 의견을 정리한 문서 출력·PDF 저장
- ⏰ **백그라운드 작업 스케줄링**: 기한 알림, 일일 통계, 주간 보고서, SIEM 수집 주기를 화면에서 변경 (재시작 불필요)
- 📧 **메일 알림**: SMTP 기본, Microsoft Graph(Outlook) 발송은 선택
- 🔍 **SIEM 연동 (선택)**: Microsoft Sentinel 수집·필드 매핑으로 케이스 자동 생성 (ELK·Splunk 수집기는 구현 예정)
- 🪪 **Entra ID 연동 (선택)**: SSO 로그인(ID 토큰 서명·대상·테넌트 검증), 사용자 동기화
- 🌐 **다국어**: 한국어 / 영어

---

## 🧱 기술 스택

| 구분 | 내용 |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy, Pydantic v2, Alembic, APScheduler, python-jose(JWT), msal |
| Frontend | React 18, TypeScript, Vite, TailwindCSS, TanStack Query, i18next, MSAL Browser |
| DB | SQLite (기본), PostgreSQL 이관 예정 |

Redis·Celery 같은 외부 큐 없이 백엔드 프로세스 안에서 스케줄러가 동작합니다. 상세 구조는 [`docs/SYSTEM_ARCHITECTURE.md`](docs/SYSTEM_ARCHITECTURE.md)를 참고하세요.

---

## 🚀 빠른 시작

명령은 모두 프로젝트 루트에서 실행합니다. 자세한 설치 절차(인증서 생성, 운영 배포)는 [`docs/INSTALL.md`](docs/INSTALL.md)와 [`docs/PRODUCTION.md`](docs/PRODUCTION.md)를 참고하세요.

```bash
# 1. 환경 변수 준비 (SECRET_KEY, ENCRYPTION_KEY는 반드시 새로 생성)
cp .env.example .env
cp frontend/.env.example frontend/.env

# 2. 백엔드
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements-dev.txt
alembic upgrade head
uvicorn backend.main:app --reload --host 0.0.0.0 --ssl-keyfile key.pem --ssl-certfile cert.pem

# 3. 프론트엔드 (다른 터미널)
cd frontend && npm install && npm run dev
```

- 백엔드: `https://localhost:8000` (API 문서 `/docs`), 프론트엔드: `https://localhost:5173`
- 자체 서명 인증서를 쓰는 경우 브라우저에서 `https://localhost:8000`을 먼저 열어 인증서를 허용해야 로그인이 됩니다
- 첫 실행 시 초기 관리자 계정, 기본 작업 스케줄, 메뉴 권한이 자동 생성됩니다

---

## 👤 초기 계정

| 계정 | 생성 시점 | 비고 |
|---|---|---|
| 시스템 관리자 | 서버 첫 실행 시 (사용자가 0명일 때) | `.env`의 `INITIAL_ADMIN_EMAIL` / `INITIAL_ADMIN_PASSWORD`. **운영 환경에서는 반드시 변경** |
| 데모 사용자 `demo@fleitlab.com` | 샘플 데이터 생성 시 | 시스템 관리자가 `POST /system/seed` 호출 시 샘플 케이스·통계와 함께 생성 (개발·시연용) |

---

## ☁️ 설치 후 선택 연동

설치 직후에는 자체 계정 로그인과 SMTP 메일만 동작하며 외부 연동은 모두 꺼져 있습니다.
연동 정보(테넌트·클라이언트 ID, 시크릿, 워크스페이스 ID)는 `.env`나 프론트엔드 빌드 변수에 넣지 않고, 화면에서 입력하면 DB에 암호화되어 저장됩니다. 저장 즉시 반영되며 재시작이나 재빌드가 필요 없습니다.

| 연동 | 메뉴 (권한) | 설정하면 켜지는 기능 |
|---|---|---|
| Microsoft Entra ID | `외부 연동 설정` (시스템관리자) | SSO 로그인, 사용자 동기화, Outlook 메일 발송 |
| Microsoft Sentinel | `SIEM 연동` (보안관리자·시스템관리자) | 주기적 인시던트 수집 → 케이스 자동 생성 |

▶️ Azure 앱 등록·권한 설정과 화면별 절차: [`docs/INTEGRATION_GUIDE.md`](docs/INTEGRATION_GUIDE.md)

---

## 🧪 테스트·빌드

```bash
python -m pytest backend/test_main.py -q   # 백엔드 테스트
cd frontend && npm run build               # 타입 검사 + 빌드
cd frontend && npm run lint

# DB 스키마 변경 시
alembic revision --autogenerate -m "변경 내용"   # 생성된 파일은 반드시 검토
alembic check

# API 변경 후 프론트 타입 동기화
python backend/scripts/generate_openapi.py && cd frontend && npm run generate-types
```

---

## 📚 문서

| 문서 | 내용 |
|---|---|
| [`docs/INSTALL.md`](docs/INSTALL.md) | 설치·실행·트러블슈팅 |
| [`docs/PRODUCTION.md`](docs/PRODUCTION.md) | 운영 배포 (Nginx) |
| [`docs/UPGRADE.md`](docs/UPGRADE.md) | 기존 버전 업그레이드 (Entra 설정 이전 포함) |
| [`docs/INTEGRATION_GUIDE.md`](docs/INTEGRATION_GUIDE.md) | Entra ID / Sentinel 선택 연동 |
| [`docs/CLARIFICATION_PROCESS.md`](docs/CLARIFICATION_PROCESS.md) | 소명 처리 워크플로우·알림 정책 |
| [`docs/SYSTEM_ARCHITECTURE.md`](docs/SYSTEM_ARCHITECTURE.md) | 아키텍처·보안 설계 |
| [`docs/API_GUIDE.md`](docs/API_GUIDE.md) | API 명세 |
| [`docs/DB_ERD.md`](docs/DB_ERD.md) | DB 스키마·관계 |

---

## 📁 프로젝트 구조

```text
backend/
  main.py                 앱 생성, 미들웨어, 라우터 등록, 초기 시딩·스케줄러
  core/                   설정, DB, 인증·권한, 암호화, 스케줄러, 메일
  modules/<도메인>/        API (auth, users, cases, submissions, reviews, siem, system, audit, reports, integrations)
  services/               SIEM 수집기 (BaseCollector → SentinelCollector)
  tasks/                  배치·메일·SIEM 동기화 작업
  migrations/             Alembic 마이그레이션
frontend/src/
  pages/ components/ services/ locales/{ko,en}/
docs/                     설계·운영 문서
```

---

## 👨‍💻 라이선스 (License)

This project is licensed under the MIT License.
Copyright (c) 2026 Fleit Lab (<contact@fleitlab.com>)
