import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { CheckCircle2, Loader2, MessageSquare, Save, Send, XCircle } from 'lucide-react';
import { integrationService } from '../services/integration.service';
import { IntegrationTestResult, TeamsIntegration, TeamsIntegrationUpdate } from '../types';
import { getApiErrorBody, getErrorMessage } from '../utils/error';

/** 보안팀 Teams 채널 웹훅 설정 (외부 연동 설정 화면의 일부) */
const TeamsSettingsCard: React.FC = () => {
    const { t } = useTranslation();
    const [saved, setSaved] = useState<TeamsIntegration | null>(null);
    const [enabled, setEnabled] = useState(false);
    const [url, setUrl] = useState('');
    const [clearUrl, setClearUrl] = useState(false);
    const [busy, setBusy] = useState<'save' | 'test' | null>(null);
    const [result, setResult] = useState<IntegrationTestResult | null>(null);

    useEffect(() => {
        integrationService.getTeams()
            .then((data) => { setSaved(data); setEnabled(data.is_enabled); })
            .catch((err: unknown) => setResult({ status: 'error', message: getApiErrorBody(err).detail || getErrorMessage(err) }));
    }, []);

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        setBusy('save');
        setResult(null);
        const payload: TeamsIntegrationUpdate = { is_enabled: enabled };
        if (clearUrl) payload.webhook_url = '';
        else if (url) payload.webhook_url = url;
        try {
            const data = await integrationService.updateTeams(payload);
            setSaved(data);
            setEnabled(data.is_enabled);
            setUrl('');
            setClearUrl(false);
            setResult({ status: 'success', message: t('integrations.saved') });
        } catch (err: unknown) {
            setResult({ status: 'error', message: getApiErrorBody(err).detail || getErrorMessage(err) });
        } finally {
            setBusy(null);
        }
    };

    const handleTest = async () => {
        setBusy('test');
        setResult(null);
        try {
            setResult(await integrationService.testTeams());
        } catch (err: unknown) {
            setResult({ status: 'error', message: getApiErrorBody(err).detail || getErrorMessage(err) });
        } finally {
            setBusy(null);
        }
    };

    return (
        <form onSubmit={handleSave} className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-5">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-lg font-semibold text-slate-900 flex items-center">
                        <MessageSquare className="w-5 h-5 mr-2" />{t('integrations.teams.title')}
                    </h2>
                    <p className="text-sm text-slate-500">{t('integrations.teams.description')}</p>
                </div>
                <label className="flex items-center space-x-2 text-sm font-medium text-slate-700">
                    <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} className="h-4 w-4" />
                    <span>{t('integrations.teams.enabled')}</span>
                </label>
            </div>

            <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">{t('integrations.teams.webhookUrl')}</label>
                <input type="password" value={url} onChange={(e) => setUrl(e.target.value)} disabled={clearUrl}
                    autoComplete="off" className="w-full border-slate-300 rounded-lg shadow-sm p-2.5 border text-sm"
                    placeholder={saved?.webhook_url_set ? t('integrations.teams.urlSet') : 'https://...'} />
                {saved?.webhook_url_set && (
                    <label className="mt-1 flex items-center space-x-1 text-xs text-slate-500">
                        <input type="checkbox" checked={clearUrl} onChange={(e) => setClearUrl(e.target.checked)} />
                        <span>{t('integrations.teams.clearUrl')}</span>
                    </label>
                )}
            </div>

            <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-xs text-slate-600 space-y-1">
                <p>{t('integrations.teams.guide1')}</p>
                <p>{t('integrations.teams.guide2')}</p>
                <p>{t('integrations.teams.guide3')}</p>
            </div>

            {result && (
                <div className={`flex items-start p-3 rounded-lg text-sm ${result.status === 'success' ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'}`}>
                    {result.status === 'success' ? <CheckCircle2 className="w-4 h-4 mr-2 mt-0.5 shrink-0" /> : <XCircle className="w-4 h-4 mr-2 mt-0.5 shrink-0" />}
                    <span>{result.message}</span>
                </div>
            )}

            <div className="flex justify-end space-x-2">
                <button type="button" onClick={handleTest} disabled={busy !== null}
                    className="flex items-center px-4 py-2 border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 transition disabled:opacity-50">
                    {busy === 'test' ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Send className="w-4 h-4 mr-2" />}
                    {t('integrations.teams.test')}
                </button>
                <button type="submit" disabled={busy !== null}
                    className="flex items-center px-4 py-2 bg-sky-600 text-white rounded-lg hover:bg-sky-700 transition disabled:opacity-50">
                    {busy === 'save' ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                    {t('common.save')}
                </button>
            </div>
        </form>
    );
};

export default TeamsSettingsCard;
