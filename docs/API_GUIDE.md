# API 가이드 (API Guide)

Fleit InsiderGuard SICS의 주요 API 엔드포인트와 사용법을 설명합니다.

모든 API 문서는 서버 실행 후 Swagger UI (`/docs`) 및 ReDoc (`/redoc`)에서 대화형으로 테스트할 수 있습니다.

- **Swagger UI**: <https://localhost:8000/docs>
- **ReDoc**: <https://localhost:8000/redoc>

---

## 1. 인증 및 사용자 관리 (Authentication & Users)

모든 보호된 엔드포인트는 `Authorization: Bearer <토큰>` 헤더를 요구합니다.

### 1.1 로그인 (Local Login)

- **Endpoint**: `POST /login`
- **Content-Type**: `application/x-www-form-urlencoded`
- **Parameters**: `username` (이메일), `password`
- **Response**: `{"access_token": "...", "token_type": "bearer"}`
- **Security**: 분당 5회 속도 제한 (Brute-force 방지) 적용

### 1.2 Entra ID (SSO) 로그인

- **Endpoint**: `POST /login/entra`
- **Content-Type**: `application/json`
- **Body**: `{"access_token": "<Entra_Access_Token>"}`
- **Response**: SICS 자체 JWT Token

### 1.3 사용자 등록 (Register)

- **Endpoint**: `POST /register`
- **권한**: `SYSTEM_ADMIN` 전용
- **Body**: `{"user_email": "...", "password": "...", "user_name": "...", "role": "USER", "company": "...", "department": "..."}`

### 1.4 비밀번호 변경

- **Endpoint**: `POST /pwchange`
- **Body**: `{"old_password": "...", "new_password": "..."}`

### 1.5 로그인 기록 조회 및 생성

- **목록 조회**: `GET /loginhistory` (본인 기록 또는 관리자는 전체 조회 가능)
- **기록 생성**: `POST /loginhistory`

---

## 2. 케이스 관리 (Case Management)

### 2.1 케이스 목록 조회

- **Endpoint**: `GET /cases`
- **Parameters** (Query):
  - `skip` (기본: 0), `limit` (기본: 100)
  - **필터링**: `case_status`, `priority`, `case_type`, `start_date`, `end_date`
  - **검색**: `search` (제목, 요약, 탐지번호 `incident_num` 대상 통합 검색)
  - **정렬**: `sort_by`, `order` (asc/desc)

### 2.2 대시보드 통계 조회 (Synergistic Filtering)

- **Endpoint**: `GET /cases/stats`
- **Parameters** (Query): `case_status`, `priority`, `case_type`, `start_date`, `end_date`
- **Response**: 누적 필터링 기반의 전체 건수, 우선순위별, 상태별, 유형별 집계 데이터를 반환합니다.

### 2.3 일일 발생/처리 통계 조회

- **Endpoint**: `GET /cases/daily-stats`
- **Parameters**: `days` (조회 기간, 기본 14일)
- **Response**:

  ```json
  [
    {
      "date": "2026-03-01",
      "unclassified": 2, // 미확인
      "request": 5,      // 소명 요청
      "submit": 3,       // 소명 제출
      "reviewed": 10     // 검토 완료
    }
  ]
  ```

### 2.4 주간 보안 보고서 요약 조회

- **Endpoint**: `GET /cases/weekly-reports`
- **Parameters**: `limit` (가져올 주차 수, 기본 5주)
- **Response**:

  ```json
  [
    {
      "report_id": 1,
      "week_start": "2026-02-23",
      "week_end": "2026-03-01",
      "created": 15,
      "approved": 8,
      "rejected": 2,
      "generated_at": "2026-03-02 08:00:00"
    }
  ]
  ```

### 2.5 케이스 상세 및 생성 (이하 번호 밀림 생략)

- **상세 조회**: `GET /cases/{case_id}`
- **생성**: `POST /cases` (권한: `SECURITY_ADMIN`, `SYSTEM_ADMIN`)
  - **Body**: `{"siem_type": "SENTINEL", "rule_title": "...", "incident_num": "...", "summary": "...", "case_type": "...", "related_employee_id": 1, "priority": "HIGH", "due_date": "2023-12-31"}`

### 2.4 케이스 상태 변경 및 액션

- **소명 요청 발송**: `POST /cases/{case_id}/request`
  - 상태를 `REQUEST`로 변경하고 대상자에게 이메일 알림 발송
- **강제 종료**: `POST /cases/{case_id}/close`
  - 상태를 `CLOSE`로 변경 (검토 없이 강제 종료 시 사용)
- **상태 업데이트**: `PUT /cases/{case_id}/status`
  - **Body**: `{"status": "..."}`

### 2.5 케이스 잠금 (Case Locking)

동시 편집 및 검토 충돌을 방지하기 위한 기능입니다.

- **잠금 설정**: `POST /cases/{case_id}/lock` (진입 시 호출, 30분 후 자동 만료)
- **잠금 해제**: `POST /cases/{case_id}/unlock` (결재 또는 페이지 이탈 시 호출)

### 2.6 이력 조회

- **Endpoint**: `GET /cases/history`
- **Response**: 모든 케이스의 전체 이력 반환

---

## 3. 소명 및 검토 (Submission & Review)

### 3.1 소명 제출 (직원용)

- **Endpoint**: `POST /submissions`
- **Content-Type**: `multipart/form-data`
- **Parameters**:
  - `case_id`: 케이스 ID
  - `content`: 소명 내용
  - `files`: 증빙 첨부파일 리스트 (선택 항목)
- **주의**: 제출 완료 시 케이스 상태가 `SUBMIT`으로 변경되며 관리자에게 이메일 통지됨.

### 3.2 첨부 파일 다운로드

- **Endpoint**: `GET /attachments/{file_id}`
- **보안**: Path Traversal 검증 및 접속자 열람 권한 확인 후 스트림 반환.

### 3.3 검토 승인/반려 (관리자용)

- **Endpoint**: `POST /reviews`
- **권한**: `SECURITY_ADMIN`, `SYSTEM_ADMIN`, `AUDIT_TEAM`
- **Body**:

  ```json
  {
    "case_id": 123,
    "case_status": "APPROVE",  // APPROVE, REJECT
    "case_result": "JUSTIFIED", // 위반 없음 타당, 오탐지 등
    "comments": "소명 내용 분석 결과 정당한 업무로 인정됨"
  }
  ```

---

## 4. 시스템 관리 (System Management)

`SYSTEM_ADMIN` 전용 엔드포인트입니다.

### 4.1 환경 변수 관리 (.env)

시스템 및 프론트엔드 환경 변수들을 재시작 없이 동적으로(또는 최소 반영) 수정합니다.

- **목록 조회**: `GET /system/env`
- **값 업데이트**: `POST /system/env`
  - **Body**: `{"file": ".env", "key": "ENABLE_EMAIL_NOTIFICATIONS", "value": "true"}`

### 4.2 SIEM 연동 테스트

- **Endpoint**: `POST /siem/test-connection`
- **Body**: SIEM 설정 (Tenant ID, Client ID, Workspace ID, Secret 등)
- **보안**: 비밀번호 필드가 `********`로 전달되면 DB에 암호화되어 저장된 기존 시크릿을 자동으로 참조하여 테스트합니다.

### 4.3 시스템 초기화 및 샘플 데이터

- **전체 리셋**: `POST /system/reset`
  - 케이스, 소명, 검토 이력을 모두 삭제 (계정 유지)
- **샘플시드 생성**: `POST /system/seed`
  - 테스트용 가상 사용자 및 케이스 데이터를 생성

### 4.4 사용자 일괄 등록 (Bulk Upload)

- **Endpoint**: `POST /system/users/upload`
- **Content-Type**: `multipart/form-data`
- **Parameters**: `file` (.csv 또는 .json 파일), `format` (auto, csv, json)

### 4.5 백그라운드 작업 (System Jobs) 관리

시스템에서 실행 중인 APScheduler 스케줄을 동적으로 관리합니다.

- **목록 조회**: `GET /system/jobs` (DB에 저장된 활성/비활성 작업 목록)
- **작업 중지**: `POST /system/jobs/{job_id}/pause`
- **작업 재개**: `POST /system/jobs/{job_id}/resume`
- **수동 실행**: `POST /system/jobs/{job_id}/run`
- **스케줄 수정**: `PUT /system/jobs/{job_id}` (Body: `{"cron_expression": "..."}`)

### 4.6 역할별 메뉴 권한 (Menu Permissions) 관리

- **전체 권한 조회**: `GET /system/permissions`
- **일괄 권한 수정**: `POST /system/permissions/bulk-update`
  - **Body**: `[{"permission_id": 1, "is_visible": true}, ...]`
- **내 권한 조회**: `GET /system/permissions/my` (로그인한 사용자의 허용된 메뉴 목록 반환)

---

## 5. OpenAPI 명세 기반 타입 동기화

Fleit InsiderGuard 시스템은 백엔드 FastAPI 코드로부터 OpenAPI(Swagger) 명세를 추출해 프론트엔드의 TypeScript API Type을 자동 생성합니다.

새로운 엔드포인트나 파라미터를 추가한 경우, 다음 절차를 수행해야 프론트엔드에서 새로운 API를 안전하게 호출할 수 있습니다:

1. `PYTHONPATH=. .venv/bin/python backend/scripts/generate_openapi.py` (백엔드 `openapi.json` 추출)
2. `cd frontend && npm run generate-types` (추출된 명세를 TypeScript Interface로 변환)

---

**최종 수정**: 2026-03-06 (v1.4.0 시스템 작업 및 권한 API 추가 현행화)
