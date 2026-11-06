# Azure 서비스 설정 가이드 (Azure Setup Guide)

이 문서는 SICS 시스템에서 **Entra ID(Azure AD) 로그인** 및 **Outlook 메일 발송(Graph API)** 기능을 사용하기 위한 Azure Portal 설정 방법을 설명합니다.

---

## 1. Entra ID 연계 (SSO 로그인 설정)

SICS 시스템에 Microsoft 계정으로 로그인하기 위한 설정입니다.

### 1.1 애플리케이션 등록

1. [Azure Portal](https://portal.azure.com)에 접속하여 **Microsoft Entra ID** 서비스로 이동합니다.
2. 좌측 메뉴에서 **앱 등록(App registrations)** -> **새 등록(New registration)**을 클릭합니다.
3. **이름**: `SICS-Web-App` (식별 가능한 이름)
4. **지원되는 계정 유형**: 이 조직 디렉터리의 계정만(단일 테넌트) 선택
5. **리디렉션 URI (선택 사항)**:
   - 유형: `SPA` (Single Page Application)
   - URI: `https://localhost:5173/auth-callback` (운영 환경에서는 실제 도메인 주소로 입력)
6. **등록**을 클릭합니다.

### 1.2 인증 정보 확보

등록 완료 후 **개요(Overview)** 화면에서 다음 값을 복사하여 `.env` 파일에 기록합니다.

- **애플리케이션(클라이언트) ID** -> `ENTRA_CLIENT_ID`
- **디렉터리(테넌트) ID** -> `ENTRA_TENANT_ID`

### 1.3 클라이언트 암호 생성

1. 좌측 메뉴의 **인증서 및 암호(Certificates & secrets)** -> **새 클라이언트 암호(New client secret)**를 클릭합니다.
2. 설명과 만료 기간을 설정한 후 **추가**를 클릭합니다.
3. 생성된 암호의 **값(Value)**을 복사하여 `.env`의 `ENTRA_CLIENT_SECRET`에 기록합니다. (비밀값은 생성 시점에만 확인할 수 있으므로 즉시 백업하세요.)

---

## 2. Outlook 메일 발송 설정 (Microsoft Graph API)

시스템에서 소명 요청 메일을 발송하기 위한 API 권한 설정입니다.

### 2.1 API 권한 부여

1. 등록한 앱의 좌측 메뉴에서 **API 권한(API permissions)** -> **권한 추가(Add a permission)**를 클릭합니다.
2. **Microsoft Graph**를 선택합니다.
3. **애플리케이션 권한(Application permissions)**을 선택합니다. (사용자 로그인 없이 시스템이 발송해야 하므로 필수)
4. `Mail.Send` 권한을 검색하여 체크하고 **권한 추가**를 클릭합니다.

### 2.2 관리자 동의(Admin Consent) 완료

1. **API 권한** 화면에서 추가된 `Mail.Send` 권한 옆에 "상태: ...에 대해 부여되지 않음" 경고가 뜹니다.
2. 상단의 **[사용자조직]에 대해 관리자 동의 부여(Grant admin consent for [Org])** 버튼을 클릭합니다.
3. 상태가 초록색 체크 표시(**부여됨**)로 바뀌었는지 확인합니다.

### 2.3 .env 환경 변수 최종 설정

메일을 발송할 실제 공용 사함함 주소를 입력합니다.

```env
# 이메일 전송 방식
MAIL_SENDER_TYPE=OUTLOOK
ENABLE_EMAIL_NOTIFICATIONS=true

# 메일 발송용 공용 계정 (실제 Outlook 사함함이 있는 계정)
GRAPH_MAIL_SENDER=security@yourcompany.com
```

---

## 3. 요약 및 주의사항

> [!IMPORTANT]
>
> - **권한 유형**: 반드시 '위임된 권한'이 아닌 **'애플리케이션 권한'**으로 `Mail.Send`를 설정해야 백그라운드 태스크에서 메일이 정상 발송됩니다.
> - **URL 정합성**: Azure Portal에 등록된 리디렉션 URI와 앱의 `.env` 내 `ENTRA_REDIRECT_URI`는 정확히 일치해야 로그인 에러가 발생하지 않습니다.
