import React, { useEffect, useState } from 'react';
import { systemService, AuditLog } from '../services/system.service';
import { useTranslation } from 'react-i18next';
import { Shield, Clock, Monitor, Download } from 'lucide-react';

const SystemLogs: React.FC = () => {
    const { t } = useTranslation();
    const [logs, setLogs] = useState<AuditLog[]>([]);
    const [loading, setLoading] = useState(true);
    const [exportStart, setExportStart] = useState('');
    const [exportEnd, setExportEnd] = useState('');
    const [exporting, setExporting] = useState(false);

    // 감사 제출용 CSV (기간 미지정 시 전체, 내보내기 행위도 감사로그에 기록됨)
    const handleExport = async () => {
        setExporting(true);
        try {
            await systemService.exportAuditLogs(exportStart || undefined, exportEnd || undefined);
        } catch {
            alert(t('system.logs.exportFail'));
        } finally {
            setExporting(false);
        }
    };

    useEffect(() => {
        const fetchLogs = async () => {
            try {
                const data = await systemService.getAuditLogs();
                setLogs(data);
            } catch {
                console.error("Failed to fetch logs");
            } finally {
                setLoading(false);
            }
        };
        fetchLogs();
    }, []);

    return (
        <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-slate-900">{t('system.logs.title')}</h1>
                    <p className="text-slate-500 mt-1">{t('system.logs.description')}</p>
                </div>
                <div className="flex items-center gap-2 text-sm">
                    <input type="date" value={exportStart} onChange={(e) => setExportStart(e.target.value)}
                        aria-label={t('system.logs.exportFrom')} className="border border-slate-300 rounded-lg px-2 py-1.5" />
                    <span className="text-slate-400">~</span>
                    <input type="date" value={exportEnd} onChange={(e) => setExportEnd(e.target.value)}
                        aria-label={t('system.logs.exportTo')} className="border border-slate-300 rounded-lg px-2 py-1.5" />
                    <button onClick={handleExport} disabled={exporting}
                        className="flex items-center px-3 py-1.5 border border-slate-300 bg-white text-slate-700 rounded-lg hover:bg-slate-50 disabled:opacity-50 font-medium">
                        <Download className="w-4 h-4 mr-1.5" />
                        {exporting ? t('common.loading') : t('system.logs.exportCsv')}
                    </button>
                </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                {loading ? (
                    <div className="p-12 text-center text-slate-500">{t('common.loading')}</div>
                ) : logs.length === 0 ? (
                    <div className="p-12 text-center text-slate-500">
                        <Shield className="w-12 h-12 mx-auto text-slate-300 mb-4" />
                        {t('system.logs.emptyLogs')}
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-slate-200">
                            <thead className="bg-slate-50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider whitespace-nowrap">{t('common.user')}</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider whitespace-nowrap">{t('system.logs.actionType')}</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider whitespace-nowrap">{t('system.logs.ipAddress')}</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider whitespace-nowrap">{t('system.logs.timestamp')}</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-slate-200">
                                {logs.map((log, index) => (
                                    <tr key={index} className="hover:bg-slate-50">
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="text-sm font-medium text-slate-900">
                                                {log.actor?.user_name || `User ${log.actor_id || log.user_id}`}
                                            </div>
                                            {log.actor?.user_email && (
                                                <div className="text-xs text-slate-500">
                                                    {log.actor.user_email}
                                                </div>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">
                                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-800">
                                                {log.action}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500 flex items-center">
                                            <Monitor className="w-4 h-4 mr-1.5 text-slate-400" />
                                            {log.ip_address || '-'}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">
                                            <div className="flex items-center">
                                                <Clock className="w-4 h-4 mr-1.5 text-slate-400" />
                                                {new Date(log.occurred_at).toLocaleString()}
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
};

export default SystemLogs;
