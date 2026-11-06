import React from 'react';
import { useTranslation } from 'react-i18next';
import { Calendar, ChevronRight, FileText, CheckCircle2, XCircle } from 'lucide-react';
import { WeeklyReport } from '../../types';

interface WeeklyReportWidgetProps {
    data: WeeklyReport[];
}

const WeeklyReportWidget: React.FC<WeeklyReportWidgetProps> = ({ data }) => {
    const { t } = useTranslation();

    if (!data || data.length === 0) {
        return (
            <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 h-full flex flex-col items-center justify-center text-slate-400">
                <Calendar className="w-12 h-12 mb-2 opacity-20" />
                <p className="text-sm">{t('dashboard.weekly.noReport')}</p>
            </div>
        );
    }

    return (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 h-full flex flex-col">
            <div className="p-4 border-b border-slate-100 flex items-center justify-between">
                <div className="flex items-center space-x-2">
                    <div className="p-2 bg-indigo-50 rounded-lg">
                        <Calendar className="w-5 h-5 text-indigo-600" />
                    </div>
                    <h3 className="text-base font-bold text-slate-900">{t('dashboard.weekly.title')}</h3>
                </div>
                <button className="text-xs font-semibold text-indigo-600 hover:text-indigo-700 flex items-center transition-colors">
                    {t('dashboard.weekly.viewDetail')} <ChevronRight className="w-4 h-4" />
                </button>
            </div>

            <div className="flex-grow overflow-auto p-2">
                <table className="w-full text-left text-sm">
                    <thead>
                        <tr className="text-slate-500 border-b border-slate-50">
                            <th className="px-3 py-2 font-medium">{t('dashboard.weekly.header.week')}</th>
                            <th className="px-3 py-2 font-medium text-center">{t('dashboard.weekly.header.occurred')}</th>
                            <th className="px-3 py-2 font-medium text-center">{t('dashboard.weekly.header.approved')}</th>
                            <th className="px-3 py-2 font-medium text-center">{t('dashboard.weekly.header.rejected')}</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-50">
                        {data.map((report) => (
                            <tr key={report.report_id} className="hover:bg-slate-50 transition-colors group">
                                <td className="px-3 py-3">
                                    <div className="flex flex-col">
                                        <span className="font-semibold text-slate-700">
                                            {t('dashboard.weekly.weekStart', { date: new Date(report.week_start).toLocaleDateString(t('common.locale', { defaultValue: 'ko-KR' }), { month: 'long', day: 'numeric' }) })}
                                        </span>
                                        <span className="text-xs text-slate-400">
                                            {report.week_start} ~ {report.week_end}
                                        </span>
                                    </div>
                                </td>
                                <td className="px-3 py-3 text-center">
                                    <div className="flex items-center justify-center space-x-1">
                                        <FileText className="w-3.5 h-3.5 text-slate-400" />
                                        <span className="font-bold text-slate-700">{report.created}</span>
                                    </div>
                                </td>
                                <td className="px-3 py-3 text-center">
                                    <div className="flex items-center justify-center space-x-1">
                                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                                        <span className="font-bold text-emerald-600">{report.approved}</span>
                                    </div>
                                </td>
                                <td className="px-3 py-3 text-center">
                                    <div className="flex items-center justify-center space-x-1">
                                        <XCircle className="w-3.5 h-3.5 text-rose-500" />
                                        <span className="font-bold text-rose-600">{report.rejected}</span>
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            <div className="p-3 bg-slate-50 rounded-b-xl border-t border-slate-100">
                <p className="text-[11px] text-slate-400 text-center">
                    {t('dashboard.weekly.footer')}
                </p>
            </div>
        </div>
    );
};

export default WeeklyReportWidget;
