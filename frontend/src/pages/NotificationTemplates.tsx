import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Eye, Loader2, Mail, RotateCcw, Save } from 'lucide-react';
import { notificationService } from '../services/notification.service';
import { NotificationPreview, NotificationTemplate } from '../types';
import { getApiErrorBody, getErrorMessage } from '../utils/error';

/** 알림 메일 템플릿 편집 (시스템관리자·보안관리자). 저장 즉시 이후 발송 메일에 적용 */
const NotificationTemplates: React.FC = () => {
    const { t } = useTranslation();
    const [templates, setTemplates] = useState<NotificationTemplate[]>([]);
    const [selectedKey, setSelectedKey] = useState<string | null>(null);
    const [subject, setSubject] = useState('');
    const [body, setBody] = useState('');
    const [preview, setPreview] = useState<NotificationPreview | null>(null);
    const [busy, setBusy] = useState<'save' | 'reset' | 'preview' | null>(null);
    const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);

    const selected = templates.find(tpl => tpl.template_key === selectedKey) || null;

    const select = (tpl: NotificationTemplate) => {
        setSelectedKey(tpl.template_key);
        setSubject(tpl.subject);
        setBody(tpl.body_html);
        setPreview(null);
        setMessage(null);
    };

    useEffect(() => {
        notificationService.getTemplates()
            .then((list) => {
                setTemplates(list);
                if (list.length > 0) select(list[0]);
            })
            .catch((err: unknown) => setMessage({ ok: false, text: getApiErrorBody(err).detail || getErrorMessage(err) }));
    }, []);

    const replaceTemplate = (updated: NotificationTemplate) => {
        setTemplates(prev => prev.map(tpl => tpl.template_key === updated.template_key ? updated : tpl));
        select(updated);
    };

    const run = async (action: 'save' | 'reset' | 'preview') => {
        if (!selected) return;
        if (action === 'reset' && !window.confirm(t('notifications.resetConfirm'))) return;
        setBusy(action);
        setMessage(null);
        try {
            if (action === 'preview') {
                setPreview(await notificationService.previewTemplate(selected.template_key, subject, body));
            } else if (action === 'save') {
                replaceTemplate(await notificationService.updateTemplate(selected.template_key, subject, body));
                setMessage({ ok: true, text: t('notifications.saved') });
            } else {
                replaceTemplate(await notificationService.resetTemplate(selected.template_key));
                setMessage({ ok: true, text: t('notifications.resetDone') });
            }
        } catch (err: unknown) {
            setMessage({ ok: false, text: getApiErrorBody(err).detail || getErrorMessage(err) });
        } finally {
            setBusy(null);
        }
    };

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-2xl font-bold text-slate-900 flex items-center">
                    <Mail className="w-6 h-6 mr-2" />{t('notifications.title')}
                </h1>
                <p className="text-slate-500 mt-1">{t('notifications.description')}</p>
            </div>

            <div className="flex flex-col lg:flex-row gap-6">
                <div className="lg:w-72 shrink-0 bg-white rounded-xl border border-slate-200 shadow-sm p-2 space-y-1 h-fit">
                    {templates.map(tpl => (
                        <button key={tpl.template_key} onClick={() => select(tpl)}
                            className={`w-full text-left px-3 py-2 rounded-lg text-sm transition
                                ${tpl.template_key === selectedKey ? 'bg-sky-50 text-sky-900 font-semibold' : 'hover:bg-slate-50 text-slate-700'}`}>
                            <div className="flex items-center justify-between">
                                <span>{tpl.name}</span>
                                {tpl.is_customized && (
                                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-700">{t('notifications.customized')}</span>
                                )}
                            </div>
                            <div className="text-[11px] text-slate-400 truncate">{tpl.description}</div>
                        </button>
                    ))}
                </div>

                {selected && (
                    <div className="flex-1 min-w-0 bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
                        <div>
                            <label className="block text-xs font-medium text-slate-500 mb-1">{t('notifications.subject')}</label>
                            <input value={subject} onChange={(e) => setSubject(e.target.value)}
                                className="w-full border border-slate-300 rounded-lg p-2.5 text-sm font-mono" />
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-slate-500 mb-1">{t('notifications.body')}</label>
                            <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={16} spellCheck={false}
                                className="w-full border border-slate-300 rounded-lg p-2.5 text-xs font-mono" />
                        </div>
                        <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-xs text-slate-600">
                            <p className="font-semibold mb-1">{t('notifications.variables')}</p>
                            <p className="font-mono break-words">{selected.variables.map(v => `{{ ${v} }}`).join('  ')}</p>
                            <p className="mt-2 text-slate-500">{t('notifications.syntaxHint')}</p>
                        </div>

                        {message && (
                            <div className={`p-3 rounded-lg text-sm ${message.ok ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'}`}>{message.text}</div>
                        )}

                        <div className="flex flex-wrap justify-end gap-2">
                            <button onClick={() => run('reset')} disabled={busy !== null || !selected.is_customized}
                                className="flex items-center px-4 py-2 border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 disabled:opacity-50 text-sm">
                                {busy === 'reset' ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <RotateCcw className="w-4 h-4 mr-2" />}
                                {t('notifications.reset')}
                            </button>
                            <button onClick={() => run('preview')} disabled={busy !== null}
                                className="flex items-center px-4 py-2 border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 disabled:opacity-50 text-sm">
                                {busy === 'preview' ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Eye className="w-4 h-4 mr-2" />}
                                {t('notifications.preview')}
                            </button>
                            <button onClick={() => run('save')} disabled={busy !== null}
                                className="flex items-center px-4 py-2 bg-sky-600 text-white rounded-lg hover:bg-sky-700 disabled:opacity-50 text-sm">
                                {busy === 'save' ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                                {t('common.save')}
                            </button>
                        </div>

                        {preview && (
                            <div className="border border-slate-200 rounded-lg overflow-hidden">
                                <div className="bg-slate-50 px-3 py-2 text-sm border-b border-slate-200">
                                    <span className="text-slate-500 mr-2">{t('notifications.subject')}:</span>{preview.subject}
                                </div>
                                {/* 스크립트가 실행되지 않도록 sandbox iframe으로 표시 (샘플 값으로 렌더링) */}
                                <iframe title="preview" sandbox="" srcDoc={preview.body_html} className="w-full h-[480px] bg-white" />
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

export default NotificationTemplates;
