# 시스템 업그레이드 가이드 (Upgrade Guide) - SICS 최신 버전

이 문서는 운영 중인 윈도우(Windows) 및 일반 환경의 SICS 시스템을 가장 최신의 배포 버전으로 업그레이드하는 절차를 설명합니다.
이번 업데이트에는 **다국어 (한국어/영어) 지원**, **동적 백그라운드 작업 스케줄링**, **역할별 메뉴 권한 동적 관리(RBAC)**, **주간 보안 보고서**, **Outlook 메일 연동(Graph API)** 기능 등이 대폭 추가/개선되었습니다.

---

## ⚠️ 주의사항 및 사전 준비

- **데이터베이스 백업**: 업그레이드를 시작하기 전에 현재 사용 중인 데이터베이스 파일(`sqlite:///./sql_app.db` 등)을 반드시 백업하십시오.
- **설정 파일 백업**: 환경 변수가 저장된 `.env` 파일을 복사하여 안전한 곳에 보관하세요.
- **Azure AD 권한 설정**: 이메일 발송 기능을 사용하는 경우, Azure Portal에서 **Mail.Send (Application)** 권한을 부여하고 관리자 동의를 해야 합니다. (상세 내용은 [Azure 설정 가이드](./azure_setup_guide.md) 참조)

---

## 1. 코드 업데이트 (Git Pull)

최신 소스 코드를 서버로 동기화합니다.

```powershell
# SICS 설치 디렉토리로 이동
cd C:\path\to\Fleit_InsiderGuard  # 또는 운영 환경 경로

# 최신 코드 동기화
git pull origin main
```

---

## 2. 의존성 및 환경 변수 업데이트

1. **의존성 설치**: 백엔드의 파이썬 패키지를 최신 상태로 업데이트합니다.

   ```powershell
   .\.venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **.env 환경 변수 확인 및 추가**: 기존 사용 중이던 `.env` 설정에 아래의 신규 항목들을 확인/추가합니다. (프론트엔드의 `환경 변수 관리` 메뉴에서도 수정 가능)

   ```env
   # 이메일 전송 방식 설정 (필요 시)
   MAIL_SENDER_TYPE=OUTLOOK
   ENABLE_EMAIL_NOTIFICATIONS=true

   # 메일 발송용 공용 계정 (실제 사서함이 존재하는 계정)
   GRAPH_MAIL_SENDER=your-email@company.com

   # 메일 본문 링크에 쓰는 프론트엔드 접속 주소 (미설정 시 CORS_ORIGINS의 첫 주소)
   # 웹 UI는 기존 키만 수정할 수 있으므로 이 키는 .env에 직접 추가
   APP_URL=https://sics.your-company.com

   # 기존 로그인용 Entra 정보 (없을 경우에만 입력)
   ENTRA_TENANT_ID=031e97aa-xxxx-xxxx-xxxx
   ENTRA_CLIENT_ID=3f329bad-xxxx-xxxx-xxxx
   ENTRA_CLIENT_SECRET=your-secret-key
   ```

---

## 3. DB 마이그레이션 (필수)

새롭게 추가된 백그라운드 스케줄 관리 및 역할별 권한 관리, 보고서 기능을 위한 데이터베이스 스키마를 현행화합니다.
아래 스크립트는 신규 테이블을 안전하게 생성하고 기본 구조를 패치합니다.

```powershell
# SICS 루트 디렉토리에서 실행 (앱 종료 상태 권장)
python -c "
from backend.core.database import engine
from backend.models import Base, WeeklyReport, DailyStatistic, SystemJobConfiguration, MenuPermission
from sqlalchemy import text

print('--- DB 스키마 현행화 시작 ---')

# 1. 보고서 신규 테이블(WeeklyReport) 생성
WeeklyReport.__table__.create(engine, checkfirst=True)

# 2. 통계 테이블(DailyStatistic) 생성을 위한 재구성 (지표 변경 대응 용도)
DailyStatistic.__table__.drop(engine, checkfirst=True)
DailyStatistic.__table__.create(engine, checkfirst=True)

# 3. 신규 백그라운드 작업 및 메뉴 모델 (SystemJobConfiguration, MenuPermission) 생성
SystemJobConfiguration.__table__.create(engine, checkfirst=True)
MenuPermission.__table__.create(engine, checkfirst=True)

# 4. SIEM 설정 테이블 패치 (cron_expression 컬럼 추가)
with engine.connect() as conn:
    try:
        conn.execute(text('ALTER TABLE siem_configuration ADD COLUMN cron_expression VARCHAR(50)'))
        conn.commit()
        print('siem_configuration 패치 성공.')
    except Exception as e:
        print(f'siem_configuration 패치 스킵 (오류 무시 가능, 이미 컬럼 존재 시): {e}')

print('--- DB 스키마 현행화 완료 ---')
"
```

> **참고**:
> `MenuPermission`과 `SystemJobConfiguration`의 초기 데이터 시딩(Default Settings)은 백엔드 앱(`main.py`)이 구동될 때 자동으로 처리됩니다.
> 사이드바 접근 권한이나 기본 스케줄(e.g., 밤 12시 배치 작업 등)은 앱 시작 직후 DB에 기본값으로 저장됩니다.

---

## 4. 과거 통계 데이터 재집계 (선택 사항)

과거의 운영 데이터가 보고서 지표 변경 사항에 맞게 재계산되어야 한다면 실행합니다.

```powershell
# 최근 15일치 일일 통계 및 최근 4주치 주간 보고서 재집계 스크립트 실행
python -c "
from datetime import datetime, timedelta
from backend.tasks.batch_tasks import generate_daily_statistics, generate_weekly_report

print('데이터 패치 시작...')
for i in range(15):
    target = datetime.now().date() - timedelta(days=i)
    generate_daily_statistics(target_date=target)

for i in range(4):
    target = datetime.now().date() - timedelta(days=i*7)
    generate_weekly_report(target_date=target)

print('데이터 패치 성공.')
"
```

---

## 5. 프론트엔드 빌드 (Nginx 등 배포 환경)

새로운 UI 디자인(사이드바 스크롤 최적화, 스케줄 수정 모달, 역할 권한 설정 그리드 등)이 제대로 반영되도록 프로덕션용 빌드를 진행합니다.

```powershell
cd frontend
npm install --legacy-peer-deps
npm run build
```

이후 생성된 `dist` 폴더를 Nginx 등의 웹 서버 경로에 맞게 매핑 또는 복사합니다 (로컬 구동 시 `npm run dev`).

---

## 6. 서비스 재시작 및 검증

모든 작업이 완료되면 SICS 백엔드와 프론트엔드 서비스를 재시작합니다.

1. **서비스 재시작**:
   - Backend: (운영 방식에 맞춰 `uvicorn backend.main:app`을 재실행하거나 윈도우 서비스/pm2 등 리스타트)
   - Frontend: 빌드된 웹서버 (Nginx) 재개.
2. **동적 작업 관리 확인**: '시스템관리자'로 로그인 후, 사이드바 하단의 **[백그라운드 작업]** 메뉴에서 모달을 이용한 스케줄 수정이 되는지 확인합니다. 크론 규칙은 DB에 저장되며 실시간으로 반영됩니다.
3. **역할(Role) 권한 검증**: '시스템관리자' 접속 시 **[메뉴 권한 설정]** 화면이 보이며, 역할에 따른 UI 메뉴 노출 숨김 처리가 동작하는지 직접 체크합니다.
4. **대시보드 노출**: 기타 추가된 위젯이나 그래프가 정상적으로 보이는지, 로그아웃 및 정보 버튼 등 UI의 고정 위치가 망가지지 않았는지 확인합니다.

---

## 7. v2.1.0 신규 기능 업그레이드 가이드 (2026-11-06)

v2.1.0은 **소명 반려 3대 워크플로우**, **일반 사용자 프로세스 및 데이터 격리**, **다중 상태(OR) 필터링**, **완벽한 다국어(i18n) 시스템**, **대용량 실감형 시드 데이터**가 포함된 주요 마일스톤입니다.

### 🌟 신규 주요 기능 요약

1. **소명 반려(Rejection) 후속 처리 3대 분기 및 감사 보고서 출력**:
   - 관리자가 반려 시 3가지 유형 선택 가능:
     - **유형 A (소명 불충분)**: 보완 사유 입력 후 재소명 기회 부여.
     - **유형 B (경미한 규정 위반)**: 보안 교육 이수 및 준수 서약서 제출 요구.
     - **유형 C (중대 위반 의심)**: 소명 기각, 징계 요청 및 감사팀 공식 이관.
   - **인쇄용 감사 이관 보고서(Audit Escalation Report)**: 유형 C 반려 시 사건 상세/로그/소명/심의 의견이 정리된 공문서 양식 팝업 호출 및 원클릭 브라우저 인쇄(`window.print()`).
2. **일반 사용자(USER) 프로세스 분리 및 강력한 데이터 격리 (방식 1)**:
   - 일반 임직원은 미검토(`UNCLASSIFIED`) 및 종결(`CLOSE`) 건이 API와 UI 모두에서 완전히 은닉됨.
   - 대시보드의 전사 트렌드 통계 차트 및 주간 리포트 위젯은 일반 사용자 세션에서 미노출.
   - 대시보드 사건 행 클릭 시 검토 화면이 아닌 직접 소명 작성 페이지(`/cases/{id}`)로 다이렉트 진입.
   - 상단 '대시보드로 돌아가기' 버튼을 통한 이전 문맥 유지 스마트 뒤로가기 지원.
   - '나의 소명 관리' 화면에서 본인 대상자 필터 제거 및 소명 요약(summary) 카드 표시.
3. **상태 다중 선택(OR) 필터링 & 초기화**:
   - 목록 상단 상태 뱃지 버튼 클릭 시 2개 이상의 상태(예: [요청] + [반려]) 동시 필터링 지원.
   - 우측 회전 화살표(초기화) 버튼을 클릭하여 필터 조건을 즉시 전체 해제.
4. **전 화면 다국어(i18n) 적용 & 관제 용어 표준화**:
   - 모든 컴포넌트(필터, 모달, 버튼, 알림, 에러 메시지) 한국어/영어 동기화.
   - 인시던트 위험도 표기를 `Normal` 대신 SIEM 표준인 `Medium(보통)`으로 통일.
   - 영문 모드 시 테이블 헤더 글자 겹침 방지(`w-[130px]`, `min-w-[1220px]`).
5. **실감형 엔터프라이즈 시드 데이터 엔진**:
   - 200건의 SIEM 케이스, 20일간의 연속 일일 통계, 5주간의 주간 보고서 자동 생성.
   - 데모 전용 계정 제공: `demo@fleitlab.com` / `password123` (상태별 20건 배정).

### 🛠️ v2.1.0 데이터베이스 시딩 실행

새로운 실감형 시드 데이터로 테스트 환경을 갱신하려면 백엔드 실행 상태에서 아래 API를 호출하거나 개발자 스크립트를 실행합니다:

```bash
# 시드 데이터 API 호출 (관리자 권한 필요)
curl -X POST "http://localhost:8000/system/seed" \
  -H "Authorization: Bearer <ADMIN_ACCESS_TOKEN>"
```

또는 백엔드 가상환경에서 직접 실행:

```bash
python -c "
from backend.core.database import SessionLocal
from backend.modules.system.seed_data import seed_realistic_data

db = SessionLocal()
try:
    result = seed_realistic_data(db)
    print('시드 데이터 생성 성공:', result)
finally:
    db.close()
"
```

---

**업그레이드 수고하셨습니다. 장애나 문의 사항 시 시스템 관리자에게 문의 바랍니다.**

---

## v2.1.0 이후: DB 마이그레이션(Alembic) 도입 (2026-11-06)

스키마는 이제 Alembic으로 관리합니다. 프로젝트 루트에서 실행하세요.

```bash
pip install -r backend/requirements.txt   # alembic 추가됨

# 마이그레이션 도입 이전에 만들어진 기존 DB (최초 1회)
alembic stamp 0001
alembic upgrade head

# 신규 설치
alembic upgrade head
```

- `0002` 마이그레이션은 초기 SQL 스크립트로 만들어진 레거시 인덱스 이름을 모델 기준으로 정렬합니다. 데이터는 변경하지 않습니다.
- DB 접속 정보는 `.env`의 `DATABASE_URL`을 사용합니다. (이전 버전은 이 값을 무시하고 `SICS_DATABASE_URL`만 읽었으며, 호환을 위해 `SICS_DATABASE_URL`이 있으면 우선 적용됩니다.)

