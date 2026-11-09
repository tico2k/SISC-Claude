import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { Lock, Mail, Loader2, ChevronRight } from 'lucide-react';
import { getMsalInstance, loginRequest } from "../config/msal";
import { authService } from '../services/auth.service';
import LanguageSwitcher from '../components/LanguageSwitcher';
import { AuthConfig } from '../types';
import { getApiErrorBody, getErrorMessage } from '../utils/error';

const LoginPage: React.FC = () => {
    const { t } = useTranslation();
    const { login } = useAuth();
    const navigate = useNavigate();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [ssoLoading, setSsoLoading] = useState(false);
    const [config, setConfig] = useState<AuthConfig | null>(null);
    const [showLocal, setShowLocal] = useState(false);

    useEffect(() => {
        const fetchConfig = async () => {
            try {
                const authConfig = await authService.getAuthConfig();
                setConfig(authConfig);
                if (authConfig.allow_local) {
                    setShowLocal(true);
                }
            } catch (err) {
                console.error(t('login.errorFetchConfig'), err);
                // Fallback: 자체 로그인만 표시 (SSO는 서버가 연동 정보를 줄 때만 사용)
                setConfig({ allow_local: true, allow_entra: false, default_method: 'LOCAL' });
                setShowLocal(true);
            }
        };
        fetchConfig();
    }, []);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError('');
        try {
            await login({ user_email: email, password });
            navigate('/dashboard');
        } catch (err: unknown) {
            const detail = getApiErrorBody(err).detail;
            setError(detail || t('login.failMessage'));
        } finally {
            setLoading(false);
        }
    };

    const handleMicrosoftLogin = async () => {
        setSsoLoading(true);
        setError('');

        try {
            if (!config?.entra_client_id || !config?.entra_tenant_id) {
                throw new Error(t('login.errorStart'));
            }
            const instance = await getMsalInstance(config.entra_client_id, config.entra_tenant_id);
            // popup 대신 redirect 방식 사용
            await instance.loginRedirect({
                ...loginRequest,
                redirectStartPage: window.location.origin + '/auth-callback'
            });
            // loginRedirect는 즉시 반환되며, 페이지가 리다이렉션됩니다.
            // 이후 처리는 AuthCallbackPage에서 handleRedirectPromise()로 수행됩니다.
        } catch (err: unknown) {
            console.error("Entra ID login initiation failed", err);
            setError(getErrorMessage(err) || t('login.errorStart'));
            setSsoLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
            <div className="absolute top-4 right-4">
                <LanguageSwitcher />
            </div>
            <div className="w-full max-w-md bg-white/10 backdrop-blur-lg rounded-2xl shadow-xl overflow-hidden border border-white/20">
                <div className="p-8">
                    <div className="text-center mb-8">
                        <h1 className="text-3xl font-bold text-white mb-2">{t('login.title')}</h1>
                        <p className="text-slate-300">{t('login.subtitle')}</p>
                    </div>

                    <div className="space-y-6">
                        {/* Entra ID SSO Button */}
                        {config?.allow_entra && (
                            <button
                                type="button"
                                onClick={handleMicrosoftLogin}
                                disabled={ssoLoading}
                                className="w-full bg-white hover:bg-slate-100 text-slate-900 font-semibold py-3 px-4 rounded-lg transition-all duration-200 transform active:scale-95 disabled:opacity-50 flex items-center justify-center shadow-lg"
                            >
                                {ssoLoading ? (
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                ) : (
                                    <>
                                        <svg className="w-5 h-5 mr-3" viewBox="0 0 23 23">
                                            <path fill="#f3f3f3" d="M0 0h23v23H0z" />
                                            <path fill="#f35325" d="M1 1h10v10H1z" />
                                            <path fill="#81bc06" d="M12 1h10v10H12z" />
                                            <path fill="#05a6f0" d="M1 12h10v10H1z" />
                                            <path fill="#ffba08" d="M12 12h10v10H12z" />
                                        </svg>
                                        {t('login.ssoLogin')}
                                    </>
                                )}
                            </button>
                        )}

                        {/* Divider - Only shown when both options are available */}
                        {config?.allow_entra && showLocal && (
                            <div className="relative my-6">
                                <div className="absolute inset-0 flex items-center">
                                    <div className="w-full border-t border-slate-600"></div>
                                </div>
                                <div className="relative flex justify-center text-sm">
                                    <span className="px-2 bg-slate-800 text-slate-400">{t('login.or')}</span>
                                </div>
                            </div>
                        )}

                        {/* Local Login Form */}
                        {showLocal ? (
                            <form onSubmit={handleSubmit} className="space-y-6">
                                <div>
                                    <label className="block text-sm font-medium text-slate-300 mb-1.5">{t('login.email')}</label>
                                    <div className="relative">
                                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                            <Mail className="h-5 w-5 text-slate-400" />
                                        </div>
                                        <input
                                            type="email"
                                            value={email}
                                            onChange={(e) => setEmail(e.target.value)}
                                            required
                                            className="block w-full pl-10 pr-3 py-2.5 bg-slate-800/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent transition-all hover:bg-slate-800/70"
                                            placeholder="admin@example.com"
                                        />
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-slate-300 mb-1.5">{t('login.password')}</label>
                                    <div className="relative">
                                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                            <Lock className="h-5 w-5 text-slate-400" />
                                        </div>
                                        <input
                                            type="password"
                                            value={password}
                                            onChange={(e) => setPassword(e.target.value)}
                                            required
                                            className="block w-full pl-10 pr-3 py-2.5 bg-slate-800/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent transition-all hover:bg-slate-800/70"
                                            placeholder="••••••••"
                                        />
                                    </div>
                                </div>

                                {error && (
                                    <div className="bg-red-500/10 border border-red-500/50 text-red-200 text-sm p-3 rounded-lg text-center">
                                        {error}
                                    </div>
                                )}

                                <button
                                    type="submit"
                                    disabled={loading}
                                    className="w-full bg-sky-600 hover:bg-sky-500 text-white font-semibold py-3 px-4 rounded-lg transition-all duration-200 transform active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center shadow-lg shadow-sky-900/20"
                                >
                                    {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : t('login.signIn')}
                                </button>

                                {!config?.allow_local && (
                                    <button
                                        type="button"
                                        onClick={() => setShowLocal(false)}
                                        className="w-full text-xs text-slate-400 hover:text-slate-200 transition-colors"
                                    >
                                        {t('login.backToSso')}
                                    </button>
                                )}
                            </form>
                        ) : (
                            /* Admin Fallback Link when local login is disabled for general users */
                            !config?.allow_local && (
                                <div className="text-center">
                                    <button
                                        type="button"
                                        onClick={() => setShowLocal(true)}
                                        className="text-sm text-slate-400 hover:text-sky-400 transition-all flex items-center justify-center mx-auto group"
                                    >
                                        {t('login.localLogin')} <ChevronRight className="w-4 h-4 ml-0.5 group-hover:translate-x-1 transition-transform" />
                                    </button>
                                </div>
                            )
                        )}
                    </div>
                </div>
                <div className="bg-white/5 p-4 text-center border-t border-white/10">
                    <p className="text-xs text-slate-400">
                        &copy; 2026 Fleit InsiderGuard. All rights reserved.
                    </p>
                </div>
            </div>
        </div>
    );
};

export default LoginPage;
