import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { CheckCircle2, Loader2, Plug, Save, XCircle } from 'lucide-react';
import { integrationService } from '../services/integration.service';
import { EntraIntegration, EntraIntegrationUpdate, IntegrationTestResult } from '../types';
import { getApiErrorBody, getErrorMessage } from '../utils/error';
import TeamsSettingsCard from '../components/TeamsSettingsCard';

interface FormState {
    is_enabled: boolean;
    tenant_id: string;
    client_id: string;
    client_secret: string;
    mail_sender: string;
}

const toForm = (data: EntraIntegration): FormState => ({
    is_enabled: data.is_enabled,
    tenant_id: data.tenant_id || '',
    client_id: data.client_id || '',
    client_secret: '',
    mail_sender: data.mail_sender || '',
});

const inputClass = "w-full border-slate-300 rounded-lg shadow-sm p-2.5 border text-sm";
const labelClass = "block text-xs font-medium text-slate-500 mb-1";

/** 설치 후 관리자가 Entra ID 연동을 설정하는 화면 (DB 저장, 재시작·재빌드 불필요) */
const IntegrationSettings: React.FC = () => {
    const { t } = useTranslation();
    const [saved, setSaved] = useState<EntraIntegration | null>(null);
    const [form, setForm] = useState<FormState | null>(null);
    const [clearSecret, setClearSecret] = useState(false);
    const [saving, setSaving] = useState(false);
    const [testing, setTesting] = useState(false);
    const [result, setResult] = useState<IntegrationTestResult | null>(null);

    useEffect(() => {
        integrationService.getEntra()
            .then((data) => { setSaved(data); setForm(toForm(data)); })
            .catch((err: unknown) => setResult({ status: 'error', message: getApiErrorBody(err).detail || getErrorMessage(err) }));
    }, []);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!form) return;
        const { name, value, type, checked } = e.target;
        setForm({ ...form, [name]: type === 'checkbox' ? checked : value });
    };

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!form) return;
        setSaving(true);
        setResult(null);
        const payload: EntraIntegrationUpdate = {
            is_enabled: form.is_enabled,
            tenant_id: form.tenant_id,
            client_id: form.client_id,
            mail_sender: form.mail_sender,
        };
        // 시크릿은 새로 입력했을 때만 전송 (미전송 시 서버가 기존 값 유지)
        if (clearSecret) payload.client_secret = '';
        else if (form.client_secret) payload.client_secret = form.client_secret;
        try {
            const data = await integrationService.updateEntra(payload);
            setSaved(data);
            setForm(toForm(data));
            setClearSecret(false);
            setResult({ status: 'success', message: t('integrations.saved') });
        } catch (err: unknown) {
            setResult({ status: 'error', message: getApiErrorBody(err).detail || getErrorMessage(err) });
        } finally {
            setSaving(false);
        }
    };

    const handleTest = async () => {
        setTesting(true);
        setResult(null);
        try {
            setResult(await integrationService.testEntra());
        } catch (err: unknown) {
            setResult({ status: 'error', message: getApiErrorBody(err).detail || getErrorMessage(err) });
        } finally {
            setTesting(false);
        }
    };

    if (!form) {
        return (
            <div className="flex justify-center py-20">
                {result ? <p className="text-red-600 text-sm">{result.message}</p> : <Loader2 className="w-8 h-8 animate-spin text-slate-400" />}
            </div>
        );
    }

    const redirectUri = `${window.location.origin}/auth-callback`;

    return (
        <div className="space-y-6 max-w-3xl">
            <div>
                <h1 className="text-2xl font-bold text-slate-900 flex items-center">
                    <Plug className="w-6 h-6 mr-2" />{t('integrations.title')}
                </h1>
                <p className="text-slate-500 mt-1">{t('integrations.description')}</p>
            </div>

            <form onSubmit={handleSave} className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-5">
                <div className="flex items-center justify-between">
                    <div>
                        <h2 className="text-lg font-semibold text-slate-900">{t('integrations.entra.title')}</h2>
                        <p className="text-sm text-slate-500">{t('integrations.entra.description')}</p>
                    </div>
                    <label className="flex items-center space-x-2 text-sm font-medium text-slate-700">
                        <input type="checkbox" name="is_enabled" checked={form.is_enabled} onChange={handleChange} className="h-4 w-4" />
                        <span>{t('integrations.entra.enabled')}</span>
                    </label>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label className={labelClass}>{t('integrations.entra.tenantId')}</label>
                        <input name="tenant_id" value={form.tenant_id} onChange={handleChange} className={inputClass}
                            placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" autoComplete="off" />
                    </div>
                    <div>
                        <label className={labelClass}>{t('integrations.entra.clientId')}</label>
                        <input name="client_id" value={form.client_id} onChange={handleChange} className={inputClass}
                            placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" autoComplete="off" />
                    </div>
                    <div>
                        <label className={labelClass}>{t('integrations.entra.clientSecret')}</label>
                        <input type="password" name="client_secret" value={form.client_secret} onChange={handleChange}
                            disabled={clearSecret} className={inputClass} autoComplete="new-password"
                            placeholder={saved?.client_secret_set ? t('integrations.entra.secretSet') : t('integrations.entra.secretOptional')} />
                        {saved?.client_secret_set && (
                            <label className="mt-1 flex items-center space-x-1 text-xs text-slate-500">
                                <input type="checkbox" checked={clearSecret} onChange={(e) => setClearSecret(e.target.checked)} />
                                <span>{t('integrations.entra.clearSecret')}</span>
                            </label>
                        )}
                    </div>
                    <div>
                        <label className={labelClass}>{t('integrations.entra.mailSender')}</label>
                        <input name="mail_sender" value={form.mail_sender} onChange={handleChange} className={inputClass}
                            placeholder="security@company.com" autoComplete="off" />
                    </div>
                </div>

                <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-xs text-slate-600 space-y-1">
                    <p className="font-semibold text-slate-700">{t('integrations.entra.guideTitle')}</p>
                    <p>{t('integrations.entra.guideRedirect')} <code className="bg-white px-1 rounded border">{redirectUri}</code></p>
                    <p>{t('integrations.entra.guideSso')}</p>
                    <p>{t('integrations.entra.guideSync')}</p>
                    <p>{t('integrations.entra.guideMail')}</p>
                </div>

                {result && (
                    <div className={`flex items-start p-3 rounded-lg text-sm ${result.status === 'success' ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'}`}>
                        {result.status === 'success' ? <CheckCircle2 className="w-4 h-4 mr-2 mt-0.5 shrink-0" /> : <XCircle className="w-4 h-4 mr-2 mt-0.5 shrink-0" />}
                        <span>{result.message}</span>
                    </div>
                )}

                <div className="flex justify-end space-x-2">
                    <button type="button" onClick={handleTest} disabled={testing || saving}
                        className="flex items-center px-4 py-2 border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 transition disabled:opacity-50">
                        {testing ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Plug className="w-4 h-4 mr-2" />}
                        {t('integrations.test')}
                    </button>
                    <button type="submit" disabled={saving}
                        className="flex items-center px-4 py-2 bg-sky-600 text-white rounded-lg hover:bg-sky-700 transition disabled:opacity-50">
                        {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                        {t('common.save')}
                    </button>
                </div>
                <p className="text-xs text-slate-400 text-right">{t('integrations.testHint')}</p>
            </form>

            <TeamsSettingsCard />
        </div>
    );
};

export default IntegrationSettings;
