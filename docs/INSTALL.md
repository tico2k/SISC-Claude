# SICS 설치 및 운영 가이드 (v1.4.0)

본 문서는 **Fleit InsiderGuard SICS (Security Incident Clarification System)**의 신규 설치 및 환경 설정 방법을 안내합니다.

**v1.4.0 업데이트 핵심 내역**:

- **동적 스케줄링 통합**: APScheduler가 데이터베이스와 직접 동기화되어 웹 UI에서 크론 탭 규칙을 동적으로 수정할 수 있습니다.
- **RBAC 메뉴 권한 관리 추가**: 사용자 역할별 접근 가능 메뉴가 데이터베이스에서 제어되며 서버 시작 시 기본 규칙이 자동 시딩됩니다.
- **환경 변수 관리 강화**: 프론트엔드 UI를 통한 직관적인 환경 변수 관리 및 감사 로그 기록 기능이 추가 되었습니다.
- **보안 가이드 최신화**: `SECRET_KEY` 및 `ENCRYPTION_KEY` 생성 방법을 명시하였습니다.

---

## Part 1. 신규 설치 가이드 (New Installation)

### 1.1 시스템 요구사항 (Prerequisites)

- **운영체제**: Windows (WSL2 권장), macOS, Linux
- **Python**: 3.12 이상
- **Node.js**: 18 이상 (20 LTS 권장)
- **버전 관리**: Git

### 1.2 저장소 복제 (Clone Repository)

```bash
git clone https://github.com/tico2k/SISC-Claude.git Fleit_InsiderGuard
cd Fleit_InsiderGuard
```

### 1.3 백엔드 설정 (FastAPI)

#### 1.3.1 가상 환경 생성 및 활성화

```bash
# Windows
python -m venv .venv
.\.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

#### 1.3.2 의존성 패키지 설치

```bash
pip install -r backend/requirements.txt
# 개발·테스트 환경은 pytest 등이 포함된 dev 의존성 설치
pip install -r backend/requirements-dev.txt
```

> 주의: 가상환경(`.venv`)은 다른 폴더에서 복사하지 말고 프로젝트 폴더에서 새로 생성하세요. 복사한 가상환경은 원래 폴더의 Python을 가리켜 패키지가 엉뚱한 곳에 설치됩니다.

#### 1.3.3 SSL 인증서 설정

SICS는 보안을 위해 HTTPS 통신이 필수입니다. 환경에 따라 아래 두 가지 옵션 중 하나를 선택하세요.

**Option A: 로컬/개발용 (자가 서명 인증서)**
로컬 개발 환경에서 빠르게 시작할 때 사용합니다. (브라우저 경고 발생)

```bash
python backend/generate_cert.py
```

**Option B: 로컬/개발용 (mkcert - 권장)**
브라우저의 "안전하지 않음" 경고를 없애고 "초록색 자물쇠"를 보고 싶을 때 사용합니다.

1. **mkcert 설치**:
    - **macOS**: `brew install mkcert`
    - **Windows**: `choco install mkcert` (Chocolatey 사용 시) 또는 `scoop install mkcert` (Scoop 사용 시)
    - **Linux**: 각 배포판의 패키지 매니저 사용
2. **로컬 CA 등록**: `mkcert -install` (Windows의 경우 관리자 권한 필요)
3. **인증서 생성**: 프로젝트 루트에서 `mkcert -key-file key.pem -cert-file cert.pem localhost 127.0.0.1 <서버_IP> ::1` 실행
    - *동일 망의 다른 PC에서 접속하려면 `<서버_IP>` 부분에 실제 사설 IP(예: 192.168.x.x)를 포함해야 합니다.*
4. **다른 PC에서 접속 시 (중요)**:
    - 서버 PC에서 `mkcert -CAROOT` 명령어로 CA 경로를 확인합니다.
    - 해당 경로의 `rootCA.pem` 파일을 접속하려는 다른 PC(클라이언트)로 복사합니다.
    - 클라이언트 PC에서 해당 파일을 '신뢰할 수 있는 루트 인증 기관'으로 등록해야 경고 없이 접속 가능합니다.

**Option C: 운영/공인 환경 (공인 인증서)**
 발급받은 공인 인증서를 사용하는 경우입니다.

1. **파일 준비**: 발급받은 인증서(`CRT`, `CER`)와 비밀키(`KEY`) 파일을 준비합니다.
2. **PEM 형식 변환 방법**:
    - **단순 확장자 변경**: 파일을 메모장(Text Editor)으로 열었을 때 `-----BEGIN CERTIFICATE-----`라는 문구로 시작한다면 이미 PEM 호환 형식입니다. 이 경우 단순히 파일 확장자를 `.crt`에서 `.pem`으로 수동 변경하면 됩니다.
    - **OpenSSL 명령어 사용 (변환이 필요한 경우)**:

        ```bash
        # CRT를 PEM으로 변환
        openssl x509 -in certificate.crt -out cert.pem -outform PEM
        
        # KEY를 PEM으로 변환
        openssl rsa -in device.key -out key.pem -outform PEM
        ```

3. **파일 배치**: 프로젝트 루트 디렉토리에 `cert.pem`, `key.pem`으로 이름을 맞춰 배치하거나, 절대 경로를 기억해 둡니다.
4. **Uvicorn 설정**: 아래 서버 실행 시 `--ssl-keyfile`과 `--ssl-certfile` 인자에 실제 파일 경로를 지정합니다.

#### 1.3.4 환경 변수 (`.env`) 설정

`.env.example` 파일을 복사하여 `.env`를 생성한 후, 각 섹션별 설정을 확인하세요.

```bash
cp .env.example .env
```

**주요 필수 설정 항목:**

1. **SECRET_KEY**: JWT 서명용. 아래 명령어로 생성하세요.
   - `python -c "import secrets; print(secrets.token_urlsafe(32))"`
2. **ENCRYPTION_KEY**: 데이터 암호화용. 아래 명령어로 생성하세요.
   - `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
3. **DATABASE_URL**: 기본값은 SQLite(`sqlite:///./sql_app.db`)입니다.

### 1.4 프론트엔드 설정 (React + Vite)

```bash
cd frontend
npm install --legacy-peer-deps
```

#### 1.4.1 타입 동기화 (최초 1회 필수)

백엔드 서버가 실행 중인 상태에서 API 명세를 TypeScript 타입으로 변환합니다.

```bash
npm run generate-types
```

---

## Part 2. 실행 및 운영 (Execution)

### 2.1 백엔드 서버 실행

```bash
# 루트 디렉토리에서 실행
uvicorn backend.main:app --reload --host 0.0.0.0 --ssl-keyfile key.pem --ssl-certfile cert.pem
```

> **참고**: v1.4.0부터 백엔드 서버가 구동될 때, 데이터베이스에 **초기 관리자 계정**, **기본 배치 작업 스케줄**, **기본 메뉴 접근 권한** 이 자동으로 생성(Seeding)됩니다. 최초 1회 실행 후 별도의 수동 시딩 작업이 불필요합니다.

### 2.2 프론트엔드 개발 서버 실행

```bash
cd frontend
npm run dev
```

**성공 확인**: `https://localhost:5173` 에 접속하여 로그인하면 완료됩니다.

---

## Part 4. 운영 환경 배포 (Production Deployment)

실제 서비스 운영 환경(Public/Production)에서 Nginx를 사용하여 배포하는 방법은 별도의 가이드 문서를 참조하세요.

- **[운영 환경 배포 가이드 (Nginx)](./PRODUCTION.md)**: 프론트엔드 빌드, Gunicorn 설정, Nginx 리버스 프록시 및 SSL 설정 방법을 포함합니다.

---

## Part 5. 트러블슈팅 (FAQ)

### Q. 브라우저에서 SSL 에러가 발생합니다

A. 로컬 개발 시 자가 서명 인증서를 사용하므로, 브라우저에서 `https://localhost:8000`에 접속하여 '위험을 감수하고 계속'을 한 번 클릭해 주어야 프론트엔드와 백엔드 간 통신이 허용됩니다.

### Q. 환경 변수 변경사항이 적용되지 않습니다

A. `.env` 파일을 직접 수정하거나 관리 페이지에서 저장한 후에는 백엔드 서버를 재시작해야 적용되는 항목이 있습니다 (예: DB 접속 URL, 포트 등).

### Q. 특정 라이브러리 임포트 에러가 발생합니다

A. 가상환경(`.venv`)이 활성화되어 있는지 확인하고, `pip install -r backend/requirements.txt`를 다시 실행해 보세요.

---
**최종 업데이트**: 2026-03-06 (v1.4.0 기준)
