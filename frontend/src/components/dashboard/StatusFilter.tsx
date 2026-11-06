import React from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../context/AuthContext';

interface StatusFilterProps {
    stats: any;
    filters: any;
    toggleFilter: (type: string, value: string) => void;
}

const StatusFilter: React.FC<StatusFilterProps> = ({ stats, filters, toggleFilter }) => {
    const { t } = useTranslation();
    const { role } = useAuth();
    if (!stats) return null;

    const isAdminOrAudit = role === '보안관리자' || role === '감사팀' || role === '시스템관리자';

    const allStatuses = [
        { label: t('cases.status.unconfirmed'), value: '미확인', count: stats.status.unclassified, colorClass: 'slate' },
        { label: t('cases.status.requested'), value: '요청', count: stats.status.requested, colorClass: 'blue' },
        { label: t('cases.status.submitted'), value: '제출', count: stats.status.submitted, colorClass: 'purple' },
        { label: t('cases.status.approved'), value: '승인', count: stats.status.approved, colorClass: 'green' },
        { label: t('cases.status.rejected'), value: '반려', count: stats.status.rejected, colorClass: 'red' },
        { label: t('cases.status.closed'), value: '종결', count: stats.status.closed, colorClass: 'gray' },
    ];

    // 일반 사용자는 관리자 내부 스크리닝(미확인) 및 오탐 자체종결(종결)을 숨기고 실제 소명 관련 4대 상태만 노출
    const visibleStatuses = isAdminOrAudit 
        ? allStatuses 
        : allStatuses.filter(st => st.value !== '미확인' && st.value !== '종결');

    return (
        <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-100 flex flex-wrap items-center gap-4 mt-2">
            <div className="flex items-center space-x-2 overflow-x-auto py-2 sm:py-1 hide-scrollbar w-full">
                {visibleStatuses.map((st) => {
                    const isActive = filters.case_status === st.value;
                    return (
                        <button
                            key={st.label}
                            onClick={() => toggleFilter('case_status', st.value)}
                            className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg border transition-all shrink-0
                                ${isActive
                                    ? `bg-${st.colorClass}-100 border-${st.colorClass}-400 ring-2 ring-${st.colorClass}-400 ring-inset`
                                    : 'bg-white border-slate-200 hover:bg-slate-50'}`}
                        >
                            <span className={`text-sm font-medium ${isActive ? `text-${st.colorClass}-800` : 'text-slate-600'}`}>{st.label}</span>
                            <span className={`text-lg font-bold ${isActive ? `text-${st.colorClass}-900` : 'text-slate-900'}`}>{st.count}</span>
                        </button >
                    );
                })}
            </div >
        </div >
    );
};

export default StatusFilter;
