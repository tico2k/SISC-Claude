import { Configuration, LogLevel } from "@azure/msal-browser";

export const msalConfig: Configuration = {
    auth: {
        clientId: import.meta.env.VITE_ENTRA_CLIENT_ID || "",
        authority: `https://login.microsoftonline.com/${import.meta.env.VITE_ENTRA_TENANT_ID || 'common'}`,
        redirectUri: window.location.origin + "/auth-callback",
        postLogoutRedirectUri: window.location.origin,
    },
    cache: {
        cacheLocation: "localStorage", // 팝업창과의 상태 공유를 위해 localStorage 사용 권장
    },
    system: {
        loggerOptions: {
            loggerCallback: (level: LogLevel, message: string, containsPii: boolean) => {
                if (containsPii) {
                    return;
                }
                switch (level) {
                    case LogLevel.Error:
                        console.error(message);
                        return;
                    case LogLevel.Info:
                        // console.info(message); // Too noisy in production
                        return;
                    case LogLevel.Verbose:
                        console.debug(message);
                        return;
                    case LogLevel.Warning:
                        console.warn(message);
                        return;
                }
            },
        },
    },
};

// Graph API 조회를 위한 기본 Scope
export const loginRequest = {
    scopes: ["User.Read"],
};
