# Fleit InsiderGuard - SICS (Security Incident Clarification System)

**내부자 위협 탐지 및 소명 관리 시스템 (v2.1.0)**

Fleit InsiderGuard는 SIEM(Security Information and Event Management)에서 탐지된 내부 보안 인시던트에 대해 관련 임직원에게 사유를 묻고, 보안 부서에서 소명 자료를 통합 검토할 수 있도록 심의 프로세스를 지원하는 엔터프라이즈 통합 관리 시스템입니다.

---

## 📋 핵심 주요 기능 (v2.1.0 기준)

- 🔍 **SIEM 지능형 연동**: Sentinel, Splunk, ELK 등 다양한 이기종 SIEM 경고를 동적으로 수집하고 매핑
- ⚖️ **반려(Rejection) 3대 워크플로우**: 단순 반려를 넘어 **재소명(유형 A)**, **보안교육/준수서약(유형 B)**, **징계/감사이관(유형 C)** 으로 체계화된 후속 조치 지원
- 🖨️ **감사 이관 보고서 원클릭 인쇄**: 중대 위반 의심 건 이관 시 사건 개요, 탐지 로그, 소명 내역, 심의 의견이 완벽히 정리된 표준 공문서 출력/PDF 저장 지원
- 🔐 **역할 기반 강력한 데이터 격리 (RBAC)**: 일반 사용자는 미검토(`UNCLASSIFIED`) 및 종결(`CLOSE`) 건이 API와 UI 모두에서 원천 차단되며, 전사 트렌드 통계 위젯도 격리
- 🧭 **스마트 네비게이션 & UI/UX 최적화**: 대시보드 행 클릭 시 역할별 다이렉트 화면 이동(사용자는 `/cases/{id}`, 관리자는 `/reviews?caseId={id}`), 상단 '대시보드로 돌아가기' 이전 문맥 보존
- 🎛️ **다중 상태(OR) 필터링 & 일괄 초기화**: 복수 상태 뱃지 동시 선택(예: `[요청]` + `[반려]`) 및 1초 초기화 버튼(`RotateCcw`)
- 🌐 **완벽한 다국어(i18n) 시스템**: 한국어/영어 전 화면 지원, 테이블 헤더 너비 최적화 및 보안 관제 표준 용어(`Medium`) 준수
- ⏰ **동적 백그라운드 스케줄링**: `APScheduler`를 DB와 연동하여 웹 UI에서 별도 서버 재시작 없이 자유롭게 **로그 수집/보고서/알림 크론(Cron) 주기** 조작
- 📧 **Enterprise 이메일 통합**: Microsoft Graph API를 이용한 Outlook 계정 연동 및 자동화 알림 템플릿 최적화
- 📊 **실시간 통계 및 실감형 시드 데이터**: 200건의 SIEM 케이스, 20일 통계, 5주 보고서 및 데모 사용자(`demo@fleitlab.com`) 즉시 지원

---

## 🏗️ 시스템 아키텍처

Fleit InsiderGuard는 최신 아키텍처 트렌드에 따라 외부 의존성(Redis/Celery 등)을 과감히 제거하고 **웹/서버 In-Process 비동기 태스크** 기반으로 극도의 경량화 생태계를 달성했습니다.

▶️ **상세 아키텍처 및 기술 스택 안내는 [`docs/SYSTEM_ARCHITECTURE.md`](docs/SYSTEM_ARCHITECTURE.md)를 참조하십시오.**

---

## 🚀 설치 및 실행 가이드

Fleit InsiderGuard v2.1.0은 **Zero-Config-Seed 환경**을 제공합니다. 애플리케이션 가동 시 초기 어드민 계정, 초기 동적 스케줄 탭, 사이드바 RBAC 권한이 자동으로 생성(Seeding)되므로 별도의 복잡한 스크립트 실행이 필요 없습니다.

▶️ **로컬 개발서버 및 엔터프라이즈 환경 구축 방법은 [`docs/INSTALL.md`](docs/INSTALL.md) 및 [`docs/PRODUCTION.md`](docs/PRODUCTION.md)를 확인하십시오.**

---

## 🚦 보안 프로세스 흐름 (Clarification Process)

임직원의 소명을 처리하는 전체 라이프사이클(인시던트 탐지 -> 초기검토 -> 소명요청 -> 심의 및 반려 3대 워크플로우 -> 최종종결)에 대한 상세 시스템 통제 규정은 개별 문서로 분리 관리합니다.

▶️ **소명 처리 워크플로우 및 자동 알림 정책은 [`docs/CLARIFICATION_PROCESS.md`](docs/CLARIFICATION_PROCESS.md)를 참조하십시오.**

---

## 🔌 API 가이드 및 데이터베이스 명세

- 프론트엔드와 백엔드 간의 통신 규약과 TypeScript 자동화 설계 방침은 ▶️ **[`docs/API_GUIDE.md`](docs/API_GUIDE.md)**
- SQLite 및 PostgreSQL 이관에 대비한 데이터베이스 스키마 및 외래키 참조 관계는 ▶️ **[`docs/DB_ERD.md`](docs/DB_ERD.md)**

---

## 📦 초기 계정 안내

시스템 부트스트랩 및 시딩 시 다음 계정들을 기본 제공합니다:

1. **최고 시스템 관리자 계정**:
   - **ID (Email)**: `system@fleitlab.com`
   - **Password**: `password123`
   - *권한*: 전사 케이스 심의, 감사 보고서 출력, 시스템 설정, RBAC 및 스케줄링 관리
2. **일반 임직원 데모 계정**:
   - **ID (Email)**: `demo@fleitlab.com`
   - **Password**: `password123`
   - *권한*: 본인에게 배정된 4가지 상태(`요청`, `제출`, `승인`, `반려`) 케이스 확인 및 소명서 작성/제출

▶️ **기존 구 버전 사용자의 마이그레이션 절차는 [`docs/UPGRADE.md`](docs/UPGRADE.md)를 따라 순차적으로 진행해 주세요.**

---

## ☁️ 시스템 연계 (Azure / Entra ID)

메일 발송 및 Single Sign-On (SSO)을 위해 Microsoft Graph API와 Entra ID 구성이 필요한 조직의 경우 하단의 설정 가이드라인을 따르십시오.

▶️ **Azure 포털 권한 등록 및 Microsoft 플랫폼 연계 방안은 [`docs/azure_setup_guide.md`](docs/azure_setup_guide.md)에 기술되어 있습니다.**

---

## 👨‍💻 라이선스 (License)

This project is licensed under the MIT License.
Copyright (c) 2026 Fleit Lab (<contact@fleitlab.com>)
