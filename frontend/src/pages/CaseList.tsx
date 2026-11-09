import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { caseService } from '../services/case.service';
import { Case } from '../types';
import { FileText, Filter, Search, RotateCcw, Clock } from 'lucide-react';
import DateRangeFilter from '../components/DateRangeFilter';
import CaseDetail from './CaseDetail';

const CaseList: React.FC = () => {
    const { t } = useTranslation();
    const [cases, setCases] = useState<Case[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedStatuses, setSelectedStatuses] = useState<string[]>(['요청']);
    const [priorityFilter, setPriorityFilter] = useState('all');
    const [typeFilter, setTypeFilter] = useState('all');
    const [startDate, setStartDate] = useState(() => {
        const d = new Date();
        d.setDate(d.getDate() - 14);
        return d.toISOString().split('T')[0];
    });
    const [endDate, setEndDate] = useState(() => new Date().toISOString().split('T')[0]);
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedCaseId, setSelectedCaseId] = useState<number | null>(null);

    useEffect(() => {
        fetchCases();
    }, []);

    const fetchCases = async () => {
        try {
            // 클라이언트 사이드 전체 로드를 위해 충분히 큰 limit 사용
            const data = await caseService.getCases(0, 50000);
            // 나의 소명 관리에서는 소명 요청이 진행 중인 건부터 노출 (미확인 및 오탐 종결 건은 비노출)
            setCases(data.filter(c => c.case_status !== '미확인' && c.case_status !== '종결'));
        } catch {
            console.error("Failed to fetch cases");
            alert(t('common.fail'));
        } finally {
            setLoading(false);
        }
    };

    // 1. 전체 데이터 필터링 (상태 필터 제외)
    const filteredByOthers = React.useMemo(() => {
        return cases.filter(c => {
            if (priorityFilter !== 'all' && c.priority !== priorityFilter) return false;
            if (typeFilter !== 'all' && c.case_type !== typeFilter) return false;
            if (startDate) {
                const caseDate = new Date(c.created_at);
                const start = new Date(startDate);
                start.setHours(0, 0, 0, 0);
                if (caseDate < start) return false;
            }
            if (endDate) {
                const caseDate = new Date(c.created_at);
                const end = new Date(endDate);
                end.setHours(23, 59, 59, 999);
                if (caseDate > end) return false;
            }
            if (searchTerm) {
                const searchLower = searchTerm.toLowerCase();
                const matchesTitle = c.rule_title.toLowerCase().includes(searchLower);
                const matchesSummary = c.summary?.toLowerCase().includes(searchLower);
                const matchesIncident = c.incident_num?.toString().includes(searchTerm);
                if (!matchesTitle && !matchesSummary && !matchesIncident) return false;
            }
            return true;
        });
    }, [cases, priorityFilter, typeFilter, startDate, endDate, searchTerm]);

    // 2. 상태별 카운트 계산
    const statusCounts = React.useMemo(() => ({
        'all': filteredByOthers.length,
        '요청': filteredByOthers.filter(c => c.case_status === '요청').length,
        '제출': filteredByOthers.filter(c => c.case_status === '제출').length,
        '승인': filteredByOthers.filter(c => c.case_status === '승인').length,
        '반려': filteredByOthers.filter(c => c.case_status === '반려').length,
    }), [filteredByOthers]);

    const toggleStatus = (status: string) => {
        setSelectedStatuses(prev =>
            prev.includes(status)
                ? prev.filter(s => s !== status)
                : [...prev, status]
        );
    };

    const clearStatusFilter = () => {
        setSelectedStatuses([]);
    };

    // 3. 최종 표시 데이터 필터링 및 정렬 (최신순)
    const filteredCases = React.useMemo(() => {
        return filteredByOthers
            .filter(c => {
                if (selectedStatuses.length > 0 && !selectedStatuses.includes(c.case_status)) {
                    return false;
                }
                return true;
            })
            .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    }, [filteredByOthers, selectedStatuses]);

    const StatusButton = ({ status, label, count, colorClass }: { status: string, label: string, count: number, colorClass: string }) => {
        const isSelected = selectedStatuses.includes(status);
        return (
            <button
                onClick={() => toggleStatus(status)}
                className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg border transition-all cursor-pointer
                    ${isSelected
                        ? `bg-${colorClass}-100 border-${colorClass}-400 ring-2 ring-${colorClass}-400 ring-inset shadow-xs`
                        : 'bg-white border-slate-200 hover:bg-slate-50'}`}
            >
                <span className={`text-sm font-medium ${isSelected ? `text-${colorClass}-800 font-bold` : 'text-slate-600'}`}>{label}</span>
                <span className={`text-lg font-bold ${isSelected ? `text-${colorClass}-900` : 'text-slate-900'}`}>{count}</span>
            </button>
        );
    };

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

    const getPriorityStyle = (priority: string) => {
        switch (priority) {
            case '높음': return 'bg-red-100 text-red-700';
            case '보통': return 'bg-amber-100 text-amber-700';
            case '낮음': return 'bg-slate-100 text-slate-700';
            default: return 'bg-slate-100 text-slate-700';
        }
    };

    const getStatusStyle = (status: string) => {
        switch (status) {
            case '요청': return 'bg-blue-100 text-blue-800';
            case '제출': return 'bg-purple-100 text-purple-800';
            case '승인': return 'bg-green-100 text-green-800';
            case '반려': return 'bg-red-100 text-red-800';
            case '미확인': return 'bg-gray-100 text-gray-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    return (
        <div className="flex flex-col h-[calc(100vh-100px)]">
            <div className="mb-4">
                <h1 className="text-2xl font-bold text-slate-900">{t('common.myCases')}</h1>
                <p className="text-slate-500 mt-1">{t('common.myCasesSubtitle', { defaultValue: '할당된 보안 소명 요청을 확인하고 처리합니다.' })}</p>
            </div>

            {/* Filters Bar */}
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-wrap items-center gap-4 mb-6">
                <div className="flex items-center space-x-2 overflow-x-auto py-2 sm:py-1 hide-scrollbar">
                    <StatusButton status="요청" label={t('cases.status.requested')} count={statusCounts['요청']} colorClass="blue" />
                    <StatusButton status="제출" label={t('cases.status.submitted')} count={statusCounts['제출']} colorClass="purple" />
                    <StatusButton status="승인" label={t('cases.status.approved')} count={statusCounts['승인']} colorClass="green" />
                    <StatusButton status="반려" label={t('cases.status.rejected')} count={statusCounts['반려']} colorClass="red" />
                    {selectedStatuses.length > 0 && (
                        <button
                            onClick={clearStatusFilter}
                            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-dashed border-slate-300 hover:border-slate-400 bg-slate-50 hover:bg-slate-100 text-slate-500 hover:text-slate-800 text-xs font-bold transition-all cursor-pointer ml-1"
                            title={t('dashboard.clearFilter')}
                        >
                            <RotateCcw className="w-3.5 h-3.5" />
                            <span>{t('dashboard.clearFilter')}</span>
                        </button>
                    )}
                </div>
                <div className="h-8 w-px bg-slate-200 mx-2 hidden lg:block"></div>
                <div className="flex items-center space-x-3 flex-wrap gap-y-2">
                    <div className="flex items-center space-x-2 text-slate-500">
                        <Filter className="w-4 h-4" />
                        <span className="text-sm font-medium">{t('cases.filter.label')}</span>
                    </div>
                    <select
                        value={priorityFilter}
                        onChange={(e) => setPriorityFilter(e.target.value)}
                        className="pl-3 pr-8 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-sky-500"
                    >
                        <option value="all">{t('cases.filter.priority')}</option>
                        <option value="높음">{t('dashboard.priorityHigh')}</option>
                        <option value="보통">{t('dashboard.priorityNormal')}</option>
                        <option value="낮음">{t('dashboard.priorityLow')}</option>
                    </select>
                    <select
                        value={typeFilter}
                        onChange={(e) => setTypeFilter(e.target.value)}
                        className="pl-3 pr-8 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-sky-500"
                    >
                        <option value="all">{t('cases.filter.type')}</option>
                        <option value="정보유출">{t('dashboard.typeLeak')}</option>
                        <option value="보안위반">{t('dashboard.typeViolation')}</option>
                        <option value="시스템접근">{t('dashboard.typeSystem')}</option>
                        <option value="권한오남용">{t('dashboard.typeAbuse')}</option>
                    </select>
                    <DateRangeFilter
                        startDate={startDate}
                        endDate={endDate}
                        onStartDateChange={setStartDate}
                        onEndDateChange={setEndDate}
                    />
                    <div className="h-6 w-px bg-slate-200 mx-1 hidden sm:block"></div>
                    <div className="relative">
                        <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                        <input
                            type="text"
                            placeholder={t('cases.filter.search')}
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="pl-9 pr-4 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-sky-500 min-w-[200px]"
                        />
                    </div>
                </div>
            </div>

            {/* Dashboard Layout: Synced with AdminReview (1/3 split) */}
            <div className="flex-1 min-h-0 flex gap-6">
                {/* Left Side: Case list (1/3) */}
                <div className="w-1/3 min-w-[320px] bg-white rounded-xl shadow-sm border border-slate-200 flex flex-col">
                    <div className="p-4 border-b border-slate-100 bg-slate-50 rounded-t-xl">
                        <h2 className="text-sm font-semibold text-slate-700">{t('cases.list.header')} ({filteredCases.length})</h2>
                    </div>
                    <div className="flex-1 overflow-y-auto p-2 space-y-2 custom-scrollbar">
                        {loading ? (
                            <div className="flex flex-col items-center justify-center h-full text-slate-400">
                                <div className="w-8 h-8 border-4 border-sky-200 border-t-sky-600 rounded-full animate-spin mb-3"></div>
                                <p>{t('cases.list.loading')}</p>
                            </div>
                        ) : filteredCases.length === 0 ? (
                            <div className="flex flex-col items-center justify-center h-full text-slate-400">
                                <FileText className="w-12 h-12 mb-2 opacity-20" />
                                <p>{t('cases.list.empty')}</p>
                            </div>
                        ) : (
                            filteredCases.map((cse) => {
                                const pStyle = getPriorityStyle(cse.priority);
                                return (
                                    <div
                                        key={cse.case_id}
                                        onClick={() => setSelectedCaseId(cse.case_id)}
                                        className={`p-4 rounded-lg cursor-pointer border transition-all hover:shadow-md
                                            ${selectedCaseId === cse.case_id
                                                ? 'bg-sky-50 border-sky-200 shadow-sm ring-1 ring-sky-200'
                                                : 'bg-white border-slate-100 hover:border-sky-100'}`}
                                    >
                                        <div className="flex justify-between items-start mb-2">
                                            <div className="flex items-center space-x-2">
                                                <span className={`px-2 py-0.5 rounded text-xs font-bold ${pStyle}`}>
                                                    {getPriorityLabel(cse.priority)}
                                                </span>
                                                <span className="text-xs text-slate-400">#{cse.incident_num || cse.case_id}</span>
                                                <span className="text-[10px] px-1.5 py-0.5 bg-indigo-50 text-indigo-500 rounded font-bold border border-indigo-100">
                                                    {getCaseTypeLabel(cse.case_type)}
                                                </span>
                                                {cse.is_overdue && (
                                                    <span className="inline-flex items-center text-[10px] px-1.5 py-0.5 bg-red-50 text-red-600 rounded font-bold border border-red-200">
                                                        <Clock className="w-3 h-3 mr-0.5" />{t('cases.badge.overdue')}
                                                    </span>
                                                )}
                                            </div>
                                            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getStatusStyle(cse.case_status)}`}>
                                                {getStatusLabel(cse.case_status)}
                                            </span>
                                        </div>
                                        <h3 className={`text-sm font-bold mb-1 truncate ${selectedCaseId === cse.case_id ? 'text-sky-900' : 'text-slate-900'}`}>
                                            {cse.rule_title}
                                        </h3>
                                        <p className="text-xs text-slate-500 truncate mb-1">
                                            {cse.summary || cse.rule_description || '-'}
                                        </p>
                                        <div className="flex items-center justify-between text-xs text-slate-400">
                                            <span>{new Date(cse.created_at).toLocaleDateString()}</span>
                                        </div>
                                    </div>
                                );
                            })
                        )}
                    </div>
                </div>

                {/* Right: Detail View */}
                <div className="flex-1 min-w-0 bg-white rounded-xl shadow-sm border border-slate-200 flex flex-col">
                    <div className="flex-1 overflow-y-auto custom-scrollbar p-6">
                        {selectedCaseId ? (
                            <CaseDetail
                                caseId={selectedCaseId}
                                isEmbedded={true}
                                onCaseUpdate={() => {
                                    setSelectedCaseId(null);
                                    fetchCases();
                                }}
                            />
                        ) : (
                            <div className="h-full flex flex-col items-center justify-center text-slate-400">
                                <FileText className="w-16 h-16 mb-4 text-slate-300" />
                                <p>{t('cases.list.selectPrompt')}</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default CaseList;
