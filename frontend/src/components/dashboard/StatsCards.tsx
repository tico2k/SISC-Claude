import React from 'react';
import { useTranslation } from 'react-i18next';
import { FileText, AlertTriangle, MinusCircle, CheckSquare, ShieldAlert, AlertCircle, Activity, UserCircle } from 'lucide-react';

interface StatsCardsProps {
    stats: any;
    filters: any;
    toggleFilter: (type: string, value: string) => void;
    clearFilters: () => void;
    activeFilterCount: number;
}

const StatsCards: React.FC<StatsCardsProps> = ({ stats, filters, toggleFilter, clearFilters, activeFilterCount }) => {
    const { t } = useTranslation();
    if (!stats) return null;

    return (
        <>
            <div className="col-span-1 flex flex-col space-y-2">
                {/* Total Card */}
                <button
                    onClick={clearFilters}
                    className={`w-full p-2.5 rounded-xl border bg-white transition-all text-left flex flex-col justify-between
                        ${activeFilterCount === 0 ? 'border-sky-500 shadow-md ring-1 ring-sky-100' : 'border-slate-200 hover:border-sky-200 shadow-sm'}`}
                >
                    <div className="flex items-start justify-between">
                        <span className="text-xs font-bold text-slate-400 uppercase tracking-tight">{t('dashboard.totalCases')}</span>
                        <FileText className="w-5 h-5 text-slate-300" />
                    </div>
                    <span className="text-2xl font-black text-slate-900 leading-none mt-2">{stats.total}</span>
                </button>

                {/* Priority Group */}
                <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-sm space-y-2 flex-grow flex flex-col">
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-tighter ml-1">{t('dashboard.priority')}</span>
                    <div className="grid grid-cols-1 gap-1 flex-grow">
                        {[
                            { label: t('dashboard.priorityHigh'), value: '높음', count: stats.priority.high, icon: AlertTriangle, color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-100', active: 'bg-red-100 border-red-500 ring-red-100' },
                            { label: t('dashboard.priorityNormal'), value: '보통', count: stats.priority.medium, icon: MinusCircle, color: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-100', active: 'bg-amber-100 border-amber-500 ring-amber-100' },
                            { label: t('dashboard.priorityLow'), value: '낮음', count: stats.priority.low, icon: CheckSquare, color: 'text-slate-400', bg: 'bg-slate-50', border: 'border-slate-100', active: 'bg-slate-100 border-slate-500 ring-slate-100' },
                        ].map((p) => {
                            const isActive = filters.priority === p.value;
                            return (
                                <button
                                    key={p.label}
                                    onClick={() => toggleFilter('priority', p.value)}
                                    className={`w-full p-2.5 rounded-lg border transition-all text-left flex items-center justify-between group flex-grow
                                        ${isActive ? p.active + ' shadow-sm' : p.bg + ' ' + p.border + ' hover:bg-white'}`}
                                >
                                    <div className="flex flex-col">
                                        <div className="flex items-center space-x-1 mb-1">
                                            <p.icon className={`w-4 h-4 ${p.color}`} />
                                            <span className="text-xs font-bold text-slate-400">{p.label}</span>
                                        </div>
                                        <span className={`text-xl font-black ${isActive ? 'text-slate-900' : 'text-slate-800'}`}>{p.count}</span>
                                    </div>
                                </button>
                            );
                        })}
                    </div>
                </div>
            </div>

            {/* Column 2: Case Types */}
            <div className="col-span-1 flex flex-col">
                <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-sm space-y-2 h-full flex flex-col">
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-tighter ml-1">{t('dashboard.caseType')}</span>
                    <div className="grid grid-cols-1 gap-1 flex-grow">
                        {[
                            { label: t('dashboard.typeLeak'), value: '정보유출', count: stats.case_type.leak, icon: ShieldAlert, color: 'text-blue-500', bg: 'bg-blue-50', border: 'border-blue-100', active: 'bg-blue-100 border-blue-500 shadow-sm' },
                            { label: t('dashboard.typeViolation'), value: '보안위반', count: stats.case_type.violation, icon: AlertCircle, color: 'text-orange-500', bg: 'bg-orange-50', border: 'border-orange-100', active: 'bg-orange-100 border-orange-500 shadow-sm' },
                            { label: t('dashboard.typeSystem'), value: '시스템접근', count: stats.case_type.system, icon: Activity, color: 'text-indigo-500', bg: 'bg-indigo-50', border: 'border-indigo-100', active: 'bg-indigo-100 border-indigo-500 shadow-sm' },
                            { label: t('dashboard.typeAbuse'), value: '권한오남용', count: stats.case_type.abuse, icon: UserCircle, color: 'text-green-500', bg: 'bg-green-50', border: 'border-green-100', active: 'bg-green-100 border-green-500 shadow-sm' },
                        ].map((t) => {
                            const isActive = filters.case_type === t.value;
                            return (
                                <button
                                    key={t.label}
                                    onClick={() => toggleFilter('case_type', t.value)}
                                    className={`w-full p-2.5 rounded-lg border transition-all text-left flex flex-col justify-center space-y-0.5 group flex-grow
                                        ${isActive ? t.active : t.bg + ' ' + t.border + ' hover:bg-white'}`}
                                >
                                    <span className="text-xs text-slate-400">{t.label}</span>
                                    <div className="flex items-center justify-between">
                                        <span className={`text-xl font-black ${isActive ? 'text-slate-900' : 'text-slate-800'}`}>{t.count}</span>
                                        <div className="p-1">
                                            <t.icon className={`w-4 h-4 ${t.color}`} />
                                        </div>
                                    </div>
                                </button>
                            );
                        })}
                    </div>
                </div>
            </div>
        </>
    );
};

export default StatsCards;
