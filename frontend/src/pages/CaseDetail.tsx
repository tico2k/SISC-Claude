import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { caseService } from '../services/case.service';
import { useAuth } from '../context/AuthContext';
import { Case } from '../types';
import { validateFiles } from '../utils/fileValidation';
import { getHttpStatus } from '../utils/error';
import {
    ArrowLeft,
    Calendar,
    AlertTriangle,
    CheckCircle2,
    XCircle,
    Paperclip,
    Download,
    Upload,
    RotateCcw,
    ShieldCheck,
    FileText,
    Printer,
    ExternalLink,
    AlertOctagon,
    Clock,
    Lock
} from 'lucide-react';
import SmartSubmissionForm from '../components/SmartSubmissionForm';
import CaseAdminPanel from '../components/CaseAdminPanel';

interface CaseDetailProps {
    caseId?: number;
    isEmbedded?: boolean;
    onCaseUpdate?: () => void;
}

const CaseDetail: React.FC<CaseDetailProps> = ({ caseId: propCaseId, isEmbedded = false, onCaseUpdate }) => {
    const { t } = useTranslation();
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const location = useLocation();
    const { role } = useAuth();
    const fromDashboard = location.state?.from === 'dashboard';

    const handleBack = () => {
        // 대시보드 또는 이전 페이지에서 유입된 경우 히스토리 뒤로가기 실행
        if (window.history.state && window.history.state.idx > 0) {
            navigate(-1);
        } else if (fromDashboard) {
            navigate('/dashboard');
        } else if (role === '보안관리자' || role === '감사팀' || role === '시스템관리자') {
            navigate('/reviews');
        } else {
            navigate('/cases');
        }
    };
    const [cse, setCse] = useState<Case | null>(null);
    const [loading, setLoading] = useState(true);
    const [showRequestModal, setShowRequestModal] = useState(false);
    const [showCloseModal, setShowCloseModal] = useState(false);
    const [requestDueDate, setRequestDueDate] = useState('');
    const [requestReason, setRequestReason] = useState('');
    const [requestFiles, setRequestFiles] = useState<File[]>([]);
    const [closeResult, setCloseResult] = useState('오탐');
    const [closeReason, setCloseReason] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [requestModalStep, setRequestModalStep] = useState<1 | 2>(1);
    const [dragActive, setDragActive] = useState(false);
    const [showResubmitForm, setShowResubmitForm] = useState(false);
    const [pledgeAgreed, setPledgeAgreed] = useState(false);
    const [pledgeSubmitted, setPledgeSubmitted] = useState(false);

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

    const getCloseResultLabel = (result: string) => {
        switch (result) {
            case '오탐': return t('cases.detail.modal.falsePositive');
            case '정당 사유': return t('cases.detail.modal.justified');
            case '경미한 위반': return t('cases.detail.modal.minorViolation');
            case '소명 불충분': return t('cases.detail.modal.insufficientTarget');
            case '교육 필요': return t('cases.detail.modal.educationTarget');
            case '징계 요청': return t('cases.detail.modal.disciplinaryTarget');
            default: return result;
        }
    };

    // Determine the active case ID: prop takes precedence over URL param
    const activeId = propCaseId || (id ? parseInt(id) : null);

    useEffect(() => {
        if (activeId) {
            fetchCase(activeId);
        } else {
            // If no ID is provided, reset state (useful for split view when selection is cleared)
            setCse(null);
            setLoading(false);
        }
    }, [activeId]);

    const fetchCase = async (caseId: number) => {
        setLoading(true);
        try {
            const data = await caseService.getCaseById(caseId);
            setCse(data);
        } catch (error) {
            console.error("Failed to fetch case", error);
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async (content: string, classification: string, files: File[]) => {
        if (!cse) return;
        setSubmitting(true);
        try {
            await caseService.submitClarification(cse.case_id, content, classification, files);
            // Refresh
            await fetchCase(cse.case_id);
            if (onCaseUpdate) onCaseUpdate();
            alert(t('cases.detail.alerts.submitSuccess'));
        } catch (error) {
            console.error("Submission failed", error);
            alert(t('cases.detail.alerts.submitFail'));
        } finally {
            setSubmitting(false);
        }
    };

    const handleDownload = async (fileId: number, fileName: string) => {
        try {
            const blob = await caseService.downloadAttachment(fileId);
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = fileName;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (error) {
            console.error(error);
            // 409: 저장 해시와 파일이 달라 무결성 검증 실패 (변조·손상 의심)
            alert(getHttpStatus(error) === 409 ? t('cases.detail.alerts.integrityFail') : t('cases.detail.alerts.downloadFail'));
        }
    };

    const handleRequestSubmit = async () => {
        if (!cse) return;
        if (!requestDueDate || !requestReason) {
            alert(t('cases.detail.alerts.requestRequirement'));
            return;
        }

        try {
            await caseService.requestClarification(cse.case_id, requestDueDate, requestReason, requestFiles);
            alert(t('cases.detail.alerts.requestSuccess'));
            setShowRequestModal(false);
            fetchCase(cse.case_id);
            if (onCaseUpdate) onCaseUpdate();
            // Reset form
            setRequestDueDate('');
            setRequestReason('');
            setRequestFiles([]);
            setRequestModalStep(1);
        } catch (error) {
            console.error(error);
            alert(t('cases.detail.alerts.requestFail'));
        }
    };

    const handleCloseSubmit = async () => {
        if (!cse) return;
        if (!closeResult || !closeReason) {
            alert(t('cases.detail.alerts.closeRequirement'));
            return;
        }

        try {
            await caseService.closeCase(cse.case_id, closeResult, closeReason);
            alert(t('cases.detail.alerts.closeSuccess'));
            setShowCloseModal(false);
            fetchCase(cse.case_id);
            if (onCaseUpdate) onCaseUpdate();
            setCloseReason('');
        } catch (error) {
            console.error(error);
            alert(t('cases.detail.alerts.closeFail'));
        }
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) {
            const newFiles = Array.from(e.target.files);

            // 파일 검증
            const validation = validateFiles(newFiles);
            if (!validation.valid) {
                alert(validation.error || t('cases.detail.alerts.fileValidationFail'));
                e.target.value = ''; // 입력 초기화
                return;
            }

            setRequestFiles(prev => [...prev, ...newFiles]);
        }
    };

    const removeFile = (index: number) => {
        setRequestFiles(prev => prev.filter((_, i) => i !== index));
    };

    const handleDrag = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setDragActive(true);
        } else if (e.type === 'dragleave') {
            setDragActive(false);
        }
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            const droppedFiles = Array.from(e.dataTransfer.files);
            const validation = validateFiles(droppedFiles);
            if (!validation.valid) {
                alert(validation.error || t('cases.detail.alerts.fileValidationFail'));
                return;
            }
            setRequestFiles(prev => [...prev, ...droppedFiles]);
        }
    };

    if (loading && activeId) return <div className="p-8 text-center text-slate-500">{t('cases.list.loading')}</div>;
    if (!activeId) return <div className="p-8 text-center text-slate-500">{t('cases.list.selectPrompt')}</div>;
    // If we get here, activeId is present. If cse is null, it means we fetched but got nothing or error.
    if (!cse || !activeId) return <div className="p-8 text-center text-slate-500">{t('cases.list.empty')}</div>;

    const getStatusColor = (status: string) => {
        switch (status) {
            case '미확인': return 'bg-slate-100 text-slate-600';
            case '요청': return 'bg-blue-100 text-blue-800';
            case '제출': return 'bg-purple-100 text-purple-800';
            case '승인': return 'bg-green-100 text-green-800';
            case '반려': return 'bg-red-100 text-red-800';
            case '종결': return 'bg-slate-200 text-slate-800';
            default: return 'bg-slate-100 text-slate-600';
        }
    };

    return (
        <div className={`w-full ${isEmbedded ? '' : 'max-w-5xl mx-auto py-8 px-4'}`}>
            {!isEmbedded && (
                <button
                    onClick={handleBack}
                    className="flex items-center text-slate-500 hover:text-slate-900 mb-6 transition-colors font-medium text-sm group"
                >
                    <ArrowLeft className="w-4 h-4 mr-1.5 transition-transform group-hover:-translate-x-0.5" />
                    {fromDashboard ? t('cases.detail.backToDashboard') : t('cases.detail.back')}
                </button>
            )}

            <div className="space-y-6">
                {/* Header Card */}
                <div className="bg-white rounded-2xl border border-slate-100 p-8 shadow-sm">
                    <div className="flex justify-between items-start mb-6">
                        <div className="space-y-3">
                            <div className="flex items-center space-x-2">
                                <span className={`px-2.5 py-0.5 rounded text-[11px] font-black border uppercase tracking-wider
                                        ${cse.priority === '높음' ? 'bg-red-50 text-red-600 border-red-100' :
                                        cse.priority === '보통' ? 'bg-orange-50 text-orange-600 border-orange-100' :
                                            'bg-slate-50 text-slate-500 border-slate-100'}`}>
                                    {getPriorityLabel(cse.priority)}
                                </span>
                                <span className="px-2.5 py-0.5 rounded text-[11px] font-bold bg-indigo-50 text-indigo-500 border border-indigo-100">
                                    {getCaseTypeLabel(cse.case_type)}
                                </span>
                            </div>
                            <h1 className="text-2xl font-black text-slate-900 leading-tight">{cse.rule_title}</h1>
                            <p className="text-sm text-slate-500 font-medium">{cse.rule_description || `${t('dashboard.daily.unclassified')}: ${cse.rule_title}`}</p>
                        </div>
                        <div className="flex items-center space-x-3">
                            {cse.is_overdue && (
                                <span className="inline-flex items-center px-3 py-1 rounded text-xs font-black border bg-red-50 text-red-600 border-red-200">
                                    <Clock className="w-3.5 h-3.5 mr-1" />{t('cases.badge.overdue')}
                                </span>
                            )}
                            {cse.legal_hold && (
                                <span className="inline-flex items-center px-3 py-1 rounded text-xs font-black border bg-amber-50 text-amber-700 border-amber-200">
                                    <Lock className="w-3.5 h-3.5 mr-1" />{t('cases.badge.legalHold')}
                                </span>
                            )}
                            {cse.anonymized_at && (
                                <span className="px-3 py-1 rounded text-xs font-black border bg-slate-100 text-slate-500 border-slate-200">
                                    {t('cases.badge.anonymized')}
                                </span>
                            )}
                            <span className={`px-3 py-1 rounded text-xs font-black border ${getStatusColor(cse.case_status)}`}>
                                {getStatusLabel(cse.case_status)}
                            </span>
                            {(role === '보안관리자' || role === '감사팀' || role === '시스템관리자') && cse.original_log_link && (
                                <a
                                    href={cse.original_log_link}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex items-center px-3 py-1.5 border border-slate-200 text-[11px] font-bold rounded-lg text-slate-600 bg-white hover:bg-slate-50 transition-colors"
                                >
                                    <svg className="mr-2 h-3.5 w-3.5 text-slate-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                                        <polyline points="15 3 21 3 21 9" />
                                        <line x1="10" y1="14" x2="21" y2="3" />
                                    </svg>
                                    {t('cases.detail.originalLog')}
                                </a>
                            )}
                        </div>
                    </div>

                    <div className="grid grid-cols-4 gap-8 pt-6 border-t border-slate-50">
                        <div className="space-y-1.5">
                            <span className="text-[10px] text-slate-400 font-black uppercase tracking-tight">{t('cases.detail.incidentId')}</span>
                            <p className="text-sm font-bold text-slate-800">#{cse.incident_num || cse.case_id}</p>
                        </div>
                        <div className="space-y-1.5">
                            <span className="text-[10px] text-slate-400 font-black uppercase tracking-tight">{t('cases.detail.createdAt')}</span>
                            <div className="flex items-center text-sm font-bold text-slate-800">
                                <Calendar className="w-3.5 h-3.5 mr-2 text-slate-300" />
                                {new Date(cse.created_at).toLocaleDateString()}
                            </div>
                        </div>
                        <div className="space-y-1.5">
                            <span className="text-[10px] text-slate-400 font-black uppercase tracking-tight">{t('cases.detail.dueDate')}</span>
                            <div className="flex items-center text-sm font-bold text-red-500">
                                <AlertTriangle className="w-3.5 h-3.5 mr-2 text-red-400" />
                                {new Date(cse.due_date).toLocaleDateString()}
                            </div>
                        </div>
                        <div className="space-y-1.5">
                            <span className="text-[10px] text-slate-400 font-black uppercase tracking-tight">{t('cases.filter.employee')}</span>
                            <p className="text-sm font-bold text-slate-800">{cse.related_employee?.user_name || '-'}</p>
                        </div>
                    </div>
                </div>

                {/* 관리자·감사팀: 직원 이력, 증거 보존 */}
                {(role === '보안관리자' || role === '감사팀' || role === '시스템관리자') && (
                    <CaseAdminPanel cse={cse} onUpdated={() => fetchCase(cse.case_id)} />
                )}

                {/* Request Details Card (Visible to everyone if NOT UNCLASSIFIED) */}
                {cse.case_status !== '미확인' && (cse.summary || (cse.attachments && cse.attachments.filter(a => !a.submission_id).length > 0)) && (
                    <div className="bg-white rounded-2xl border border-slate-100 p-8 shadow-sm">
                        <h3 className="text-base font-black text-slate-900 mb-6 flex items-center">
                            <AlertTriangle className="w-5 h-5 mr-2 text-indigo-500" />
                            {t('cases.detail.requestHistory')}
                        </h3>
                        <div className="bg-indigo-50/30 rounded-xl p-6 border border-indigo-100/50">
                            <div className="mb-4">
                                <span className="text-[10px] text-slate-400 font-black uppercase tracking-tight block mb-2">{t('cases.detail.requestReason')}</span>
                                <p className="text-sm text-slate-700 font-bold leading-relaxed">{cse.summary || t('cases.detail.noRequestReason')}</p>
                            </div>

                            {cse.attachments && cse.attachments.filter(a => !a.submission_id).length > 0 && (
                                <div className="mt-6 border-t border-indigo-100/50 pt-4">
                                    <span className="text-[10px] text-slate-400 font-black uppercase tracking-tight block mb-3">{t('cases.detail.adminAttachments')}</span>
                                    <div className="flex flex-wrap gap-2">
                                        {cse.attachments.filter(a => !a.submission_id).map(att => (
                                            <button
                                                key={att.file_id}
                                                onClick={() => handleDownload(att.file_id, att.original_filename)}
                                                className="flex items-center bg-white border border-slate-200 px-3 py-1.5 rounded-lg text-[10px] font-bold text-slate-600 hover:border-indigo-300 transition-colors group"
                                            >
                                                <Paperclip className="w-3 h-3 mr-2 text-slate-400 group-hover:text-indigo-500" />
                                                {att.original_filename}
                                                <Download className="w-3 h-3 ml-2 text-slate-300 opacity-0 group-hover:opacity-100 transition-opacity" />
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* Submission Content Card */}
                {cse.submissions && cse.submissions.length > 0 && (
                    <div className="bg-white rounded-2xl border border-slate-100 p-8 shadow-sm">
                        <h3 className="text-base font-black text-slate-900 mb-6">{t('cases.detail.submissionHeader')}</h3>
                        <div className="space-y-4">
                            {cse.submissions.map((sub) => (
                                <div key={sub.submission_id} className="bg-slate-50/50 rounded-xl p-6 border border-slate-100/50 relative">
                                    <div className="flex items-center justify-between mb-4">
                                        <span className="px-3 py-1 bg-white border border-slate-200 rounded text-[10px] font-black text-slate-500 uppercase">
                                            {sub.classification || 'BUSINESS'}
                                        </span>
                                        <span className="text-[10px] font-bold text-slate-400">
                                            {new Date(sub.submitted_at).toLocaleString()}
                                        </span>
                                    </div>
                                    <p className="text-sm text-slate-700 font-bold leading-relaxed">{sub.content}</p>

                                    {sub.attachments && sub.attachments.length > 0 && (
                                        <div className="mt-6 flex flex-wrap gap-2">
                                            {sub.attachments.map(att => (
                                                <button
                                                    key={att.file_id}
                                                    onClick={() => handleDownload(att.file_id, att.original_filename)}
                                                    className="flex items-center bg-white border border-slate-200 px-3 py-1.5 rounded-lg text-[10px] font-bold text-slate-600 hover:border-sky-300 transition-colors group"
                                                >
                                                    <Paperclip className="w-3 h-3 mr-2 text-slate-400 group-hover:text-sky-500" />
                                                    {att.original_filename}
                                                    <Download className="w-3 h-3 ml-2 text-slate-300 opacity-0 group-hover:opacity-100 transition-opacity" />
                                                </button>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Review Results Card */}
                {(cse.case_status === '승인' || cse.case_status === '반려' || cse.case_status === '종결') && (
                    <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
                        <div className="p-12 flex flex-col items-center border-b border-slate-50 bg-slate-50/30">
                            <div className={`w-16 h-16 rounded-full flex items-center justify-center mb-6 shadow-sm
                                ${cse.case_status === '반려' ? 'bg-red-50' : 'bg-green-50'}`}>
                                {cse.case_status === '반려' ? (
                                    <div className="w-10 h-10 border-4 border-red-500 rounded-full flex items-center justify-center">
                                        <div className="w-6 h-1 bg-red-500 rotate-45 absolute"></div>
                                        <div className="w-6 h-1 bg-red-500 -rotate-45 absolute"></div>
                                    </div>
                                ) : (
                                    <CheckCircle2 className="w-10 h-10 text-green-500" />
                                )}
                            </div>
                            <h2 className="text-2xl font-black text-slate-900 mb-3">{t('cases.detail.reviewResultTitle', { status: cse.case_status })}</h2>
                            <p className="text-sm text-slate-500 font-bold text-center">
                                {cse.case_status === '반려'
                                    ? t('cases.detail.reviewRejected')
                                    : t('cases.detail.reviewApproved')}
                            </p>
                        </div>

                        <div className="p-8 space-y-6">
                            <div className="flex items-center justify-between">
                                <div className="space-y-1">
                                    <span className="text-[10px] text-slate-400 font-black uppercase">{t('cases.detail.reviewStatus')}</span>
                                    <p className="font-black text-slate-900 text-lg">{cse.case_result || t('common.needsEducation')}</p>
                                </div>
                                <div className="flex items-center space-x-6">
                                    <div className="text-right space-y-1">
                                        <span className="text-[10px] text-slate-400 font-black uppercase">{t('cases.detail.reviewDate')}</span>
                                        <p className="text-xs font-bold text-slate-600">{cse.final_review_date ? new Date(cse.final_review_date).toLocaleDateString() : '2026. 2. 6.'}</p>
                                    </div>
                                    <div className="text-right space-y-1">
                                        <span className="text-[10px] text-slate-400 font-black uppercase">{t('cases.detail.reviewer')}</span>
                                        <p className="text-xs font-bold text-slate-600 font-mono">{cse.reviewer_name || t('system.user.roles.security_admin')}</p>
                                    </div>
                                </div>
                            </div>

                            <div className="bg-slate-50 rounded-xl p-6 border border-slate-100">
                                <div className="mb-4">
                                    <span className="px-3 py-1 bg-red-50 border border-red-100 rounded text-[10px] font-black text-red-500">
                                        {getCloseResultLabel(cse.case_result || t('common.needsEducation'))}
                                    </span>
                                </div>
                                <p className="text-sm text-slate-700 font-bold leading-relaxed">
                                    {cse.review_comment || t('cases.detail.reviewCompleted')}
                                </p>
                            </div>
                        </div>
                    </div>
                )}

                {/* Rejection Handling Section (세부 처리 방안 A, B, C) */}
                {cse.case_status === '반려' && (
                    <div className="space-y-6">
                        {/* 방안 A: 소명 불충분 - 보완 소명서 재작성 및 제출 */}
                        {(cse.case_result === '소명 불충분' || (!cse.case_result && !['교육 필요', '징계 요청'].includes(cse.case_result || ''))) && (
                            <div className="bg-amber-50/70 border border-amber-200 rounded-2xl p-6 shadow-sm">
                                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                                    <div className="flex items-start space-x-3.5">
                                        <div className="p-2.5 bg-amber-100 text-amber-700 rounded-xl mt-0.5 shrink-0">
                                            <RotateCcw className="w-5 h-5" />
                                        </div>
                                        <div>
                                            <h4 className="text-base font-black text-amber-950 mb-1">
                                                {t('cases.detail.rejection.resubmitTitle')}
                                            </h4>
                                            <p className="text-xs text-amber-800 leading-relaxed max-w-xl font-medium">
                                                {t('cases.detail.rejection.resubmitDesc')}
                                            </p>
                                        </div>
                                    </div>
                                    <button
                                        onClick={() => setShowResubmitForm(prev => !prev)}
                                        className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-xl text-xs font-bold transition-colors shadow-sm flex items-center justify-center space-x-1.5 shrink-0 self-start sm:self-auto"
                                    >
                                        <RotateCcw className="w-3.5 h-3.5 mr-1" />
                                        <span>{showResubmitForm ? t('cases.detail.rejection.btnCloseResubmit') : t('cases.detail.rejection.btnOpenResubmit')}</span>
                                    </button>
                                </div>

                                {showResubmitForm && (
                                    <div className="mt-6 pt-6 border-t border-amber-200">
                                        <div className="mb-4 text-xs font-bold text-amber-900 bg-amber-100/60 p-3 rounded-lg border border-amber-200/80">
                                            {t('cases.detail.rejection.resubmitNotice')}
                                        </div>
                                        <SmartSubmissionForm
                                            currentCase={cse}
                                            onSubmit={handleSubmit}
                                            isSubmitting={submitting}
                                        />
                                    </div>
                                )}
                            </div>
                        )}

                        {/* 방안 B: 교육 필요 - 보안 교육 안내 및 서약서 */}
                        {cse.case_result === '교육 필요' && (
                            <div className="bg-indigo-50/70 border border-indigo-200 rounded-2xl p-6 shadow-sm">
                                <div className="flex items-start space-x-3.5 mb-5">
                                    <div className="p-2.5 bg-indigo-100 text-indigo-700 rounded-xl mt-0.5 shrink-0">
                                        <ShieldCheck className="w-5 h-5" />
                                    </div>
                                    <div>
                                        <h4 className="text-base font-black text-indigo-950 mb-1">
                                            {t('cases.detail.rejection.educationTitle')}
                                        </h4>
                                        <p className="text-xs text-indigo-800 leading-relaxed max-w-xl font-medium">
                                            {t('cases.detail.rejection.educationDesc')}
                                        </p>
                                    </div>
                                </div>

                                <div className="bg-white rounded-xl p-5 border border-indigo-100 mb-5 space-y-3">
                                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs font-bold text-slate-800">
                                        <span className="flex items-center">
                                            <FileText className="w-4 h-4 mr-2 text-indigo-500 shrink-0" />
                                            {t('cases.detail.rejection.guidelineTitle')}
                                        </span>
                                        <a
                                            href="#policy"
                                            onClick={(e) => { e.preventDefault(); alert(t('cases.detail.rejection.guidelineAlert')); }}
                                            className="text-indigo-600 hover:text-indigo-800 flex items-center font-bold text-xs"
                                        >
                                            <span>{t('cases.detail.rejection.educationLink')}</span>
                                            <ExternalLink className="w-3.5 h-3.5 ml-1" />
                                        </a>
                                    </div>
                                    <p className="text-[11px] text-slate-600 leading-relaxed bg-slate-50 p-3 rounded-lg border border-slate-100">
                                        {t('cases.detail.rejection.guidelineContent')}
                                    </p>
                                </div>

                                {pledgeSubmitted ? (
                                    <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 flex items-center space-x-3 text-emerald-800 text-xs font-bold">
                                        <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                                        <span>{t('cases.detail.rejection.pledgeCompleted')}</span>
                                    </div>
                                ) : (
                                    <div className="space-y-4 pt-1">
                                        <label className="flex items-start space-x-3 cursor-pointer">
                                            <input
                                                type="checkbox"
                                                checked={pledgeAgreed}
                                                onChange={(e) => setPledgeAgreed(e.target.checked)}
                                                className="w-4 h-4 mt-0.5 rounded border-indigo-300 text-indigo-600 focus:ring-indigo-500"
                                            />
                                            <span className="text-xs font-bold text-slate-800 select-none leading-relaxed">
                                                {t('cases.detail.rejection.pledgeCheckbox')}
                                            </span>
                                        </label>
                                        <button
                                            disabled={!pledgeAgreed}
                                            onClick={() => {
                                                setPledgeSubmitted(true);
                                                alert(t('cases.detail.rejection.pledgeAlert'));
                                            }}
                                            className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white rounded-xl text-xs font-bold transition-colors shadow-sm"
                                        >
                                            {t('cases.detail.rejection.btnPledgeSubmit')}
                                        </button>
                                    </div>
                                )}
                            </div>
                        )}

                        {/* 방안 C: 징계 요청 - 보안감사팀 및 인사위원회 이관 안내 & 감사 보고서 출력 */}
                        {cse.case_result === '징계 요청' && (
                            <div className="bg-red-50/70 border border-red-200 rounded-2xl p-6 shadow-sm">
                                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 mb-5">
                                    <div className="flex items-start space-x-3.5">
                                        <div className="p-2.5 bg-red-100 text-red-700 rounded-xl mt-0.5 shrink-0">
                                            <AlertOctagon className="w-5 h-5" />
                                        </div>
                                        <div>
                                            <h4 className="text-base font-black text-red-950 mb-1">
                                                {t('cases.detail.rejection.disciplinaryTitle')}
                                            </h4>
                                            <p className="text-xs text-red-800 leading-relaxed max-w-xl font-medium">
                                                {t('cases.detail.rejection.disciplinaryDesc')}
                                            </p>
                                        </div>
                                    </div>
                                    <button
                                        onClick={() => window.print()}
                                        className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-bold transition-colors shadow-sm flex items-center justify-center space-x-1.5 shrink-0 self-start sm:self-auto print:hidden"
                                    >
                                        <Printer className="w-3.5 h-3.5 mr-1" />
                                        <span>{t('cases.detail.rejection.btnPrintAuditReport')}</span>
                                    </button>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
                                    <div className="bg-white/90 p-3.5 rounded-xl border border-red-100 shadow-2xs">
                                        <div className="text-[10px] font-black text-red-500 uppercase tracking-wider mb-1">{t('cases.detail.rejection.statusHeading')}</div>
                                        <div className="text-xs font-bold text-slate-800">{t('cases.detail.rejection.step1')}</div>
                                    </div>
                                    <div className="bg-white/90 p-3.5 rounded-xl border border-red-100 shadow-2xs">
                                        <div className="text-[10px] font-black text-slate-400 uppercase tracking-wider mb-1">{t('cases.detail.rejection.nextHeading')}</div>
                                        <div className="text-xs font-bold text-slate-700">{t('cases.detail.rejection.step2')}</div>
                                    </div>
                                    <div className="bg-white/90 p-3.5 rounded-xl border border-red-100 shadow-2xs">
                                        <div className="text-[10px] font-black text-slate-400 uppercase tracking-wider mb-1">{t('cases.detail.rejection.finalHeading')}</div>
                                        <div className="text-xs font-bold text-slate-700">{t('cases.detail.rejection.step3')}</div>
                                    </div>
                                </div>

                                <p className="text-[11px] font-bold text-red-700 bg-red-100/60 px-3.5 py-2.5 rounded-lg border border-red-200">
                                    ※ {t('cases.detail.rejection.disciplinaryNotice')}
                                </p>
                            </div>
                        )}
                    </div>
                )}

                {/* Initial Unconfirmed State */}
                {cse.case_status === '미확인' && (role === '보안관리자' || role === '감사팀' || role === '시스템관리자') && (
                    <div className="bg-white rounded-2xl border border-slate-100 p-12 shadow-sm text-center">
                        <div className="mx-auto w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mb-6">
                            <AlertTriangle className="w-8 h-8 text-slate-300" />
                        </div>
                        <h3 className="text-xl font-black text-slate-900 mb-3">{t('cases.detail.unconfirmedState')}</h3>
                        <p className="text-sm text-slate-400 font-bold mb-8 max-w-sm mx-auto leading-relaxed">
                            {t('cases.detail.unconfirmedDesc')}
                        </p>
                        <div className="flex justify-center space-x-3">
                            <button
                                onClick={() => setShowRequestModal(true)}
                                className="px-6 py-2.5 bg-slate-900 text-white text-sm font-bold rounded-xl hover:bg-slate-800 transition-colors shadow-lg shadow-slate-200"
                            >
                                {t('cases.detail.btnRequest')}
                            </button>
                            <button
                                onClick={() => setShowCloseModal(true)}
                                className="px-6 py-2.5 border border-slate-200 text-slate-600 text-sm font-bold bg-white rounded-xl hover:bg-slate-50 transition-colors"
                            >
                                {t('cases.detail.btnClose')}
                            </button>
                        </div>
                    </div>
                )}

                {/* Submission Form for Requested State */}
                {cse.case_status === '요청' && (
                    <SmartSubmissionForm
                        currentCase={cse}
                        onSubmit={handleSubmit}
                        isSubmitting={submitting}
                    />
                )}
            </div>

            {/* Modals... */}
            {/* ... Modal implementations remain largely same but with refined styling ... */}
            {/* (Hiding modal code for brevity in this replace unless needed, but I should probably keep them) */}
            {/* Retaining existing modals for functional completeness */}

            {
                showRequestModal && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
                        <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full overflow-hidden border border-slate-100">
                            <div className="px-8 py-6 border-b border-slate-50 flex justify-between items-center bg-slate-50/50">
                                <h3 className="font-black text-lg text-slate-900 flex items-center">
                                    {t('cases.detail.modalRequestTitle')}
                                    <span className="ml-3 px-2 py-0.5 bg-slate-200 text-slate-500 text-[10px] rounded uppercase tracking-wider font-black">{t('cases.detail.step', { current: requestModalStep, total: 2 })}</span>
                                </h3>
                                <button onClick={() => { setShowRequestModal(false); setRequestModalStep(1); }} className="text-slate-400 hover:text-slate-600 transition-colors">
                                    <XCircle className="w-6 h-6" />
                                </button>
                            </div>

                            {/* Case info summary: Simplified and integrated to match overall UI */}
                            <div className="px-8 py-5 bg-white border-b border-slate-100 flex justify-between items-center">
                                <div className="space-y-1 flex-1 min-w-0">
                                    <div className="flex items-center space-x-2">
                                        <span className={`px-2 py-0.5 rounded-[4px] text-[10px] font-black border tracking-tight
                                            ${cse.priority === '높음' ? 'bg-red-50 text-red-600 border-red-100' :
                                                cse.priority === '보통' ? 'bg-orange-50 text-orange-600 border-orange-100' :
                                                    'bg-slate-50 text-slate-400 border-slate-100'}`}>
                                            {cse.priority}
                                        </span>
                                        <span className="text-[10px] font-bold text-slate-400 font-mono">#{cse.incident_num || cse.case_id}</span>
                                    </div>
                                    <h4 className="text-base font-black text-slate-900 truncate">{cse.rule_title}</h4>
                                </div>
                                <div className="ml-8 pl-8 border-l border-slate-100 flex flex-col justify-center text-right shrink-0">
                                    <span className="text-[10px] text-slate-400 font-black uppercase mb-1 tracking-tight">{t('cases.filter.employee')}</span>
                                    <p className="text-sm font-black text-slate-800">{cse.related_employee?.user_name || '-'}</p>
                                </div>
                            </div>

                            <div className="p-8 space-y-6">
                                {requestModalStep === 1 ? (
                                    <>
                                        <div>
                                            <label className="block text-[11px] font-black text-slate-500 uppercase mb-2">{t('cases.detail.dueDate')} <span className="text-red-500">*</span></label>
                                            <input
                                                type="date"
                                                value={requestDueDate}
                                                onChange={(e) => setRequestDueDate(e.target.value)}
                                                className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-sky-500 font-bold bg-slate-50/50"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-[11px] font-black text-slate-500 uppercase mb-2">{t('cases.detail.requestReason')} <span className="text-red-500">*</span></label>
                                            <textarea
                                                value={requestReason}
                                                onChange={(e) => setRequestReason(e.target.value)}
                                                className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-sky-500 min-h-[140px] font-bold bg-slate-50/50"
                                                placeholder={t('cases.detail.placeholderReason')}
                                            />
                                        </div>
                                    </>
                                ) : (
                                    <div>
                                        <label className="block text-[11px] font-black text-slate-500 uppercase mb-2">{t('cases.detail.adminAttachments')}</label>
                                        <div
                                            className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer relative group
                                            ${dragActive ? 'border-sky-500 bg-sky-50' : 'border-slate-200 hover:bg-slate-50'}`}
                                            onDragEnter={handleDrag}
                                            onDragLeave={handleDrag}
                                            onDragOver={handleDrag}
                                            onDrop={handleDrop}
                                        >
                                            <input
                                                type="file"
                                                multiple
                                                onChange={handleFileChange}
                                                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                                            />
                                            <Upload className={`w-6 h-6 mx-auto mb-3 transition-colors ${dragActive ? 'text-sky-500' : 'text-slate-300 group-hover:text-sky-500'}`} />
                                            <p className="text-[11px] text-slate-500 font-black uppercase tracking-tight">
                                                {dragActive ? t('cases.detail.dropFile') : t('cases.detail.selectFile')}
                                            </p>
                                        </div>
                                        {requestFiles.length > 0 && (
                                            <div className="mt-4 space-y-2 max-h-[150px] overflow-y-auto pr-2 custom-scrollbar">
                                                {requestFiles.map((file, index) => (
                                                    <div key={index} className="flex items-center justify-between text-[11px] bg-slate-50/50 px-3 py-2 rounded-lg border border-slate-100 animate-in fade-in slide-in-from-top-1">
                                                        <span className="truncate max-w-[200px] font-bold text-slate-600">{file.name}</span>
                                                        <button onClick={() => removeFile(index)} className="text-red-400 hover:text-red-500 transition-colors">
                                                            <XCircle className="w-3.5 h-3.5" />
                                                        </button>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                        {requestFiles.length === 0 && (
                                            <p className="mt-4 text-[10px] text-slate-400 font-bold text-center">{t('cases.detail.noFiles')}</p>
                                        )}
                                    </div>
                                )}
                            </div>
                            <div className="px-8 py-6 bg-slate-50 flex justify-end space-x-3">
                                {requestModalStep === 1 ? (
                                    <>
                                        <button
                                            onClick={() => setShowRequestModal(false)}
                                            className="px-6 py-2.5 text-slate-500 font-bold text-sm"
                                        >
                                            {t('cases.detail.btnCancel')}
                                        </button>
                                        <button
                                            onClick={() => {
                                                if (!requestDueDate || !requestReason) {
                                                    alert(t('cases.detail.alerts.requestRequirement'));
                                                    return;
                                                }
                                                setRequestModalStep(2);
                                            }}
                                            className="px-6 py-2.5 bg-slate-900 text-white rounded-xl text-sm font-bold shadow-lg shadow-slate-200"
                                        >
                                            {t('cases.detail.btnNext')}
                                        </button>
                                    </>
                                ) : (
                                    <>
                                        <button
                                            onClick={() => setRequestModalStep(1)}
                                            className="px-6 py-2.5 text-slate-500 font-bold text-sm"
                                        >
                                            {t('cases.detail.btnPrev')}
                                        </button>
                                        <button
                                            onClick={handleRequestSubmit}
                                            className="px-6 py-2.5 bg-sky-600 text-white rounded-xl text-sm font-bold shadow-lg shadow-sky-100"
                                        >
                                            {t('cases.detail.btnSubmitRequest')}
                                        </button>
                                    </>
                                )}
                            </div>
                        </div>
                    </div>
                )
            }

            {
                showCloseModal && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
                        <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full overflow-hidden border border-slate-100">
                            <div className="px-8 py-6 border-b border-slate-50 flex justify-between items-center bg-slate-50/50">
                                <h3 className="font-black text-lg text-slate-900">{t('cases.detail.modalCloseTitle')}</h3>
                                <button onClick={() => setShowCloseModal(false)} className="text-slate-400 hover:text-slate-600 transition-colors">
                                    <XCircle className="w-6 h-6" />
                                </button>
                            </div>

                            {/* Case info summary: Simplified and integrated to match overall UI */}
                            <div className="px-8 py-5 bg-white border-b border-slate-100 flex justify-between items-center">
                                <div className="space-y-1 flex-1 min-w-0">
                                    <div className="flex items-center space-x-2">
                                        <span className={`px-2 py-0.5 rounded-[4px] text-[10px] font-black border tracking-tight
                                            ${cse.priority === '높음' ? 'bg-red-50 text-red-600 border-red-100' :
                                                cse.priority === '보통' ? 'bg-orange-50 text-orange-600 border-orange-100' :
                                                    'bg-slate-50 text-slate-400 border-slate-100'}`}>
                                            {cse.priority}
                                        </span>
                                        <span className="text-[10px] font-bold text-slate-400 font-mono">#{cse.incident_num || cse.case_id}</span>
                                    </div>
                                    <h4 className="text-base font-black text-slate-900 truncate">{cse.rule_title}</h4>
                                </div>
                                <div className="ml-8 pl-8 border-l border-slate-100 flex flex-col justify-center text-right shrink-0">
                                    <span className="text-[10px] text-slate-400 font-black uppercase mb-1 tracking-tight">{t('cases.filter.employee')}</span>
                                    <p className="text-sm font-black text-slate-800">{cse.related_employee?.user_name || '-'}</p>
                                </div>
                            </div>

                            <div className="p-8 space-y-6">
                                <div>
                                    <label className="block text-[10px] font-black text-slate-400 uppercase mb-2">{t('cases.detail.modal.closeResult')} <span className="text-red-500">*</span></label>
                                    <select
                                        value={closeResult}
                                        onChange={(e) => setCloseResult(e.target.value)}
                                        className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-sky-500 bg-slate-50/50 font-bold"
                                    >
                                        <option value="오탐">{t('cases.detail.modal.falsePositive')}</option>
                                        <option value="정당 사유">{t('cases.detail.modal.justified')}</option>
                                        <option value="경미한 위반">{t('cases.detail.modal.minorViolation')}</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-[10px] font-black text-slate-400 uppercase mb-2">{t('cases.detail.closeReason')} <span className="text-red-500">*</span></label>
                                    <textarea
                                        value={closeReason}
                                        onChange={(e) => setCloseReason(e.target.value)}
                                        className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-sky-500 min-h-[120px] font-bold bg-slate-50/50"
                                        placeholder={t('cases.detail.placeholderReason')}
                                    />
                                </div>
                            </div>
                            <div className="px-8 py-6 bg-slate-50 flex justify-end space-x-3">
                                <button
                                    onClick={() => setShowCloseModal(false)}
                                    className="px-6 py-2.5 text-slate-500 font-bold text-sm"
                                >
                                    {t('cases.detail.btnCancel')}
                                </button>
                                <button
                                    onClick={handleCloseSubmit}
                                    className="px-6 py-2.5 bg-slate-900 text-white rounded-xl text-sm font-bold shadow-lg shadow-slate-200"
                                >
                                    {t('cases.detail.btnSubmitClose')}
                                </button>
                            </div>
                        </div>
                    </div>
                )
            }
        </div >
    );
};

export default CaseDetail;
