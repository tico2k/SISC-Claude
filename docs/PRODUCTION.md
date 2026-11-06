# SICS 프로덕션 배포 가이드 (Nginx 기반)

본 문서는 **Fleit InsiderGuard SICS**를 운영 환경(Production)에서 Nginx를 사용하여 안정적으로 배포하는 방법을 안내합니다.

---

## 1. 개요 (Overview)

운영 환경에서는 다음과 같은 구조로 배포하는 것을 권장합니다:

- **Nginx**: 리버스 프록시(Reverse Proxy) 및 정적 파일 서버 역할. SSL 종료(Termination) 처리.
- **Frontend (React)**: `npm run build`를 통해 생성된 정적 파일들을 Nginx가 직접 서빙.
- **Backend (FastAPI)**: Gunicorn과 Uvicorn Worker를 조합하여 멀티 프로세스로 실행.

---

## 2. 프론트엔드 빌드 (Frontend Build)

프론트엔드 소스 코드를 최적화된 정적 파일로 빌드합니다.

1. `frontend/.env` 파일의 `VITE_API_URL`을 실제 도메인 주소로 설정합니다.

    ```env
    VITE_API_URL=https://your-domain.com
    ```

2. 빌드 명령어를 실행합니다.

    ```bash
    cd frontend
    npm install --legacy-peer-deps
    npm run build
    ```

3. 생성된 `frontend/dist` 디렉토리의 경로를 기억해 둡니다. (Nginx 설정 시 필요)

---

## 3. 백엔드 실행 (Backend Execution)

운영 환경에서는 `uvicorn` 단독 실행보다는 `gunicorn`을 관리자(Process Manager)로 사용하는 것이 안정적입니다.

1. **필요 패키지 설치**:

    ```bash
    pip install gunicorn
    ```

2. **Gunicorn으로 실행**:
    프로젝트 루트에서 다음 명령어를 실행합니다. (Worker 수는 CPU 코어 수에 맞춰 조절)

    ```bash
    gunicorn backend.main:app \
      --workers 4 \
      --worker-class uvicorn.workers.UvicornWorker \
      --bind 127.0.0.1:8000 \
      --access-logformat '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"' \
      --access-logfile logs/access.log \
      --error-logfile logs/error.log
    ```

    *참고: SSL은 Nginx에서 처리하므로 백엔드는 HTTP(127.0.0.1)로 바인딩합니다.*

---

## 4. Nginx 설정 (Nginx Configuration)

Nginx를 설치하고 아래와 같이 설정 파일을 작성합니다. (`/etc/nginx/sites-available/sics`)

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # HTTP를 HTTPS로 리다이렉트 (권장)
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL 인증서 설정 (공인 인증서 경로)
    ssl_certificate     /path/to/fullchain.pem;
    ssl_certificate_key /path/to/privkey.pem;

    # 보안 설정 (선택 사항이지만 권장)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers on;

    # 1. 프론트엔드 정적 파일 서빙
    location / {
        root /path/to/Fleit_InsiderGuard/frontend/dist; # 실제 dist 경로로 수정
        index index.html;
        try_files $uri /index.html; # React Routing 지원
    }

    # 2. 백엔드 API 프록시
    location ~ ^/(api|docs|redoc|openapi.json) {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # 업로드 제한 설정
    client_max_body_size 50M;
}
```

---

## 5. 보안 및 최적화 팁

- **프로세스 관리**: 백엔드 서버를 `systemd` 서비스로 등록하여 서버 재부팅 시 자동 실행되도록 설정하십시오.
- **방화벽**: 서버의 80, 443 포트만 외부로 개방하고, 8000 포트는 로컬에서만 접근 가능하도록 설정하십시오.
- **로그 관리**: `logs/` 디렉토리에 생성되는 로그 파일을 `logrotate` 등을 사용하여 관리하십시오.

---

## 6. 도메인 없이 IP 주소로 운영하는 경우 (Tips)

운영 환경에서 도메인 주소 대신 고정 IP를 사용하는 경우 다음 사항을 확인하십시오.

1. **Nginx `server_name`**: IP 주소를 직접 입력하거나 `_` (Catch-all)를 사용합니다.

    ```nginx
    server_name 1.2.3.4; # 혹은 _
    ```

2. **공인 SSL 제약**:
    - **Let's Encrypt** 같은 무료 CA는 IP 주소에 대해 인증서를 발급하지 않습니다.
    - IP 주소로 운영할 경우 `Option A: 자가 서명 인증서`를 사용하거나, 유료 IP용 공인 인증서를 구매해야 합니다.
3. **프론트엔드 빌드**: `VITE_API_URL`에 IP 주소를 명시하여 빌드해야 합니다.

---
**최종 업데이트**: 2026-03-06 (v1.4.0 기준 동기화)
