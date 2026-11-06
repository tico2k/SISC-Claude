import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { caseService } from '../services/case.service';
import { Case } from '../types';
import { FileText, Filter, Search, ArrowLeft, RotateCcw } from 'lucide-react';
import CaseDetail from './CaseDetail';
import DateRangeFilter from '../components/DateRangeFilter';

const AdminReview: React.FC = () => {
    const { t } = useTranslation();
    const navigate = useNavigate();
    const location = useLocation();
    const fromDashboard = location.state?.from === 'dashboard';

    const handleBack = () => {
        if (window.history.state && window.history.state.idx > 0) {
            navigate(-1);
        } else {
            navigate('/dashboard');
        }
    };

    const [cases, setCases] = useState<Case[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchParams, setSearchParams] = useSearchParams();
    const selectedCaseId = searchParams.get('caseId') ? parseInt(searchParams.get('caseId')!) : null;
    const [directCase, setDirectCase] = useState<Case | null>(null);

    const [selectedStatuses, setSelectedStatuses] = useState<string[]>([]);
    const [priorityFilter, setPriorityFilter] = useState('all');
    const [typeFilter, setTypeFilter] = useState('all');
    const [employeeFilter, setEmployeeFilter] = useState('all');
    const [startDate, setStartDate] = useState(() => {
        const d = new Date();
        d.setDate(d.getDate() - 14);
        return d.toISOString().split('T')[0];
    });
    const [endDate, setEndDate] = useState(() => new Date().toISOString().split('T')[0]);
    const [searchTerm, setSearchTerm] = useState('');

    useEffect(() => {
        if (selectedCaseId) {
            const found = cases.find(c => c.case_id === selectedCaseId);
            if (found) {
                if (['미확인', '요청', '제출'].includes(found.case_status)) {
                    setSelectedStatuses([found.case_status]);
                }
            } else if (!loading) {
                caseService.getCaseById(selectedCaseId).then(data => {
                    setDirectCase(data);
                    if (['미확인', '요청', '제출'].includes(data.case_status)) {
                        setSelectedStatuses([data.case_status]);
                    }
                }).catch(() => setDirectCase(null));
            }
        }
    }, [selectedCaseId, cases, loading]);

    const selectedCase = cases.find(c => c.case_id === selectedCaseId) || directCase;

    // Modal State
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [reviewAction, setReviewAction] = useState<'승인' | '반려'>('승인');
    const [reviewResult, setReviewResult] = useState('정당 사유');
    const [reviewComments, setReviewComments] = useState('');
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        fetchCases();
    }, []);

    const fetchCases = async () => {
        try {
            // 전체 데이터를 가져오기 위해 충분히 큰 limit 사용
            const data = await caseService.getCases(0, 50000);
            // 미확인, 요청, 제출 상태의 모든 관리 대상 인시던트 표시
            setCases(data.filter(c => c.case_status === '미확인' || c.case_status === '요청' || c.case_status === '제출'));
        } catch {
            console.error("Failed to fetch cases");
        } finally {
            setLoading(false);
        }
    };

    const uniqueEmployees = Array.from(new Set(cases.map(c => c.related_employee?.user_name).filter((name): name is string => !!name))).sort();

    const getPriorityLabel = (priority: string) => {
        switch (priority) {
            case '높음': return t('dashboard.priorityHigh');
            case '보통': return t('dashboard.priorityNormal');
            case '낮음': return t('dashboard.priorityLow');
            default: return priority;
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

    const openReviewModal = (action: '승인' | '반려') => {
        setReviewAction(action);
        setReviewResult(action === '승인' ? '정당 사유' : '징계 요청');
        setReviewComments('');
        setIsModalOpen(true);
    };

    const handleReviewSubmit = async () => {
        if (!selectedCase) return;
        setSubmitting(true);
        try {
            await caseService.reviewCase(selectedCase.case_id, reviewAction, reviewResult, reviewComments);
            setIsModalOpen(false);
            fetchCases(); // Refresh list
            setSearchParams({}); // Clear selection
            alert(t('system.review.alertSuccess'));
        } catch {
            alert(t('system.review.alertFail'));
        } finally {
            setSubmitting(false);
        }
    };

    // 1. 전체 데이터 필터링 (상태 필터 제외)
    const filteredByOthers = React.useMemo(() => {
        return cases.filter(c => {
            // Priority Filter
            if (priorityFilter !== 'all' && c.priority !== priorityFilter) return false;

            // Case Type Filter
            if (typeFilter !== 'all' && c.case_type !== typeFilter) return false;

            // Employee Filter
            if (employeeFilter !== 'all' && c.related_employee?.user_name !== employeeFilter) return false;

            // Date Range Filter
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
    }, [cases, priorityFilter, typeFilter, employeeFilter, startDate, endDate, searchTerm]);

    // 2. 상태별 카운트 계산
    const statusCounts = React.useMemo(() => ({
        'all': filteredByOthers.length,
        '미확인': filteredByOthers.filter(c => c.case_status === '미확인').length,
        '요청': filteredByOthers.filter(c => c.case_status === '요청').length,
        '제출': filteredByOthers.filter(c => c.case_status === '제출').length,
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
                if (selectedStatuses.length > 0 && !selectedStatuses.includes(c.case_status)) return false;
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

    return (
        <div className="flex flex-col h-[calc(100vh-100px)]">
            {fromDashboard && (
                <button
                    onClick={handleBack}
                    className="flex items-center text-slate-500 hover:text-slate-900 mb-4 transition-colors font-medium text-sm group w-fit"
                >
                    <ArrowLeft className="w-4 h-4 mr-1.5 transition-transform group-hover:-translate-x-0.5" />
                    {t('cases.detail.backToDashboard')}
                </button>
            )}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-4">
                <div>
                    <h1 className="text-2xl font-bold text-slate-900">{t('system.review.title')}</h1>
                    <p className="text-slate-500 mt-1">{t('system.review.description')}</p>
                </div>
            </div>

            {/* Dashboard Filters */}
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-wrap items-center gap-4 mb-6">
                {/* Status Group */}
                <div className="flex items-center space-x-2">
                    <StatusButton status="미확인" label={t('cases.status.unconfirmed')} count={statusCounts['미확인']} colorClass="slate" />
                    <StatusButton status="요청" label={t('cases.status.requested')} count={statusCounts['요청']} colorClass="blue" />
                    <StatusButton status="제출" label={t('cases.status.submitted')} count={statusCounts['제출']} colorClass="purple" />
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

                {/* Other Filters */}
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
                        <option value="all">{t('system.review.filterPriority')}</option>
                        <option value="높음">{t('dashboard.priorityHigh')}</option>
                        <option value="보통">{t('dashboard.priorityNormal')}</option>
                        <option value="낮음">{t('dashboard.priorityLow')}</option>
                    </select>

                    <select
                        value={typeFilter}
                        onChange={(e) => setTypeFilter(e.target.value)}
                        className="pl-3 pr-8 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-sky-500"
                    >
                        <option value="all">{t('system.review.filterType')}</option>
                        <option value="정보유출">{t('dashboard.typeLeak')}</option>
                        <option value="보안위반">{t('dashboard.typeViolation')}</option>
                        <option value="시스템접근">{t('dashboard.typeSystem')}</option>
                        <option value="권한오남용">{t('dashboard.typeAbuse')}</option>
                    </select>

                    <select
                        value={employeeFilter}
                        onChange={(e) => setEmployeeFilter(e.target.value)}
                        className="pl-3 pr-8 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-sky-500"
                    >
                        <option value="all">{t('cases.filter.employee')}</option>
                        {uniqueEmployees.map(name => (
                            <option key={name} value={name}>{name}</option>
                        ))}
                    </select>

                    <div className="h-6 w-px bg-slate-200 mx-2 hidden sm:block"></div>

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

            <div className="flex-1 min-h-0 flex gap-6">
                {/* Left: Case List */}
                <div className="w-1/3 min-w-[320px] bg-white rounded-xl shadow-sm border border-slate-200 flex flex-col">
                    <div className="p-4 border-b border-slate-100 bg-slate-50 rounded-t-xl">
                        <h2 className="text-sm font-semibold text-slate-700">
                            {selectedStatuses.length === 1 ? getStatusLabel(selectedStatuses[0]) :
                                selectedStatuses.length > 1 ? selectedStatuses.map(s => getStatusLabel(s)).join(', ') :
                                    t('cases.list.header')} ({filteredCases.length})
                        </h2>
                    </div>
                    <div className="flex-1 overflow-y-auto p-2 space-y-2 custom-scrollbar">
                        {loading ? (
                            <div className="p-12 text-center">
                                <div className="w-8 h-8 border-4 border-sky-200 border-t-sky-600 rounded-full animate-spin mx-auto mb-4"></div>
                                <p className="text-slate-500">{t('common.loading')}</p>
                            </div>
                        ) : filteredCases.length === 0 ? (
                            <div className="p-12 text-center text-slate-500">
                                <FileText className="w-8 h-8 mx-auto text-slate-300 mb-2" />
                                <p className="text-sm">{t('cases.list.empty')}</p>
                            </div>
                        ) : (
                            filteredCases.map((cse) => (
                                <div
                                    key={cse.case_id}
                                    onClick={() => setSearchParams({ ...Object.fromEntries(searchParams), caseId: cse.case_id.toString() })}
                                    className={`p-4 rounded-lg cursor-pointer border transition-all hover:shadow-md
                                        ${selectedCase?.case_id === cse.case_id
                                            ? 'bg-sky-50 border-sky-200 shadow-sm ring-1 ring-sky-200'
                                            : 'bg-white border-slate-100 hover:border-sky-100'}`}
                                >
                                    <div className="flex justify-between items-start mb-2">
                                        <div className="flex items-center space-x-2">
                                            <span className={`px-2 py-0.5 rounded text-xs font-bold
                                                ${cse.priority === '높음' ? 'bg-red-100 text-red-700' :
                                                    cse.priority === '보통' ? 'bg-amber-100 text-amber-700' :
                                                        'bg-slate-100 text-slate-700'}`}>
                                                {getPriorityLabel(cse.priority)}
                                            </span>
                                            <span className="text-xs text-slate-400">#{cse.incident_num || cse.case_id}</span>
                                        </div>
                                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium
                                            ${cse.case_status === '요청' ? 'bg-blue-100 text-blue-800' :
                                                cse.case_status === '제출' ? 'bg-purple-100 text-purple-800' :
                                                    cse.case_status === '미확인' ? 'bg-slate-100 text-slate-700 border border-slate-200' :
                                                        'bg-gray-100 text-gray-800'}`}>
                                            {getStatusLabel(cse.case_status)}
                                        </span>
                                    </div>
                                    <h3 className={`text-sm font-bold mb-1 truncate ${selectedCase?.case_id === cse.case_id ? 'text-sky-900' : 'text-slate-900'}`}>
                                        {cse.rule_title}
                                    </h3>
                                    <p className="text-xs text-slate-500 truncate mb-1">
                                        {cse.related_employee?.user_name || `User ${cse.related_employee_id}`}
                                    </p>
                                    <div className="flex items-center justify-between text-xs text-slate-400">
                                        <span>{new Date(cse.created_at).toLocaleDateString()}</span>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                {/* Right: Detail View & Review Actions */}
                <div className="flex-1 min-w-0 bg-white rounded-xl shadow-sm border border-slate-200 flex flex-col">
                    <div className="flex-1 overflow-y-auto custom-scrollbar p-6">
                        {selectedCase ? (
                            // Import CaseDetail at the top of the file!
                            <CaseDetail caseId={selectedCase.case_id} isEmbedded={true} onCaseUpdate={fetchCases} />
                        ) : (
                            <div className="h-full flex flex-col items-center justify-center text-slate-400">
                                <FileText className="w-16 h-16 mb-4 text-slate-300" />
                                <p>{t('system.review.emptyReview')}</p>
                            </div>
                        )}
                    </div>
                    {selectedCase && (
                        <div className="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between">
                            <span className="text-sm text-slate-500">
                                {t('common.actions')}: <strong>#{selectedCase.incident_num || selectedCase.case_id}</strong>
                                <span className="ml-2 text-xs font-medium text-slate-400">({getStatusLabel(selectedCase.case_status)})</span>
                            </span>
                            {selectedCase.case_status === '제출' ? (
                                <div className="flex space-x-3">
                                    <button
                                        onClick={() => openReviewModal('승인')}
                                        className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium transition-colors shadow-sm"
                                    >
                                        {t('system.review.btnApprove')}
                                    </button>
                                    <button
                                        onClick={() => openReviewModal('반려')}
                                        className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium transition-colors shadow-sm"
                                    >
                                        {t('system.review.btnReject')}
                                    </button>
                                </div>
                            ) : selectedCase.case_status === '미확인' ? (
                                <span className="text-xs text-amber-700 bg-amber-50 px-3 py-1.5 rounded-lg border border-amber-200 font-medium">
                                    {t('system.review.unconfirmedHint')}
                                </span>
                            ) : (
                                <span className="text-xs text-slate-500 bg-slate-100 px-3 py-1.5 rounded-lg">
                                    {t('system.review.waitingSubmission')}
                                </span>
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* Review Modal */}
            {isModalOpen && selectedCase && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
                    <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6">
                        <h3 className="text-lg font-bold text-slate-900 mb-4">
                            {reviewAction === '승인' ? t('system.review.approveTitle') : t('system.review.rejectTitle')}
                        </h3>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">
                                    {t('cases.detail.closeResult')}
                                </label>
                                <select
                                    value={reviewResult}
                                    onChange={(e) => setReviewResult(e.target.value)}
                                    className="block w-full border border-slate-300 rounded-lg p-2.5 focus:ring-sky-500 focus:border-sky-500"
                                >
                                    {reviewAction === '승인' ? (
                                        <>
                                            <option value="정당 사유">{t('cases.detail.modal.justified')} ({t('system.review.exemption')})</option>
                                            <option value="경미한 위반">{t('cases.detail.modal.minorViolation')} ({t('system.review.caution')})</option>
                                        </>
                                    ) : (
                                        <>
                                            <option value="소명 불충분">{t('system.review.insufficient')} ({t('system.review.reRequest')})</option>
                                            <option value="징계 요청">{t('system.review.disciplinary')}</option>
                                            <option value="교육 필요">{t('system.review.securityEducation')}</option>
                                        </>
                                    )}
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">
                                    {t('system.review.finalReviewResult')}
                                </label>
                                <textarea
                                    value={reviewComments}
                                    onChange={(e) => setReviewComments(e.target.value)}
                                    rows={4}
                                    className="block w-full border border-slate-300 rounded-lg p-3 focus:ring-sky-500 focus:border-sky-500"
                                    placeholder={t('system.review.finalReviewDesc')}
                                />
                            </div>
                        </div>
                        <div className="mt-6 flex justify-end space-x-3">
                            <button
                                onClick={() => setIsModalOpen(false)}
                                className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 font-medium"
                            >
                                {t('common.cancel')}
                            </button>
                            <button
                                onClick={handleReviewSubmit}
                                disabled={submitting}
                                className={`px-4 py-2 rounded-lg text-white font-medium
                            ${reviewAction === '승인' ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'}
                            disabled:opacity-50`}
                            >
                                {submitting ? t('common.loading') : (reviewAction === '승인' ? t('cases.status.approved') : t('cases.status.rejected'))}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AdminReview;
