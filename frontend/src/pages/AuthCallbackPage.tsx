import React, { useEffect, useState, useRef } from 'react';
import { getMsalInstance, loginRequest } from '../config/msal';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { authService } from '../services/auth.service';
import { useAuth } from '../context/AuthContext';
import { getApiErrorBody, getErrorMessage } from '../utils/error';

const AuthCallbackPage: React.FC = () => {
    const { t } = useTranslation();
    const navigate = useNavigate();
    const { setToken } = useAuth();
    const [statusKey, setStatusKey] = useState<string>("waiting");
    const [errorMsg, setErrorMsg] = useState<string>("");
    const hasProcessed = useRef(false);

    useEffect(() => {
        if (hasProcessed.current) return;
        hasProcessed.current = true;
        setStatusKey("processingResponse");

        const processRedirect = async () => {
            // 연동 정보는 서버에서 받는다 (Entra가 비활성이면 SSO 처리 불가)
            const authConfig = await authService.getAuthConfig();
            if (!authConfig.allow_entra || !authConfig.entra_client_id || !authConfig.entra_tenant_id) {
                setStatusKey("generalError");
                setErrorMsg(t('auth.callback.entraDisabled'));
                return;
            }
            const instance = await getMsalInstance(authConfig.entra_client_id, authConfig.entra_tenant_id);
            const response = await instance.handleRedirectPromise();
            let idToken = response?.idToken;

            // redirect 응답에 토큰이 없다면 (캐시된 세션이거나 해시가 이미 소비된 경우)
            if (!idToken) {
                const allAccounts = instance.getAllAccounts();
                if (allAccounts.length > 0) {
                    setStatusKey("checkingSession");
                    try {
                        const silentResponse = await instance.acquireTokenSilent({
                            ...loginRequest,
                            account: allAccounts[0]
                        });
                        idToken = silentResponse.idToken;
                    } catch (error: unknown) {
                        console.error("Silent token acquisition failed:", error);
                        setErrorMsg(`Silent Token Error: ${getErrorMessage(error)}`);
                    }
                }
            }

            if (!idToken) {
                setStatusKey("noAuthInfo");
                setErrorMsg(t('auth.callback.noTokenDetail'));
                return;
            }

            setStatusKey("creatingBackendSession");
            try {
                const authData = await authService.loginEntra({ id_token: idToken });
                setToken(authData.access_token);
                setStatusKey("completed");
                setTimeout(() => navigate('/dashboard', { replace: true }), 500);
            } catch (apiError: unknown) {
                console.error("Backend auth failed:", apiError);
                setStatusKey("serverError");
                setErrorMsg(`Backend Error: ${getApiErrorBody(apiError).detail || getErrorMessage(apiError)}`);
            }
        };

        processRedirect().catch((error: unknown) => {
            console.error("MSAL redirect promise error:", error);
            setStatusKey("generalError");
            setErrorMsg(`MSAL Error: ${getErrorMessage(error)}`);
        });
    }, [navigate, setToken, t]);

    const getStatusText = (key: string) => {
        switch (key) {
            case "waiting": return t('auth.callback.waiting');
            case "processingResponse": return t('auth.callback.processingResponse');
            case "checkingSession": return t('auth.callback.checkingSession');
            case "creatingBackendSession": return t('auth.callback.creatingBackendSession');
            case "completed": return t('auth.callback.completed');
            case "serverError": return t('auth.callback.serverError');
            case "noAuthInfo": return t('auth.callback.noAuthInfo');
            case "generalError": return t('auth.callback.generalError');
            default: return key;
        }
    };

    return (
        <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
            <div className="text-center bg-slate-800 p-8 rounded-lg shadow-xl max-w-lg w-full">
                {statusKey !== "completed" && !errorMsg && (
                    <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-sky-500 mx-auto mb-4"></div>
                )}
                <h1 className="text-xl font-semibold text-white">{t('auth.callback.processingTitle')}</h1>
                <p className="text-slate-300 mt-4 text-lg">{getStatusText(statusKey)}</p>

                {errorMsg && (
                    <div className="mt-6 p-4 bg-red-900/50 border border-red-500 rounded text-left">
                        <p className="text-red-300 font-mono text-sm break-all">{errorMsg}</p>
                        <button
                            onClick={() => navigate('/login')}
                            className="mt-4 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded w-full transition-colors"
                        >
                            {t('auth.callback.backToLogin')}
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
};

export default AuthCallbackPage;
