import React, { useEffect, useState } from 'react';
import { systemService, AuditLog } from '../services/system.service';
import { useTranslation } from 'react-i18next';
import { Shield, Clock, Monitor } from 'lucide-react';

const SystemLogs: React.FC = () => {
    const { t } = useTranslation();
    const [logs, setLogs] = useState<AuditLog[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchLogs = async () => {
            try {
                const data = await systemService.getAuditLogs();
                setLogs(data);
            } catch (error) {
                console.error("Failed to fetch logs");
            } finally {
                setLoading(false);
            }
        };
        fetchLogs();
    }, []);

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-2xl font-bold text-slate-900">{t('system.logs.title')}</h1>
                <p className="text-slate-500 mt-1">{t('system.logs.description')}</p>
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
                                {logs.map((log: any, index) => (
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
