import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ChevronLeft, ChevronRight, Activity, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';
import { caseService } from '../../services/case.service';
import { useAuth } from '../../context/AuthContext';
import { Case } from '../../types';
import { useTranslation } from 'react-i18next';

interface CasesTableProps {
    filters: any;
    activeFilterCount: number;
}

const CasesTable: React.FC<CasesTableProps> = ({ filters, activeFilterCount }) => {
    const { t } = useTranslation();
    const navigate = useNavigate();
    const { role } = useAuth();
    const [page, setPage] = useState(1);
    const [sortConfig, setSortConfig] = useState<{ key: string; direction: 'asc' | 'desc' }>({
        key: 'created_at',
        direction: 'desc'
    });
    const limit = 6;

    const isAdminOrAudit = role === '보안관리자' || role === '감사팀' || role === '시스템관리자';

    const handleRowClick = (cse: Case) => {
        if (isAdminOrAudit) {
            // 관리자 및 감사팀: 미확인/요청/제출 건은 소명 검토 화면으로 직행, 이미 완료된 건은 상세 뷰로 이동
            if (['미확인', '요청', '제출'].includes(cse.case_status)) {
                navigate(`/reviews?caseId=${cse.case_id}`, { state: { from: 'dashboard' } });
            } else {
                navigate(`/cases/${cse.case_id}`, { state: { from: 'dashboard' } });
            }
        } else {
            // 일반 사용자: 나의 소명 상세/작성 화면으로 즉시 이동 (이전 화면 정보 state 전달)
            navigate(`/cases/${cse.case_id}`, { state: { from: 'dashboard' } });
        }
    };

    const { data: paginatedData, isLoading } = useQuery({
        queryKey: ['cases', page, limit, filters, sortConfig],
        queryFn: () => caseService.getCasesPaginated(
            (page - 1) * limit,
            limit,
            filters.case_status,
            filters.priority,
            filters.case_type,
            filters.startDate,
            filters.endDate,
            sortConfig.key,
            sortConfig.direction
        ),
    });

    const handleSort = (key: string) => {
        setSortConfig(prev => ({
            key,
            direction: prev.key === key && prev.direction === 'desc' ? 'asc' : 'desc'
        }));
        setPage(1);
    };

    const SortIcon = ({ colId }: { colId: string }) => {
        if (sortConfig.key !== colId) return <ArrowUpDown className="w-3 h-3 ml-1 opacity-20 group-hover:opacity-100 transition-opacity shrink-0 inline-block" />;
        return sortConfig.direction === 'asc'
            ? <ArrowUp className="w-3 h-3 ml-1 text-sky-500 shrink-0 inline-block" />
            : <ArrowDown className="w-3 h-3 ml-1 text-sky-500 shrink-0 inline-block" />;
    };

    const cases: Case[] = paginatedData?.items || [];
    const totalCases = paginatedData?.total || 0;
    const totalPages = paginatedData?.pages || 0;

    const getPriorityLabel = (priority: string) => {
        switch (priority) {
            case '높음': return t('dashboard.priorityHigh');
            case '보통': return t('dashboard.priorityNormal');
            case '낮음': return t('dashboard.priorityLow');
            default: return priority;
        }
    };

    const getCaseTypeLabel = (type: string) => {
        switch (type) {
            case '정보유출': return t('dashboard.typeLeak');
            case '보안위반': return t('dashboard.typeViolation');
            case '시스템접근': return t('dashboard.typeSystem');
            case '권한오남용': return t('dashboard.typeAbuse');
            default: return type;
        }
    };

    const getCloseResultLabel = (result: string) => {
        switch (result) {
            case '오탐': return t('cases.detail.modal.falsePositive');
            case '정당 사유': return t('cases.detail.modal.justified');
            case '경미한 위반': return t('cases.detail.modal.minorViolation');
            default: return result;
        }
    };

    const getStatusLabel = (status: string) => {
        switch (status) {
            case '미확인': return t('cases.status.unconfirmed');
            case '요청': return t('cases.status.requested');
            case '제출': return t('cases.status.submitted');
            case '승인': return t('cases.status.approved');
            case '반려': return t('cases.status.rejected');
            case '종결': return t('cases.status.closed');
            default: return status;
        }
    };

    return (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden mt-3">
            <div className="p-3 md:p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/50">
                <div className="flex items-center space-x-3">
                    <Activity className="w-5 h-5 text-sky-500" />
                    <h2 className="text-base md:text-lg font-bold text-slate-900">
                        {t('dashboard.table.title')}
                        {activeFilterCount > 0 && <span className="ml-2 text-sky-600 text-xs md:text-sm font-medium">{t('dashboard.unconfirmedCount', { count: totalCases })}</span>}
                    </h2>
                </div>
                <div className="text-xs text-slate-400 font-medium hidden sm:flex items-center">
                    <span>{isAdminOrAudit ? t('dashboard.table.clickHintAdmin') : t('dashboard.table.clickHintUser')}</span>
                </div>
            </div>

            <div className="overflow-x-auto pb-2 custom-scrollbar">
                <table className="w-full text-left border-collapse table-fixed min-w-[1220px]">
                    <thead>
                         <tr className="bg-slate-50 border-b border-slate-200">
                            <th className="px-3 py-3 text-xs font-bold text-slate-500 uppercase tracking-wider w-[95px] cursor-pointer hover:bg-slate-100 group transition-colors whitespace-nowrap" onClick={() => handleSort('priority')}>
                                <div className="flex items-center">{t('dashboard.table.priority')} <SortIcon colId="priority" /></div>
                            </th>
                            <th className="px-3 py-3 text-xs font-bold text-slate-500 uppercase tracking-wider w-[130px] cursor-pointer hover:bg-slate-100 group transition-colors whitespace-nowrap" onClick={() => handleSort('incident_num')}>
                                <div className="flex items-center">{t('dashboard.table.incidentNum')} <SortIcon colId="incident_num" /></div>
                            </th>
                            <th className="px-3 py-3 text-xs font-bold text-slate-500 uppercase tracking-wider w-[125px] cursor-pointer hover:bg-slate-100 group transition-colors whitespace-nowrap" onClick={() => handleSort('case_type')}>
                                <div className="flex items-center">{t('dashboard.table.type')} <SortIcon colId="case_type" /></div>
                            </th>
                            <th className="px-3 py-3 text-xs font-bold text-slate-500 uppercase tracking-wider min-w-[220px] cursor-pointer hover:bg-slate-100 group transition-colors whitespace-nowrap" onClick={() => handleSort('rule_title')}>
                                <div className="flex items-center">{t('dashboard.table.content')} <SortIcon colId="rule_title" /></div>
                            </th>
                            <th className="px-3 py-3 text-xs font-bold text-slate-500 uppercase tracking-wider w-[130px] cursor-pointer hover:bg-slate-100 group transition-colors whitespace-nowrap" onClick={() => handleSort('created_at')}>
                                <div className="flex items-center">{t('dashboard.table.occurredAt')} <SortIcon colId="created_at" /></div>
                            </th>
                            <th className="px-3 py-3 text-xs font-bold text-slate-500 uppercase tracking-wider w-[125px] cursor-pointer hover:bg-slate-100 group transition-colors whitespace-nowrap" onClick={() => handleSort('due_date')}>
                                <div className="flex items-center">{t('dashboard.table.deadline')} <SortIcon colId="due_date" /></div>
                            </th>
                            <th className="px-3 py-3 text-xs font-bold text-slate-500 uppercase tracking-wider w-[145px] cursor-pointer hover:bg-slate-100 group transition-colors whitespace-nowrap" onClick={() => handleSort('final_review_date')}>
                                <div className="flex items-center">{t('dashboard.table.responseDate')} <SortIcon colId="final_review_date" /></div>
                            </th>
                            <th className="px-3 py-3 text-xs font-bold text-slate-500 uppercase tracking-wider w-[115px] cursor-pointer hover:bg-slate-100 group transition-colors whitespace-nowrap" onClick={() => handleSort('related_employee')}>
                                <div className="flex items-center">{t('dashboard.table.target')} <SortIcon colId="related_employee" /></div>
                            </th>
                            <th className="px-3 py-3 text-xs font-bold text-slate-500 uppercase tracking-wider w-[110px] cursor-pointer hover:bg-slate-100 group transition-colors whitespace-nowrap" onClick={() => handleSort('case_status')}>
                                <div className="flex items-center">{t('dashboard.table.status')} <SortIcon colId="case_status" /></div>
                            </th>
                            <th className="px-3 py-3 text-xs font-bold text-slate-500 uppercase tracking-wider w-[125px] cursor-pointer hover:bg-slate-100 group transition-colors whitespace-nowrap" onClick={() => handleSort('case_result')}>
                                <div className="flex items-center">{t('dashboard.table.result')} <SortIcon colId="case_result" /></div>
                            </th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 bg-white">
                        {isLoading ? (
                            <tr>
                                <td colSpan={10} className="p-10 text-center text-slate-400 text-xs">{t('dashboard.table.loading')}</td>
                            </tr>
                        ) : cases.length === 0 ? (
                            <tr>
                                <td colSpan={10} className="p-10 text-center text-slate-400 text-xs">{t('dashboard.table.noData')}</td>
                            </tr>
                        ) : (
                            cases.map((cse) => (
                                <tr 
                                    key={cse.case_id} 
                                    onClick={() => handleRowClick(cse)}
                                    className="hover:bg-sky-50/60 cursor-pointer transition-all border-l-4 border-l-transparent hover:border-l-sky-500 group"
                                    title={isAdminOrAudit ? "클릭하여 소명 검토 및 조치 화면으로 이동" : "클릭하여 소명서 작성 및 상세 확인"}
                                >
                                    <td className="px-3 py-3 whitespace-nowrap">
                                        <span className={`inline-flex px-2 py-0.5 rounded text-xs font-black border
                                            ${cse.priority === '높음' ? 'bg-red-50 text-red-600 border-red-100' :
                                                cse.priority === '보통' ? 'bg-amber-50 text-amber-600 border-amber-100' :
                                                    'bg-slate-50 text-slate-400 border-slate-100'
                                            }`}>
                                            {getPriorityLabel(cse.priority)}
                                        </span>
                                    </td>
                                    <td className="px-3 py-3 whitespace-nowrap text-xs font-bold text-slate-400">
                                        {cse.incident_num ? `#${cse.incident_num}` : '-'}
                                    </td>
                                    <td className="px-3 py-3 whitespace-nowrap text-xs font-bold text-slate-400">
                                        {getCaseTypeLabel(cse.case_type)}
                                    </td>
                                    <td className="px-3 py-3 overflow-hidden">
                                        <div className="min-w-0">
                                            <p className="font-bold text-slate-800 text-sm line-clamp-1 break-all">{cse.rule_title}</p>
                                            <p className="text-xs text-slate-400 truncate">{cse.summary}</p>
                                        </div>
                                    </td>
                                    <td className="px-3 py-3 whitespace-nowrap text-xs text-slate-500">
                                        {new Date(cse.created_at).toLocaleDateString()}
                                    </td>
                                    <td className="px-3 py-3 whitespace-nowrap text-xs text-slate-500">
                                        {new Date(cse.due_date).toLocaleDateString()}
                                    </td>
                                    <td className="px-3 py-3 whitespace-nowrap text-xs text-slate-500">
                                        {cse.final_review_date ? new Date(cse.final_review_date).toLocaleDateString() : '-'}
                                    </td>
                                    <td className="px-3 py-3 whitespace-nowrap text-xs font-bold text-slate-400">
                                        {cse.related_employee?.user_name || '-'}
                                    </td>
                                    <td className="px-3 py-3 whitespace-nowrap">
                                        <span className={`px-2 py-1 rounded-full text-xs font-black whitespace-nowrap
                                            ${cse.case_status === '요청' ? 'bg-blue-100 text-blue-700' :
                                                cse.case_status === '제출' ? 'bg-indigo-100 text-indigo-700' :
                                                    cse.case_status === '승인' ? 'bg-green-100 text-green-700' :
                                                        cse.case_status === '미확인' ? 'bg-slate-100 text-slate-500' :
                                                            'bg-red-100 text-red-700'
                                            }`}>
                                            {getStatusLabel(cse.case_status)}
                                        </span>
                                    </td>
                                    <td className="px-3 py-3 whitespace-nowrap">
                                        {cse.case_result && (
                                            <span className="inline-flex px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-600 border border-slate-200">
                                                {getCloseResultLabel(cse.case_result)}
                                            </span>
                                        )}
                                        {!cse.case_result && <span className="text-slate-300 text-xs">-</span>}
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            {/* Pagination Controls */}
            {!isLoading && totalCases > limit && (
                <div className="flex items-center justify-between px-4 py-3 bg-white border-t border-slate-100 rounded-b-xl">
                    <div className="flex items-center text-xs text-slate-500">
                        {t('dashboard.table.pagination', {
                            total: totalCases,
                            start: Math.min((page - 1) * limit + 1, totalCases),
                            end: Math.min(page * limit, totalCases)
                        })}
                    </div>
                    <div className="flex items-center space-x-1">
                        <button
                            onClick={() => setPage(p => Math.max(1, p - 1))}
                            disabled={page === 1}
                            className="p-1 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-30 disabled:hover:bg-white transition-colors"
                        >
                            <ChevronLeft className="w-4 h-4 text-slate-600" />
                        </button>
                        {Array.from({ length: totalPages }).map((_, i) => {
                            const pageNum = i + 1;
                            if (
                                pageNum === 1 ||
                                pageNum === totalPages ||
                                (pageNum >= page - 2 && pageNum <= page + 2)
                            ) {
                                return (
                                    <button
                                        key={pageNum}
                                        onClick={() => setPage(pageNum)}
                                        className={`w-8 h-8 rounded-lg text-xs font-bold transition-all
                                            ${page === pageNum
                                                ? 'bg-sky-500 text-white shadow-sm'
                                                : 'text-slate-600 hover:bg-slate-50 border border-transparent hover:border-slate-200'}`}
                                    >
                                        {pageNum}
                                    </button>
                                );
                            }
                            if (pageNum === page - 3 || pageNum === page + 3) {
                                return <span key={pageNum} className="text-slate-300 px-1 text-xs">...</span>;
                            }
                            return null;
                        })}
                        <button
                            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                            disabled={page === totalPages}
                            className="p-1 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-30 disabled:hover:bg-white transition-colors"
                        >
                            <ChevronRight className="w-4 h-4 text-slate-600" />
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default CasesTable;
