import { Configuration, LogLevel, PublicClientApplication } from "@azure/msal-browser";

/**
 * Entra ID(MSAL) 설정은 빌드 변수가 아니라 서버(/config)에서 받아 실행 중에 만든다.
 * 설치 후 관리자가 연동을 설정하면 재빌드 없이 SSO가 동작한다.
 */
const buildConfig = (clientId: string, tenantId: string): Configuration => ({
    auth: {
        clientId,
        authority: `https://login.microsoftonline.com/${tenantId}`,
        redirectUri: window.location.origin + "/auth-callback",
        postLogoutRedirectUri: window.location.origin,
    },
    cache: {
        cacheLocation: "localStorage",
    },
    system: {
        loggerOptions: {
            loggerCallback: (level: LogLevel, message: string, containsPii: boolean) => {
                if (containsPii) return;
                if (level === LogLevel.Error) console.error(message);
                else if (level === LogLevel.Warning) console.warn(message);
            },
        },
    },
});

let cached: { key: string; instance: Promise<PublicClientApplication> } | null = null;

/** 같은 클라이언트/테넌트면 초기화된 인스턴스를 재사용 */
export const getMsalInstance = (clientId: string, tenantId: string): Promise<PublicClientApplication> => {
    const key = `${clientId}/${tenantId}`;
    if (!cached || cached.key !== key) {
        const instance = new PublicClientApplication(buildConfig(clientId, tenantId));
        cached = { key, instance: instance.initialize().then(() => instance) };
    }
    return cached.instance;
};

// 서버는 ID 토큰만 검증하므로 OIDC 기본 범위만 요청
export const loginRequest = {
    scopes: ["openid", "profile", "email"],
};
