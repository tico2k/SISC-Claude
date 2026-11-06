import { useState, useEffect } from 'react';
import { PlayCircle, PauseCircle, Zap, RefreshCw, AlertCircle, History, Filter, CheckCircle2, XCircle, Clock } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { systemService, JobResponse, BackgroundJobLog, JobLogFilter } from '../services/system.service';
import { getApiErrorBody } from '../utils/error';
import { JobTriggerPayload } from '../types';

export default function SystemJobs() {
    const { t } = useTranslation();
    const [jobs, setJobs] = useState<JobResponse[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Unified Job Log State
    const [jobLogs, setJobLogs] = useState<BackgroundJobLog[]>([]);
    const [jobFilters, setJobFilters] = useState<JobLogFilter[]>([]);
    const [selectedJobId, setSelectedJobId] = useState<string>('all');
    const [loadingLogs, setLoadingLogs] = useState(false);

    // Pagination for logs
    const [logPage, setLogPage] = useState(1);
    const logsPerPage = 10;

    // Manual Trigger / Reschedule Modal State
    const [showManualModal, setShowManualModal] = useState(false);
    const [showCronModal, setShowCronModal] = useState(false);
    const [selectedJob, setSelectedJob] = useState<JobResponse | null>(null);
    const [manualJobId, setManualJobId] = useState<string | null>(null);
    const [targetDate, setTargetDate] = useState<string>('');
    const [cronExpression, setCronExpression] = useState<string>('');

    const fetchJobs = async () => {
        try {
            setLoading(true);
            setError(null);
            const data = await systemService.getJobs();
            setJobs(data);
        } catch (err: unknown) {
            setError(getApiErrorBody(err).message || t('system.jobs.fetchFailed'));
        } finally {
            setLoading(false);
        }
    };

    const fetchLogFilters = async () => {
        try {
            const data = await systemService.getJobLogFilters();
            setJobFilters(data);
        } catch (error) {
            console.error('Failed to load job filters', error);
        }
    };

    const fetchLogs = async (jobId?: string) => {
        setLoadingLogs(true);
        try {
            // "all"이면 undefined를 보내서 전체 조회
            const data = await systemService.getJobLogs(jobId === 'all' ? undefined : jobId);
            setJobLogs(data);
            setLogPage(1);
        } catch (error) {
            console.error('Failed to load job logs', error);
            setJobLogs([]);
        } finally {
            setLoadingLogs(false);
        }
    };

    useEffect(() => {
        fetchJobs();
        fetchLogFilters();
        fetchLogs();
    }, []);

    const handlePause = async (jobId: string) => {
        if (!window.confirm(t('system.jobs.confirmPause', { id: jobId }))) return;
        try {
            await systemService.pauseJob(jobId);
            fetchJobs();
        } catch (err: unknown) {
            alert(getApiErrorBody(err).message || t('system.jobs.pauseFailed'));
        }
    };

    const handleResume = async (jobId: string) => {
        try {
            await systemService.resumeJob(jobId);
            fetchJobs();
        } catch (err: unknown) {
            alert(getApiErrorBody(err).message || t('system.jobs.resumeFailed'));
        }
    };

    const handleTrigger = async (jobId: string) => {
        if (jobId === 'generate_daily_statistics') {
            const today = new Date();
            today.setDate(today.getDate() - 1);
            setTargetDate(today.toISOString().split('T')[0]);
            setManualJobId(jobId);
            setShowManualModal(true);
            return;
        }

        if (!window.confirm(t('system.jobs.confirmTrigger', { id: jobId }))) {
            return;
        }
        await executeTrigger(jobId);
    };

    const handleEditCron = (job: JobResponse) => {
        setSelectedJob(job);
        setCronExpression(job.cron_expression || '');
        setShowCronModal(true);
    };

    const executeReschedule = async () => {
        if (!selectedJob) return;
        try {
            const res = await systemService.rescheduleJob(selectedJob.id, cronExpression);
            alert(res.message);
            setShowCronModal(false);
            fetchJobs();
        } catch (err: unknown) {
            alert(getApiErrorBody(err).message || t('system.jobs.rescheduleFailed'));
        }
    };

    const executeTrigger = async (jobId: string, payload?: JobTriggerPayload) => {
        try {
            const res = await systemService.triggerJob(jobId, payload);
            alert(res.message);
            fetchJobs();
            fetchLogs(selectedJobId); // 로그 갱신
            fetchLogFilters(); // 필터 목록 갱신 (새로운 SIEM ID 등이 생겼을 수 있음)
            setShowManualModal(false);
        } catch (err: unknown) {
            alert(getApiErrorBody(err).message || t('system.jobs.triggerFailed'));
        }
    };

    const formatDateTime = (dateString?: string) => {
        if (!dateString) return '-';
        return new Date(dateString).toLocaleString(t('common.locale'), {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    };

    return (
        <div className="space-y-6 animate-in fade-in duration-300">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight text-slate-900 mb-1">
                        {t('system.jobs.title')}
                    </h1>
                    <p className="text-slate-500">
                        {t('system.jobs.description')}
                    </p>
                </div>
                <button
                    onClick={() => {
                        fetchJobs();
                        fetchLogs(selectedJobId);
                    }}
                    disabled={loading || loadingLogs}
                    className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 
                             text-white rounded-lg transition-colors disabled:opacity-50 shadow-md"
                >
                    <RefreshCw size={18} className={loading || loadingLogs ? "animate-spin" : ""} />
                    {t('common.refresh')}
                </button>
            </div>

            {error && (
                <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3 text-red-600">
                    <AlertCircle size={20} />
                    <p>{error}</p>
                </div>
            )}

            {/* 작업 목록 카드 */}
            <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden shadow-2xl">
                <div className="p-4 border-b border-slate-800 bg-slate-800/30 flex items-center justify-between">
                    <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                        <Zap size={20} className="text-blue-400" />
                        {t('system.jobs.scheduleStatus')}
                    </h2>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr className="bg-slate-800/50 border-b border-slate-800 text-xs font-bold uppercase tracking-wider text-slate-400">
                                <th className="p-4">{t('system.jobs.jobId')}</th>
                                <th className="p-4">{t('system.jobs.descriptionLabel')}</th>
                                <th className="p-4">{t('system.jobs.actions')}</th>
                                <th className="p-4">{t('system.jobs.cron')}</th>
                                <th className="p-4">{t('system.jobs.nextRun')}</th>
                                <th className="p-4 text-right">{t('system.jobs.actions')}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800">
                            {loading && jobs.length === 0 ? (
                                <tr>
                                    <td colSpan={6} className="p-12 text-center text-slate-500">
                                        <RefreshCw size={24} className="animate-spin mx-auto mb-2 opacity-50" />
                                        {t('common.loading')}
                                    </td>
                                </tr>
                            ) : jobs.length === 0 ? (
                                <tr>
                                    <td colSpan={6} className="p-12 text-center text-slate-500">
                                        {t('system.jobs.emptyList')}
                                    </td>
                                </tr>
                            ) : (
                                jobs.map((job) => {
                                    const jobDescriptions: Record<string, string> = {
                                        'generate_daily_statistics': t('system.jobs.descGenerateStats'),
                                        'archive_old_cases': t('system.jobs.descArchiveCases'),
                                        'send_deadline_reminders': t('system.jobs.descSendReminders'),
                                        'generate_weekly_report': t('system.jobs.descWeeklyReport'),
                                    };

                                    let displayName = jobDescriptions[job.id] || job.name;
                                    if (job.id.startsWith('sync_siem_logs_')) {
                                        const siemId = job.id.split('_').pop();
                                        displayName = t('system.jobs.descSyncSiem', { id: siemId });
                                    }

                                    return (
                                        <tr key={job.id} className="hover:bg-slate-800/40 transition-colors group">
                                            <td className="p-4">
                                                <code className="px-2 py-1 bg-slate-800 rounded text-blue-400 text-xs font-mono border border-slate-700">
                                                    {job.id}
                                                </code>
                                            </td>
                                            <td className="p-4">
                                                <div className="text-slate-200 font-medium">{displayName}</div>
                                            </td>
                                            <td className="p-4">
                                                {job.status === 'RUNNING' ? (
                                                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 uppercase tracking-tight">
                                                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                                                        {t('system.jobs.running')}
                                                    </span>
                                                ) : (
                                                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20 uppercase tracking-tight">
                                                        <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
                                                        {t('system.jobs.paused')}
                                                    </span>
                                                )}
                                            </td>
                                            <td className="p-4">
                                                <div className="flex items-center gap-2">
                                                    <code className="text-xs font-mono text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded">
                                                        {job.cron_expression || '-'}
                                                    </code>
                                                    <button
                                                        onClick={() => handleEditCron(job)}
                                                        className="text-slate-500 hover:text-blue-400 transition-colors"
                                                        title={t('system.jobs.rescheduleTitle')}
                                                    >
                                                        <Clock size={14} />
                                                    </button>
                                                </div>
                                            </td>
                                            <td className="p-4 text-slate-400 text-sm">
                                                {formatDateTime(job.next_run_time)}
                                            </td>
                                            <td className="p-4">
                                                <div className="flex items-center justify-end gap-2 opacity-80 group-hover:opacity-100 transition-opacity">
                                                    {job.status === 'RUNNING' ? (
                                                        <button
                                                            onClick={() => handlePause(job.id)}
                                                            className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-500/10 hover:bg-amber-500/20 text-amber-500 rounded-md transition-all border border-amber-500/20"
                                                        >
                                                            <PauseCircle size={14} />
                                                            <span className="text-xs font-bold uppercase">{t('common.stop')}</span>
                                                        </button>
                                                    ) : (
                                                        <button
                                                            onClick={() => handleResume(job.id)}
                                                            className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-500 rounded-md transition-all border border-emerald-500/20"
                                                        >
                                                            <PlayCircle size={14} />
                                                            <span className="text-xs font-bold uppercase">{t('common.start')}</span>
                                                        </button>
                                                    )}
                                                    <button
                                                        onClick={() => handleTrigger(job.id)}
                                                        className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 rounded-md transition-all border border-blue-500/20"
                                                    >
                                                        <Zap size={14} />
                                                        <span className="text-xs font-bold uppercase">{t('system.jobs.trigger')}</span>
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    );
                                })
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* 통합 실행 이력 섹션 */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                <div className="p-5 border-b border-slate-200 bg-slate-50 flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="flex items-center gap-2">
                        <History className="w-5 h-5 text-indigo-600" />
                        <h3 className="text-lg font-bold text-slate-900">{t('system.jobs.history')}</h3>
                    </div>

                    <div className="flex items-center gap-3">
                        {/* Red Box: 작업 ID 선택기 */}
                        <div className="relative group">
                            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                                <Filter size={16} />
                            </div>
                            <select
                                value={selectedJobId}
                                onChange={(e) => {
                                    setSelectedJobId(e.target.value);
                                    fetchLogs(e.target.value);
                                }}
                                className="pl-9 pr-10 py-2 text-sm bg-white border border-slate-200 rounded-lg shadow-sm 
                                         focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 transition-all cursor-pointer hover:border-slate-300"
                                title={t('system.jobs.filterTitle', '작업 필터 선택')}
                            >
                                <option value="all">{t('system.jobs.allLogs')}</option>
                                {jobFilters.map(f => (
                                    <option key={f.job_id} value={f.job_id}>
                                        {f.job_name} ({f.job_id})
                                    </option>
                                ))}
                            </select>
                        </div>

                        <button
                            type="button"
                            onClick={() => fetchLogs(selectedJobId)}
                            disabled={loadingLogs}
                            className="p-2 text-slate-600 hover:bg-slate-200 rounded-lg transition-colors border border-slate-300 bg-white"
                        >
                            <RefreshCw className={`w-4 h-4 ${loadingLogs ? 'animate-spin' : ''}`} />
                        </button>
                    </div>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left border-collapse">
                        <thead className="text-xs text-slate-500 bg-slate-100/50 uppercase font-bold border-b border-slate-200">
                            <tr>
                                <th className="px-6 py-4">{t('system.jobs.executionTime')}</th>
                                <th className="px-6 py-4">{t('system.jobs.jobName')}</th>
                                <th className="px-6 py-4 text-center">{t('system.jobs.executionType')}</th>
                                <th className="px-6 py-4 text-center">{t('system.jobs.actions')}</th>
                                <th className="px-6 py-4 text-center">{t('system.jobs.processedCount')}</th>
                                <th className="px-6 py-4">{t('system.jobs.resultMessage')}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                            {loadingLogs && jobLogs.length === 0 ? (
                                <tr>
                                    <td colSpan={6} className="px-6 py-12 text-center text-slate-400 bg-slate-50/30">
                                        <RefreshCw size={24} className="animate-spin mx-auto mb-2 opacity-30" />
                                        {t('system.jobs.loadingLogs')}
                                    </td>
                                </tr>
                            ) : jobLogs.length === 0 ? (
                                <tr>
                                    <td colSpan={6} className="px-6 py-12 text-center text-slate-400">
                                        {t('system.jobs.emptyLogs')}
                                    </td>
                                </tr>
                            ) : (
                                (() => {
                                    const idxLast = logPage * logsPerPage;
                                    const idxFirst = idxLast - logsPerPage;
                                    const currentLogs = Array.isArray(jobLogs) ? jobLogs.slice(idxFirst, idxLast) : [];

                                    return currentLogs.map((log) => (
                                        <tr key={log.log_id} className="hover:bg-indigo-50/30 transition-colors group">
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <div className="flex items-center gap-2 text-slate-600 font-mono text-[13px]">
                                                    <Clock size={14} className="text-slate-400" />
                                                    {formatDateTime(log.execution_time)}
                                                </div>
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="font-semibold text-slate-800">{log.job_name}</div>
                                                <div className="text-[11px] text-indigo-500 font-mono mt-0.5">{log.job_id}</div>
                                            </td>
                                            <td className="px-6 py-4 text-center">
                                                {log.execution_type === 'MANUAL' ? (
                                                    <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-700 border border-purple-200">
                                                        MANUAL
                                                    </span>
                                                ) : (
                                                    <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-200">
                                                        AUTO
                                                    </span>
                                                )}
                                            </td>
                                            <td className="px-6 py-4 text-center">
                                                {log.status === 'SUCCESS' ? (
                                                    <span className="flex items-center justify-center gap-1 text-emerald-600 font-bold text-xs">
                                                        <CheckCircle2 size={14} />
                                                        {t('system.jobs.success')}
                                                    </span>
                                                ) : (
                                                    <span className="flex items-center justify-center gap-1 text-rose-600 font-bold text-xs" title={log.message}>
                                                        <XCircle size={14} />
                                                        {t('system.jobs.failure')}
                                                    </span>
                                                )}
                                            </td>
                                            <td className="px-6 py-4 text-center">
                                                <span className="px-2 py-1 bg-slate-100 rounded-md font-bold text-slate-700 text-xs">
                                                    {log.records_processed.toLocaleString()} {t('system.jobs.unit')}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="text-xs text-slate-500 max-w-xs truncate group-hover:max-w-md group-hover:whitespace-normal transition-all" title={log.message}>
                                                    {log.message || '-'}
                                                </div>
                                            </td>
                                        </tr>
                                    ));
                                })()
                            )}
                        </tbody>
                    </table>
                </div>

                {/* 페이징 컨트롤 */}
                {jobLogs.length > logsPerPage && (
                    <div className="flex items-center justify-between px-6 py-4 bg-slate-50 border-t border-slate-200">
                        <div className="text-xs text-slate-500">
                            {t('system.jobs.paginationInfo', {
                                total: jobLogs.length,
                                start: (logPage - 1) * logsPerPage + 1,
                                end: Math.min(logPage * logsPerPage, jobLogs.length)
                            })}
                        </div>
                        <div className="flex items-center space-x-1">
                            <button
                                onClick={() => setLogPage(p => Math.max(1, p - 1))}
                                disabled={logPage === 1}
                                className="px-3 py-1.5 border border-slate-300 rounded-lg text-xs font-semibold bg-white text-slate-600 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-50 transition-colors"
                            >
                                {t('common.prev')}
                            </button>
                            {Array.from({ length: Math.min(5, Math.ceil(jobLogs.length / logsPerPage)) }).map((_, i) => (
                                <button
                                    key={i}
                                    onClick={() => setLogPage(i + 1)}
                                    className={`px-3 py-1.5 rounded-lg border text-xs font-bold transition-all ${logPage === i + 1
                                        ? 'bg-indigo-600 border-indigo-600 text-white shadow-sm'
                                        : 'border-slate-300 bg-white text-slate-600 hover:bg-slate-50'
                                        }`}
                                >
                                    {i + 1}
                                </button>
                            ))}
                            <button
                                onClick={() => setLogPage(p => Math.min(Math.ceil(jobLogs.length / logsPerPage), p + 1))}
                                disabled={logPage === Math.ceil(jobLogs.length / logsPerPage)}
                                className="px-3 py-1.5 border border-slate-300 rounded-lg text-xs font-semibold bg-white text-slate-600 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-50 transition-colors"
                            >
                                {t('common.next')}
                            </button>
                        </div>
                    </div>
                )}
            </div>

            {/* 수동 실행 모달 (통계 전용) */}
            {showManualModal && manualJobId === 'generate_daily_statistics' && (
                <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-md flex items-center justify-center z-50 p-4 animate-in fade-in duration-200">
                    <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-md overflow-hidden animate-in zoom-in-95 duration-200">
                        <div className="p-6 md:p-8">
                            <div className="w-12 h-12 bg-indigo-100 rounded-full flex items-center justify-center mb-6">
                                <History className="w-6 h-6 text-indigo-600" />
                            </div>
                            <h3 className="text-xl font-bold text-slate-900 mb-2">{t('system.jobs.manualTriggerTitle')}</h3>
                            <p className="text-sm text-slate-500 mb-8 leading-relaxed">
                                {t('system.jobs.manualTriggerDesc')}
                            </p>
                            <div className="space-y-4">
                                <label className="block text-sm font-bold text-slate-700 uppercase tracking-wider">
                                    {t('system.jobs.selectDate')}
                                </label>
                                <input
                                    type="date"
                                    value={targetDate}
                                    onChange={(e) => setTargetDate(e.target.value)}
                                    className="w-full border-slate-300 rounded-xl shadow-sm focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 p-4 bg-slate-50 font-semibold"
                                />
                            </div>
                            <div className="flex flex-col md:flex-row gap-3 mt-10">
                                <button
                                    onClick={() => setShowManualModal(false)}
                                    className="flex-1 px-4 py-3 text-sm font-bold text-slate-600 bg-white border border-slate-200 rounded-xl hover:bg-slate-100 transition-all uppercase tracking-wider"
                                >
                                    {t('common.cancel')}
                                </button>
                                <button
                                    onClick={() => executeTrigger(manualJobId, { target_date: targetDate })}
                                    className="flex-1 px-4 py-3 text-sm font-bold text-white bg-indigo-600 rounded-xl hover:bg-indigo-700 transition-all flex items-center justify-center gap-2 shadow-lg shadow-indigo-200 uppercase tracking-wider"
                                >
                                    <Zap size={16} />
                                    {t('system.jobs.triggerNow')}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* 스케줄(Cron) 수정 모달 */}
            {showCronModal && selectedJob && (
                <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-md flex items-center justify-center z-50 p-4 animate-in fade-in duration-200">
                    <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-md overflow-hidden animate-in zoom-in-95 duration-200">
                        <div className="p-6 md:p-8">
                            <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mb-6">
                                <Clock className="w-6 h-6 text-blue-600" />
                            </div>
                            <h3 className="text-xl font-bold text-slate-900 mb-2">{t('system.jobs.rescheduleTitle')}</h3>
                            <p className="text-sm text-slate-500 mb-8 leading-relaxed">
                                {t('system.jobs.cronEditDesc', { name: selectedJob.name })}
                                <br />예: <code>0 9 * * *</code> (09:00 AM Daily)
                            </p>
                            <div className="space-y-4">
                                <label className="block text-sm font-bold text-slate-700 uppercase tracking-wider">
                                    {t('system.jobs.cronInput')}
                                </label>
                                <input
                                    type="text"
                                    value={cronExpression}
                                    onChange={(e) => setCronExpression(e.target.value)}
                                    placeholder="* * * * *"
                                    className="w-full border-slate-300 rounded-xl shadow-sm focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 p-4 bg-slate-50 font-mono font-semibold"
                                />
                                <p className="text-[11px] text-slate-400">
                                    {t('system.jobs.cronHelp')}: <a href="https://crontab.guru" target="_blank" rel="noreferrer" className="text-blue-500 underline">crontab.guru</a>
                                </p>
                            </div>
                            <div className="flex flex-col md:flex-row gap-3 mt-10">
                                <button
                                    onClick={() => setShowCronModal(false)}
                                    className="flex-1 px-4 py-3 text-sm font-bold text-slate-600 bg-white border border-slate-200 rounded-xl hover:bg-slate-100 transition-all uppercase tracking-wider"
                                >
                                    {t('common.cancel')}
                                </button>
                                <button
                                    onClick={executeReschedule}
                                    className="flex-1 px-4 py-3 text-sm font-bold text-white bg-blue-600 rounded-xl hover:bg-blue-700 transition-all flex items-center justify-center gap-2 shadow-lg shadow-blue-200 uppercase tracking-wider"
                                >
                                    <CheckCircle2 size={16} />
                                    {t('common.save')}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
