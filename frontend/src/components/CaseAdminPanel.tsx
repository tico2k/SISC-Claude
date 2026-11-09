import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { History, Lock, Unlock, Loader2 } from 'lucide-react';
import { caseService } from '../services/case.service';
import { Case, EmployeeHistory } from '../types';
import { getApiErrorBody, getErrorMessage } from '../utils/error';

interface CaseAdminPanelProps {
    cse: Case;
    onUpdated: () => void;
}

const STATUS_KEYS: Record<string, string> = {
    '미확인': 'cases.status.unconfirmed', '요청': 'cases.status.requested', '제출': 'cases.status.submitted',
    '승인': 'cases.status.approved', '반려': 'cases.status.rejected', '종결': 'cases.status.closed',
};

/** 관리자·감사팀 전용: 같은 직원의 과거 케이스 이력(반복 위반 판단)과 증거 보존 지정 */
const CaseAdminPanel: React.FC<CaseAdminPanelProps> = ({ cse, onUpdated }) => {
    const { t } = useTranslation();
    const [history, setHistory] = useState<EmployeeHistory | null>(null);
    const [holdReason, setHoldReason] = useState('');
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        setHistory(null);
        caseService.getEmployeeHistory(cse.case_id)
            .then(setHistory)
            .catch(() => setHistory(null));
    }, [cse.case_id]);

    const toggleHold = async () => {
        setSaving(true);
        setError('');
        try {
            await caseService.setLegalHold(cse.case_id, !cse.legal_hold, cse.legal_hold ? undefined : holdReason);
            setHoldReason('');
            onUpdated();
        } catch (err: unknown) {
            setError(getApiErrorBody(err).detail || getErrorMessage(err));
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* 직원 이력 */}
            <div className="bg-white rounded-2xl border border-slate-100 p-6 shadow-sm">
                <h3 className="text-base font-black text-slate-900 mb-4 flex items-center">
                    <History className="w-5 h-5 mr-2 text-slate-500" />
                    {t('cases.admin.historyTitle')}
                </h3>
                {!history ? (
                    <Loader2 className="w-5 h-5 animate-spin text-slate-300" />
                ) : history.total === 0 ? (
                    <p className="text-sm text-slate-500">{t('cases.admin.historyEmpty')}</p>
                ) : (
                    <>
                        <div className="grid grid-cols-3 gap-2 mb-4">
                            <div className="bg-slate-50 rounded-lg p-3 text-center">
                                <div className="text-xs text-slate-500">{t('cases.admin.historyTotal')}</div>
                                <div className="text-xl font-black text-slate-900">{history.total}</div>
                            </div>
                            <div className={`rounded-lg p-3 text-center ${history.rejected > 0 ? 'bg-red-50' : 'bg-slate-50'}`}>
                                <div className="text-xs text-slate-500">{t('cases.admin.historyRejected')}</div>
                                <div className={`text-xl font-black ${history.rejected > 0 ? 'text-red-600' : 'text-slate-900'}`}>{history.rejected}</div>
                            </div>
                            <div className={`rounded-lg p-3 text-center ${history.disciplinary > 0 ? 'bg-red-100' : 'bg-slate-50'}`}>
                                <div className="text-xs text-slate-500">{t('cases.admin.historyDisciplinary')}</div>
                                <div className={`text-xl font-black ${history.disciplinary > 0 ? 'text-red-700' : 'text-slate-900'}`}>{history.disciplinary}</div>
                            </div>
                        </div>
                        <ul className="divide-y divide-slate-100 max-h-48 overflow-y-auto text-sm">
                            {history.recent.map((c) => (
                                <li key={c.case_id} className="py-2 flex items-center justify-between gap-2">
                                    <span className="truncate text-slate-700">
                                        <span className="text-slate-400 mr-1">#{c.case_id}</span>{c.rule_title}
                                    </span>
                                    <span className="shrink-0 text-xs text-slate-500">
                                        {STATUS_KEYS[c.case_status] ? t(STATUS_KEYS[c.case_status]) : c.case_status}{c.case_result ? ` · ${c.case_result}` : ''} · {new Date(c.created_at).toLocaleDateString()}
                                    </span>
                                </li>
                            ))}
                        </ul>
                    </>
                )}
            </div>

            {/* 증거 보존 */}
            <div className="bg-white rounded-2xl border border-slate-100 p-6 shadow-sm">
                <h3 className="text-base font-black text-slate-900 mb-2 flex items-center">
                    <Lock className="w-5 h-5 mr-2 text-slate-500" />
                    {t('cases.admin.legalHoldTitle')}
                </h3>
                <p className="text-xs text-slate-500 mb-4">{t('cases.admin.legalHoldDesc')}</p>
                {cse.anonymized_at ? (
                    <p className="text-sm text-slate-500">{t('cases.admin.anonymizedNotice', { date: new Date(cse.anonymized_at).toLocaleDateString() })}</p>
                ) : cse.legal_hold ? (
                    <div className="space-y-3">
                        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-800">
                            <strong>{t('cases.admin.legalHoldOn')}</strong>
                            {cse.legal_hold_reason && <p className="mt-1 text-xs">{cse.legal_hold_reason}</p>}
                        </div>
                        <button onClick={toggleHold} disabled={saving}
                            className="flex items-center px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50">
                            <Unlock className="w-4 h-4 mr-2" />{t('cases.admin.legalHoldRelease')}
                        </button>
                    </div>
                ) : (
                    <div className="space-y-3">
                        <input value={holdReason} onChange={(e) => setHoldReason(e.target.value)}
                            placeholder={t('cases.admin.legalHoldReasonPlaceholder')}
                            className="w-full border border-slate-300 rounded-lg p-2.5 text-sm" />
                        <button onClick={toggleHold} disabled={saving || !holdReason.trim()}
                            className="flex items-center px-3 py-2 bg-amber-600 text-white rounded-lg text-sm hover:bg-amber-700 disabled:opacity-50">
                            <Lock className="w-4 h-4 mr-2" />{t('cases.admin.legalHoldSet')}
                        </button>
                    </div>
                )}
                {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
            </div>
        </div>
    );
};

export default CaseAdminPanel;
