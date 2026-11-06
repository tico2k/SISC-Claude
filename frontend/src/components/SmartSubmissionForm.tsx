import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Case } from '../types';
import { caseService } from '../services/case.service';
import { validateFiles } from '../utils/fileValidation';
import {
    AlertCircle,
    CheckCircle2,
    FileText,
    History,
    Briefcase,
    AlertTriangle,
    Send,
    XCircle
} from 'lucide-react';

interface SmartSubmissionFormProps {
    currentCase: Case;
    onSubmit: (content: string, classification: string, files: File[]) => Promise<void>;
    isSubmitting: boolean;
}

const SmartSubmissionForm: React.FC<SmartSubmissionFormProps> = ({ currentCase, onSubmit, isSubmitting }) => {
    const { t } = useTranslation();

    const SUBMISSION_TYPES = [
        {
            id: 'MISTAKE',
            label: t('submission.types.mistake.label'),
            description: t('submission.types.mistake.desc'),
            icon: AlertCircle,
            guide: t('submission.types.mistake.guide'),
            template: t('submission.types.mistake.template')
        },
        {
            id: 'BUSINESS',
            label: t('submission.types.business.label'),
            description: t('submission.types.business.desc'),
            icon: Briefcase,
            guide: t('submission.types.business.guide'),
            template: t('submission.types.business.template')
        },
        {
            id: 'PRE_APPROVED',
            label: t('submission.types.preApproved.label'),
            description: t('submission.types.preApproved.desc'),
            icon: FileText,
            guide: t('submission.types.preApproved.guide'),
            template: t('submission.types.preApproved.template')
        },
        {
            id: 'MISTAKE_ACTUAL',
            label: t('submission.types.neglect.label'),
            description: t('submission.types.neglect.desc'),
            icon: AlertTriangle,
            guide: t('submission.types.neglect.guide'),
            template: t('submission.types.neglect.template')
        }
    ];

    const [step, setStep] = useState<1 | 2>(1);
    const [selectedType, setSelectedType] = useState<string | null>(null);
    const [content, setContent] = useState('');
    const [files, setFiles] = useState<File[]>([]);
    const [historyMatch, setHistoryMatch] = useState<Case | null>(null);
    const [loadingHistory, setLoadingHistory] = useState(true);

    useEffect(() => {
        checkHistory();
    }, [currentCase]);

    const checkHistory = async () => {
        try {
            const history = await caseService.getCaseHistory();
            // Simple logic: find approved case with same rule title
            const match = history.find(c => c.rule_title === currentCase.rule_title && c.case_id !== currentCase.case_id);
            if (match) {
                setHistoryMatch(match);
            }
        } catch (err) {
            console.error(err);
        } finally {
            setLoadingHistory(false);
        }
    };

    const handleTypeSelect = (typeId: string) => {
        setSelectedType(typeId);
        const type = SUBMISSION_TYPES.find(t => t.id === typeId);
        if (type) {
            setContent(type.template);
        }
        setStep(2);
    };

    const handleHistoryApply = () => {
        if (!historyMatch) return;
        setSelectedType('BUSINESS'); // Defaulting to business for history match
        setContent(`${t('submission.historyReasonPrefix')}\n${t('submission.historyReasonBody', { id: historyMatch.case_id, title: historyMatch.rule_title })}\n\n${historyMatch.summary || ''}`);
        setStep(2);
    };

    const [dragActive, setDragActive] = useState(false);

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
        setDragActive(false);
        const droppedFiles = Array.from(e.dataTransfer.files);

        // 파일 검증
        const validation = validateFiles(droppedFiles);
        if (!validation.valid) {
            alert(validation.error || t('cases.detail.alerts.fileValidationFail'));
            return;
        }

        setFiles(prev => [...prev, ...droppedFiles]);
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

            setFiles(prev => [...prev, ...newFiles]);
        }
    };

    const removeFile = (index: number) => {
        setFiles(prev => prev.filter((_, i) => i !== index));
    };

    return (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
            {/* ... header ... */}
            <div className="bg-slate-50 border-b border-slate-200 px-6 py-4 flex items-center justify-between">
                <h2 className="text-lg font-bold text-slate-900 flex items-center">
                    <CheckCircle2 className="w-5 h-5 mr-2 text-sky-600" />
                    {t('submission.assistant')}
                </h2>
                <span className="text-xs font-medium text-slate-500 bg-slate-200 px-2 py-1 rounded">
                    {t('cases.detail.step', { current: step, total: 2 })}
                </span>
            </div>

            <div className="p-6">
                {step === 1 && (
                    <div className="space-y-6">
                        {loadingHistory ? (
                            <div className="text-center py-4 text-slate-500 text-sm">{t('submission.analyzing')}</div>
                        ) : historyMatch && (
                            <div className="bg-sky-50 border border-sky-200 rounded-lg p-4 flex items-start">
                                <History className="w-5 h-5 text-sky-600 mt-0.5 mr-3 flex-shrink-0" />
                                <div>
                                    <h4 className="font-semibold text-sky-900 text-sm mb-1">{t('submission.historyFound')}</h4>
                                    <p className="text-sm text-sky-800 mb-3">
                                        {t('submission.historyDesc', { id: historyMatch.case_id })}
                                    </p>
                                    <button
                                        onClick={handleHistoryApply}
                                        className="text-xs bg-sky-600 text-white px-3 py-1.5 rounded hover:bg-sky-700 transition"
                                    >
                                        {t('submission.btnLoadHistory')}
                                    </button>
                                </div>
                            </div>
                        )}

                        <div className="text-center mb-6">
                            <h3 className="text-lg font-medium text-slate-800">{t('submission.selectType')}</h3>
                            <p className="text-sm text-slate-500 mt-1">{t('submission.selectTypeDesc')}</p>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {SUBMISSION_TYPES.map((type) => (
                                <button
                                    key={type.id}
                                    onClick={() => handleTypeSelect(type.id)}
                                    className="flex items-start p-4 border border-slate-200 rounded-xl hover:border-sky-500 hover:bg-sky-50 transition-all text-left group"
                                >
                                    <div className="p-2 bg-slate-100 rounded-lg mr-4 group-hover:bg-sky-200 transition-colors">
                                        <type.icon className="w-6 h-6 text-slate-600 group-hover:text-sky-700" />
                                    </div>
                                    <div>
                                        <div className="font-semibold text-slate-900 group-hover:text-sky-700">{type.label}</div>
                                        <div className="text-xs text-slate-500 mt-1">{type.description}</div>
                                    </div>
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {step === 2 && selectedType && (
                    <div className="space-y-6">
                        <div className="bg-slate-50 rounded-lg p-5 border border-slate-200">
                            <div className="flex items-center mb-2">
                                <div className="p-1.5 bg-sky-100 rounded mr-2">
                                    {React.createElement(SUBMISSION_TYPES.find(t => t.id === selectedType)?.icon || FileText, { className: "w-4 h-4 text-sky-600" })}
                                </div>
                                <h3 className="font-semibold text-slate-900">
                                    {SUBMISSION_TYPES.find(t => t.id === selectedType)?.label} {t('submission.guideTitle')}
                                </h3>
                            </div>
                            <p className="text-sm text-slate-600 leading-relaxed pl-8">
                                {SUBMISSION_TYPES.find(t => t.id === selectedType)?.guide}
                            </p>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-2">
                                {t('submission.contentLabel')}
                            </label>
                            <textarea
                                value={content}
                                onChange={(e) => setContent(e.target.value)}
                                rows={10}
                                className="block w-full rounded-lg border-slate-300 shadow-sm focus:border-sky-500 focus:ring-sky-500 sm:text-sm p-4 border"
                                placeholder={t('submission.placeholderContent')}
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-2">
                                {t('submission.attachmentLabel')}
                            </label>
                            <div
                                className={`mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-dashed rounded-lg transition-colors relative group
                                    ${dragActive ? 'border-sky-500 bg-sky-50' : 'border-slate-300 hover:border-sky-500'}`}
                                onDragEnter={handleDrag}
                                onDragLeave={handleDrag}
                                onDragOver={handleDrag}
                                onDrop={handleDrop}
                            >
                                <div className="space-y-1 text-center pointer-events-none">
                                    <FileText className={`mx-auto h-12 w-12 ${dragActive ? 'text-sky-500' : 'text-slate-400 group-hover:text-sky-500'}`} />
                                    <div className="flex text-sm text-slate-600 justify-center">
                                        <span className="font-medium text-sky-600 group-hover:text-sky-500">
                                            {t('cases.detail.selectFile')}
                                        </span>
                                        <p className="pl-1">{t('common.or')} {t('cases.detail.dropFile')}</p>
                                    </div>
                                    <p className="text-xs text-slate-500">
                                        PNG, JPG, PDF, DOCX up to 10MB
                                    </p>
                                </div>
                                <label
                                    htmlFor="file-upload"
                                    className="absolute inset-0 w-full h-full cursor-pointer"
                                >
                                    <input
                                        id="file-upload"
                                        name="file-upload"
                                        type="file"
                                        className="sr-only"
                                        multiple
                                        onChange={handleFileChange}
                                    />
                                </label>
                            </div>
                            {files.length > 0 && (
                                <ul className="mt-4 space-y-2">
                                    {files.map((file, index) => (
                                        <li key={index} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg border border-slate-200">
                                            <div className="flex items-center">
                                                <FileText className="w-5 h-5 text-slate-400 mr-3" />
                                                <div>
                                                    <p className="text-sm font-medium text-slate-700 truncate max-w-xs">{file.name}</p>
                                                    <p className="text-xs text-slate-500">{(file.size / 1024).toFixed(1)} KB</p>
                                                </div>
                                            </div>
                                            <button
                                                type="button"
                                                onClick={() => removeFile(index)}
                                                className="text-slate-400 hover:text-red-500 transition-colors"
                                            >
                                                <XCircle className="w-5 h-5" />
                                            </button>
                                        </li>
                                    ))}
                                </ul>
                            )}
                        </div>

                        <div className="flex justify-between pt-4">
                            <button
                                type="button"
                                onClick={() => setStep(1)}
                                className="text-slate-500 hover:text-slate-900 text-sm font-medium px-4 py-2"
                            >
                                {t('cases.detail.btnPrev')}
                            </button>
                            <button
                                onClick={() => onSubmit(content, selectedType, files)}
                                disabled={isSubmitting || !content.trim()}
                                className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-lg shadow-sm text-white bg-sky-600 hover:bg-sky-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-sky-500 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {isSubmitting ? t('submission.submitting') : (
                                    <>
                                        {t('submission.btnSubmit')}
                                        <Send className="w-4 h-4 ml-2" />
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default SmartSubmissionForm;
