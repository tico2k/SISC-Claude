import React, { useState, useEffect, useMemo } from 'react';
import { systemService, EnvResponse, EnvEntry } from '../services/system.service';
import { Lock, AlertTriangle, RefreshCw, CheckCircle2, ChevronDown, ChevronRight } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';

const EnvManagement: React.FC = () => {
    const { t } = useTranslation();
    const { user } = useAuth();
    const [envData, setEnvData] = useState<EnvResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState<string | null>(null); // key of what's being saved
    const [editMode, setEditMode] = useState<{ file: 'backend' | 'frontend', key: string } | null>(null);
    const [editValue, setEditValue] = useState('');
    const [expandedCategories, setExpandedCategories] = useState<Record<string, boolean>>({});

    const fetchEnv = async () => {
        try {
            setLoading(true);
            const data = await systemService.getEnv();
            setEnvData(data);

            // Initialize all categories as expanded
            const cats: Record<string, boolean> = {};
            [...data.backend, ...data.frontend].forEach(e => {
                cats[e.category] = true;
            });
            setExpandedCategories(cats);
        } catch (error) {
            console.error('Failed to fetch env:', error);
            alert(t('env.fetchFail'));
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchEnv();
    }, []);

    const groupedData = useMemo(() => {
        if (!envData) return { backend: {}, frontend: {} };

        const group = (entries: EnvEntry[]) => {
            return entries.reduce((acc, entry) => {
                if (!acc[entry.category]) acc[entry.category] = [];
                acc[entry.category].push(entry);
                return acc;
            }, {} as Record<string, EnvEntry[]>);
        };

        return {
            backend: group(envData.backend),
            frontend: group(envData.frontend)
        };
    }, [envData]);

    const handleEdit = (file: 'backend' | 'frontend', entry: EnvEntry) => {
        if (entry.is_sensitive) {
            if (!confirm(t('env.sensitiveConfirm'))) {
                return;
            }
            setEditValue('');
        } else {
            setEditValue(entry.value);
        }
        setEditMode({ file, key: entry.key });
    };

    const handleSave = async () => {
        if (!editMode || !envData) return;

        try {
            setSaving(editMode.key);
            await systemService.updateEnv(editMode.file, editMode.key, editValue);

            await fetchEnv();
            setEditMode(null);
            alert(t('env.saveSuccess'));
        } catch (error) {
            console.error('Failed to update env:', error);
            alert(t('env.saveFail'));
        } finally {
            setSaving(null);
        }
    };

    const toggleCategory = (cat: string) => {
        setExpandedCategories(prev => ({
            ...prev,
            [cat]: !prev[cat]
        }));
    };

    if (loading && !envData) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[400px]">
                <RefreshCw className="w-8 h-8 text-sky-500 animate-spin mb-4" />
                <p className="text-slate-500 font-bold">{t('env.loading')}</p>
            </div>
        );
    }

    const getCategoryName = (category: string) => {
        const translated = t(`env.categories.${category}`);
        if (translated && translated !== `env.categories.${category}`) {
            return translated;
        }

        const mapping: Record<string, string> = {
            '일반': t('env.categories.general'),
            '데이터베이스': t('env.categories.database'),
            '보안': t('env.categories.security'),
            'SIEM': t('env.categories.siem'),
            '이메일': t('env.categories.email'),
            '인증': t('env.categories.auth'),
            '시스템': t('env.categories.system'),
            'General': t('env.categories.general'),
            'Database': t('env.categories.database'),
            'Security': t('env.categories.security'),
            'Email': t('env.categories.email'),
            'Auth': t('env.categories.auth'),
            'System': t('env.categories.system')
        };
        return mapping[category] || category;
    };

    const getKeyDescription = (key: string, defaultDesc?: string) => {
        const translated = t(`env.keys.${key}`);
        if (translated && translated !== `env.keys.${key}`) {
            return translated;
        }
        return defaultDesc || '';
    };

    const renderCategorySection = (file: 'backend' | 'frontend', category: string, entries: EnvEntry[]) => {
        const isExpanded = expandedCategories[category] !== false;

        return (
            <div key={`${file}-${category}`} className="mb-6 last:mb-0">
                <button
                    onClick={() => toggleCategory(category)}
                    className="w-full flex items-center px-4 py-3 bg-white border border-slate-100 rounded-xl hover:bg-slate-50 transition-colors shadow-sm mb-2"
                >
                    {isExpanded ? <ChevronDown className="w-4 h-4 text-slate-400 mr-2" /> : <ChevronRight className="w-4 h-4 text-slate-400 mr-2" />}
                    <h4 className="text-sm font-bold text-slate-800 uppercase tracking-wide">{getCategoryName(category)}</h4>
                    <span className="ml-auto text-xs font-medium text-slate-400 bg-slate-50 px-2 py-0.5 rounded-full border border-slate-100">
                        {entries.length} {t('common.items')}
                    </span>
                </button>

                {isExpanded && (
                    <div className="bg-white rounded-xl border border-slate-100 shadow-sm overflow-hidden animate-in fade-in slide-in-from-top-1">
                        <table className="w-full text-left border-collapse">
                            <tbody className="divide-y divide-slate-50">
                                {entries.map((entry) => (
                                    <tr key={entry.key} className="hover:bg-slate-50/30 transition-colors group">
                                        <td className="px-6 py-4 w-1/3 whitespace-nowrap">
                                            <div className="flex flex-col">
                                                <div className="flex items-center mb-1">
                                                    <code className="text-xs font-semibold text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded">{entry.key}</code>
                                                    {entry.is_sensitive && <Lock className="w-3.5 h-3.5 ml-2 text-amber-400" />}
                                                </div>
                                                {entry.description && (
                                                    <p className="text-xs text-slate-500 font-medium leading-relaxed">{getKeyDescription(entry.key, entry.description)}</p>
                                                )}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            {editMode?.key === entry.key && editMode.file === file ? (
                                                <input
                                                    type="text"
                                                    value={editValue}
                                                    onChange={(e) => setEditValue(e.target.value)}
                                                    className="w-full px-3 py-2 text-sm font-medium border border-sky-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 bg-white shadow-sm"
                                                    autoFocus
                                                />
                                            ) : (
                                                <div className="flex items-center">
                                                    <span className={`text-sm font-medium truncate max-w-lg ${entry.is_sensitive ? 'text-slate-400 italic' : 'text-slate-600'}`}>
                                                        {entry.value}
                                                    </span>
                                                </div>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 text-right w-24">
                                            {editMode?.key === entry.key && editMode.file === file ? (
                                                <div className="flex justify-end space-x-2">
                                                    <button onClick={() => setEditMode(null)} className="text-xs font-semibold text-slate-400 hover:text-slate-600">{t('common.cancel')}</button>
                                                    <button
                                                        onClick={handleSave}
                                                        disabled={saving === entry.key}
                                                        className="px-3 py-1.5 bg-sky-600 text-white rounded-lg text-xs font-bold shadow-sm disabled:opacity-50"
                                                    >
                                                        {saving === entry.key ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : t('common.save')}
                                                    </button>
                                                </div>
                                            ) : (
                                                user?.role === '시스템관리자' && (
                                                    <button
                                                        onClick={() => handleEdit(file, entry)}
                                                        className="opacity-0 group-hover:opacity-100 px-3 py-1.5 border border-slate-200 rounded-lg text-xs font-semibold text-slate-500 hover:bg-white hover:border-sky-300 hover:text-sky-600 transition-all shadow-sm"
                                                    >
                                                        {t('common.edit')}
                                                    </button>
                                                )
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        );
    };

    return (
        <div className="space-y-6 animate-in fade-in duration-300">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight text-slate-900 mb-1">
                        {t('env.title')}
                    </h1>
                    <p className="text-slate-500">
                        {t('env.description')}
                    </p>
                </div>
                <button
                    onClick={fetchEnv}
                    disabled={loading}
                    className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 
                             text-white rounded-lg transition-colors disabled:opacity-50 shadow-md"
                >
                    <RefreshCw size={18} className={loading ? "animate-spin" : ""} />
                    {t('common.refresh')}
                </button>
            </div>

            {/* Warning Message */}
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3 text-amber-800 shadow-sm">
                <AlertTriangle className="w-5 h-5 mt-0.5 flex-shrink-0" />
                <div className="text-sm">
                    <p className="font-bold mb-1">{t('env.warning.title')}</p>
                    <p className="leading-relaxed">
                        {t('env.warning.message')}
                    </p>
                </div>
            </div>

            {/* Status Bar */}
            <div className="bg-slate-900 rounded-xl p-4 shadow-lg border border-slate-800 flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-6">
                    <div className="flex items-center gap-2">
                        <span className="text-slate-400 text-xs font-bold uppercase tracking-wider">{t('env.statusBar.user')}</span>
                        <span className="text-white text-sm font-bold">
                            {user?.user_name === '시스템관리자' ? t('system.user.roles.admin') : user?.user_name}
                        </span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="text-slate-400 text-xs font-bold uppercase tracking-wider">{t('env.statusBar.permission')}</span>
                        <span className="px-2 py-0.5 bg-sky-500/20 text-sky-400 rounded text-[10px] font-bold uppercase border border-sky-500/20">
                            {user?.role === '시스템관리자' ? t('env.statusBar.editPerm') : t('env.statusBar.readOnly')}
                        </span>
                    </div>
                </div>
                <div className="text-xs text-slate-400 font-medium">
                    {t('env.statusBar.auditHint')}
                </div>
            </div>

            <div className="space-y-8">
                {/* Backend Section */}
                <section>
                    <div className="flex items-center mb-4">
                        <div className="w-1 h-5 bg-indigo-500 rounded-full mr-3" />
                        <h2 className="text-lg font-bold text-slate-800">{t('env.backend')}</h2>
                    </div>
                    <div className="space-y-4">
                        {Object.entries(groupedData.backend).map(([category, entries]) =>
                            renderCategorySection('backend', category, entries)
                        )}
                    </div>
                </section>

                {/* Frontend Section */}
                <section>
                    <div className="flex items-center mb-4">
                        <div className="w-1 h-5 bg-sky-500 rounded-full mr-3" />
                        <h2 className="text-lg font-bold text-slate-800">{t('env.frontend')}</h2>
                    </div>
                    <div className="space-y-4">
                        {Object.entries(groupedData.frontend).map(([category, entries]) =>
                            renderCategorySection('frontend', category, entries)
                        )}
                    </div>
                </section>
            </div>

            {/* Footer Audit Record */}
            <div className="p-6 bg-slate-50 rounded-2xl border border-slate-200 flex items-center gap-6">
                <div className="w-12 h-12 bg-white rounded-xl shadow-sm border border-slate-200 flex items-center justify-center flex-shrink-0">
                    <CheckCircle2 className="w-6 h-6 text-emerald-500" />
                </div>
                <div>
                    <h5 className="text-sm font-bold text-slate-800 mb-0.5">{t('env.auditRecord.title')}</h5>
                    <p className="text-xs text-slate-500 leading-relaxed font-medium">
                        {t('env.auditRecord.message')}
                    </p>
                </div>
            </div>
        </div>
    );
};

export default EnvManagement;
