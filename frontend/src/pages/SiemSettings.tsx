import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { siemService, SiemTestResult } from '../services/siem.service';
import { SiemConfiguration } from '../types';
import { Shield, Plus, Server, CheckCircle2, XCircle, Loader2, Save, Trash2, Database, AlertCircle } from 'lucide-react';

const MAPPING_COLUMNS = [
    { id: 'related_employee_id', required: true },
    { id: 'rule_title', required: true },
    { id: 'summary', required: true },
    { id: 'created_at', required: false },
    { id: 'incident_num', required: false },
    { id: 'original_log_link', required: false },
    { id: 'priority', required: false },
    { id: 'case_type', required: false },
    { id: 'rule_description', required: false },
];

const DEFAULT_MAPPING = MAPPING_COLUMNS.reduce((acc, col) => ({ ...acc, [col.id]: col.id }), {});

const SiemSettings: React.FC = () => {
    const { t } = useTranslation();
    const [configs, setConfigs] = useState<SiemConfiguration[]>([]);
    const [loading, setLoading] = useState(true);
    const [isEditing, setIsEditing] = useState(false);


    // Form State
    const [formData, setFormData] = useState<SiemConfiguration>({
        siem_type: 'Sentinel',
        name: '',
        host_url: '',
        tenant_id: '',
        client_id: '',
        client_secret: '',
        subscription_id: '',
        resource_group: '',
        workspace_name: '',
        test_query: '',
        is_active: true,
        field_mapping: { ...DEFAULT_MAPPING }
    });

    const [testResult, setTestResult] = useState<SiemTestResult | null>(null);
    const [testing, setTesting] = useState(false);
    const [saving, setSaving] = useState(false);
    const [isConverting, setIsConverting] = useState(false);
    const [conversionProgress, setConversionProgress] = useState<{ current: number, total: number }>({ current: 0, total: 0 });
    const [previewValues, setPreviewValues] = useState<Record<string, string>>({});

    useEffect(() => {
        fetchConfigs();
    }, []);

    const fetchConfigs = async () => {
        try {
            const data = await siemService.getConfigs();
            setConfigs(data);
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    };



    const handleDelete = async (configId: number, name: string) => {
        if (confirm(t('system.siem.deleteConfirm', { name }))) {
            try {
                await siemService.deleteConfig(configId);
                alert(t('system.siem.deleteSuccess'));
                fetchConfigs();
            } catch (error) {
                alert(t('common.error') + ': ' + error);
            }
        }
    };

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleMappingCheckChange = (colId: string, checked: boolean) => {
        const currentMapping = { ...(formData.field_mapping || {}) };
        if (checked) {
            currentMapping[colId] = colId;
        } else {
            delete currentMapping[colId];
        }
        setFormData({ ...formData, field_mapping: currentMapping });
    };

    const handleMappingKeyChange = (colId: string, value: string) => {
        const currentMapping = { ...(formData.field_mapping || {}) };
        currentMapping[colId] = value;
        setFormData({ ...formData, field_mapping: currentMapping });
    };

    const handleTestConnection = async () => {
        setTesting(true);
        setTestResult(null);
        setPreviewValues({});
        try {
            const result = await siemService.testConnection(formData);
            setTestResult(result);
        } catch {
            setTestResult({ status: 'error', message: t('system.siem.testFailed') });
        } finally {
            setTesting(false);
        }
    };

    const handleCheckValues = () => {
        if (!testResult || testResult.status !== 'success' || !testResult.data || !Array.isArray(testResult.data) || testResult.data.length === 0) {
            alert(t('system.siem.testDataEmpty'));
            return;
        }

        const firstRow = testResult.data[0];
        const mappingObj = formData.field_mapping || {};
        const newPreview: Record<string, string> = {};

        const extractValue = (data: unknown, keyPath: string): unknown => {
            if (!keyPath) return null;
            if ((keyPath.startsWith('"') && keyPath.endsWith('"')) || (keyPath.startsWith("'") && keyPath.endsWith("'"))) {
                if (keyPath.length >= 2) return keyPath.substring(1, keyPath.length - 1);
            }
            const keys = String(keyPath).split('.');
            let val = data;
            for (const k of keys) {
                if (val && typeof val === 'object' && k in val) {
                    val = (val as Record<string, unknown>)[k];
                } else {
                    return null;
                }
            }
            return val;
        };

        MAPPING_COLUMNS.forEach(col => {
            if (mappingObj[col.id]) {
                const jsonKey = mappingObj[col.id].trim();
                const extracted = extractValue(firstRow, jsonKey);

                if (extracted !== null && extracted !== undefined && extracted !== "") {
                    newPreview[col.id] = typeof extracted === 'object' ? JSON.stringify(extracted) : String(extracted);
                } else {
                    newPreview[col.id] = t('system.siem.noMappedValue');
                }
            }
        });

        setPreviewValues(newPreview);
    };

    const handleConvertCase = async () => {
        if (!testResult || testResult.status !== 'success' || !testResult.data || !Array.isArray(testResult.data) || testResult.data.length === 0) {
            alert(t('system.siem.testDataEmptyShort'));
            return;
        }

        const totalItems = testResult.data.length;
        if (!confirm(t('system.siem.convertConfirm', { count: totalItems }))) {
            return;
        }

        setIsConverting(true);
        setConversionProgress({ current: 0, total: totalItems });

        let successCount = 0;
        let failCount = 0;

        try {
            for (let i = 0; i < totalItems; i++) {
                setConversionProgress({ current: i + 1, total: totalItems });
                const row = testResult.data[i];

                try {
                    const response = await siemService.convertCase(row, formData.field_mapping);
                    if (response.status === 'success') {
                        successCount++;
                    } else {
                        failCount++;
                        console.error(`Row ${i} conversion failed:`, response.message);
                    }
                } catch (err) {
                    failCount++;
                    console.error(`Row ${i} error:`, err);
                }
            }

            alert(t('system.siem.convertCompleteProgress', { total: totalItems, success: successCount, failed: failCount }));
        } catch (error) {
            console.error(error);
            alert(t('system.siem.convertError'));
        } finally {
            setIsConverting(false);
            setConversionProgress({ current: 0, total: 0 });
        }
    };

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        setSaving(true);
        try {
            if (formData.siem_id) {
                await siemService.updateConfig(formData.siem_id, formData);
                alert(t('system.siem.saveSuccess'));
            } else {
                await siemService.createConfig(formData);
                alert(t('system.siem.saveNewSuccess'));
            }

            setIsEditing(false);
            fetchConfigs();
            // Reset form
            setFormData({
                siem_type: 'Sentinel',
                name: '',
                host_url: '',
                tenant_id: '',
                client_id: '',
                client_secret: '',
                subscription_id: '',
                resource_group: '',
                workspace_name: '',
                test_query: '',
                is_active: true,
                field_mapping: { ...DEFAULT_MAPPING }
            });
            setTestResult(null);
            setPreviewValues({});
        } catch {
            alert(t('common.error'));
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-slate-900">{t('system.siem.title')}</h1>
                    <p className="text-slate-500 mt-1">{t('system.siem.description')}</p>
                </div>
                {!isEditing && (
                    <button
                        onClick={() => setIsEditing(true)}
                        className="flex items-center px-4 py-2 bg-sky-600 text-white rounded-lg hover:bg-sky-700 transition"
                    >
                        <Plus className="w-5 h-5 mr-2" />
                        {t('system.siem.addConnection')}
                    </button>
                )}
            </div>

            {loading ? (
                <div className="p-12 text-center text-slate-500">
                    <Loader2 className="w-8 h-8 mx-auto animate-spin mb-4" />
                    {t('system.siem.configLoading')}
                </div>
            ) : isEditing ? (
                <>
                    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                        <h3 className="text-lg font-semibold text-slate-900 mb-6 flex items-center">
                            <Server className="w-5 h-5 mr-2 text-sky-600" />
                            {t('system.siem.addConfigTitle')}
                        </h3>

                        <form onSubmit={handleSave} className="space-y-6">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div>
                                    <label className="block text-sm font-medium text-slate-700 mb-2">{t('system.siem.siemType')}</label>
                                    <select
                                        name="siem_type"
                                        value={formData.siem_type}
                                        onChange={handleChange}
                                        className="w-full border-slate-300 rounded-lg shadow-sm focus:border-sky-500 focus:ring-sky-500 p-2.5 border"
                                    >
                                        <option value="Sentinel">Microsoft Sentinel</option>
                                        <option value="ELK">Elastic Stack (ELK)</option>
                                        <option value="Splunk">Splunk</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-slate-700 mb-2">{t('system.siem.connectionName')}</label>
                                    <input
                                        name="name"
                                        value={formData.name}
                                        onChange={handleChange}
                                        placeholder={t('system.siem.connectionNamePlaceholder')}
                                        className="w-full border-slate-300 rounded-lg shadow-sm focus:border-sky-500 focus:ring-sky-500 p-2.5 border"
                                        required
                                    />
                                </div>
                            </div>

                            {formData.siem_type === 'Sentinel' && (
                                <div className="space-y-4 border-t border-slate-100 pt-6">
                                    <h4 className="text-sm font-semibold text-slate-900">{t('system.siem.azureSentinel')}</h4>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-xs font-medium text-slate-500 mb-1">{t('system.siem.subscriptionId')}</label>
                                            <input
                                                name="subscription_id"
                                                value={formData.subscription_id}
                                                onChange={handleChange}
                                                placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                                                className="w-full border-slate-300 rounded-lg shadow-sm p-2.5 border text-sm"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-xs font-medium text-slate-500 mb-1">{t('system.siem.resourceGroup')}</label>
                                            <input
                                                name="resource_group"
                                                value={formData.resource_group}
                                                onChange={handleChange}
                                                placeholder="rg-security-logs"
                                                className="w-full border-slate-300 rounded-lg shadow-sm p-2.5 border text-sm"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-xs font-medium text-slate-500 mb-1">{t('system.siem.workspaceId')}</label>
                                            <input
                                                name="workspace_name"
                                                value={formData.workspace_name}
                                                onChange={handleChange}
                                                placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                                                className="w-full border-slate-300 rounded-lg shadow-sm p-2.5 border text-sm"
                                                required
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-xs font-medium text-slate-500 mb-1">{t('system.siem.hostUrl')}</label>
                                            <input
                                                name="host_url"
                                                value={formData.host_url}
                                                onChange={handleChange}
                                                placeholder="https://management.azure.com"
                                                className="w-full border-slate-300 rounded-lg shadow-sm p-2.5 border text-sm"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-xs font-medium text-slate-500 mb-1">{t('system.siem.tenantId')}</label>
                                            <input
                                                name="tenant_id"
                                                value={formData.tenant_id}
                                                onChange={handleChange}
                                                className="w-full border-slate-300 rounded-lg shadow-sm p-2.5 border text-sm"
                                                required
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-xs font-medium text-slate-500 mb-1">{t('system.siem.clientId')}</label>
                                            <input
                                                name="client_id"
                                                value={formData.client_id}
                                                onChange={handleChange}
                                                className="w-full border-slate-300 rounded-lg shadow-sm p-2.5 border text-sm"
                                                required
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-xs font-medium text-slate-500 mb-1">{t('system.siem.clientSecret')}</label>
                                            <input
                                                name="client_secret"
                                                type="password"
                                                value={formData.client_secret}
                                                onChange={handleChange}
                                                className="w-full border-slate-300 rounded-lg shadow-sm p-2.5 border text-sm"
                                                required
                                            />
                                        </div>
                                        <div className="md:col-span-2">
                                            <label className="block text-xs font-medium text-slate-500 mb-1">{t('system.siem.testQuery')}</label>
                                            <textarea
                                                name="test_query"
                                                value={formData.test_query || ''}
                                                onChange={handleChange}
                                                placeholder="SecurityIncident | take 5"
                                                className="w-full border-slate-300 rounded-lg shadow-sm p-2.5 border text-sm font-mono"
                                                rows={3}
                                            />
                                        </div>
                                        <div className="md:col-span-2 pt-4 border-t border-slate-100 mt-2">
                                            <label className="block text-sm font-semibold text-slate-900 mb-2">{t('system.siem.cronTitle')}</label>
                                            <div className="flex flex-col md:flex-row gap-4 items-start md:items-center">
                                                <input
                                                    name="cron_expression"
                                                    value={formData.cron_expression || ''}
                                                    onChange={handleChange}
                                                    placeholder={t('system.siem.cronPlaceholder')}
                                                    className="w-full md:w-1/3 border-slate-300 rounded-lg shadow-sm p-2.5 border font-mono text-sm focus:border-sky-500 focus:ring-sky-500"
                                                />
                                                <div className="flex flex-wrap gap-2">
                                                    <button
                                                        type="button"
                                                        onClick={() => setFormData({ ...formData, cron_expression: '*/5 * * * *' })}
                                                        className="px-3 py-1.5 text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-md transition"
                                                    >
                                                        {t('system.siem.fiveMins')}
                                                    </button>
                                                    <button
                                                        type="button"
                                                        onClick={() => setFormData({ ...formData, cron_expression: '*/30 * * * *' })}
                                                        className="px-3 py-1.5 text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-md transition"
                                                    >
                                                        {t('system.siem.thirtyMins')}
                                                    </button>
                                                    <button
                                                        type="button"
                                                        onClick={() => setFormData({ ...formData, cron_expression: '0 * * * *' })}
                                                        className="px-3 py-1.5 text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-md transition"
                                                    >
                                                        {t('system.siem.hourly')}
                                                    </button>
                                                </div>
                                            </div>
                                            <p className="text-xs text-slate-500 mt-2">{t('system.siem.cronHint')}</p>
                                        </div>


                                        <div className="md:col-span-2 mt-6 pt-6 border-t border-slate-100">
                                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
                                                {/* 왼쪽 영역: 연결 테스트 및 결과 */}
                                                <div>
                                                    <div className="flex items-center justify-between mb-4">
                                                        <h4 className="text-sm font-semibold text-slate-900 flex items-center">
                                                            <Server className="w-4 h-4 mr-2 text-slate-500" />
                                                            {t('system.siem.testConnection')}
                                                        </h4>
                                                        <button
                                                            type="button"
                                                            onClick={handleTestConnection}
                                                            disabled={testing}
                                                            className="px-3 py-1.5 text-xs text-sky-600 bg-sky-50 hover:bg-sky-100 rounded-lg font-medium transition flex items-center border border-sky-100"
                                                        >
                                                            {testing ? <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" /> : <Shield className="w-3.5 h-3.5 mr-1.5" />}
                                                            {t('system.siem.send')}
                                                        </button>
                                                    </div>

                                                    {!testResult ? (
                                                        <div className="p-8 text-center text-slate-500 bg-slate-50 rounded-lg border-2 border-dashed border-slate-200">
                                                            <Server className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                                                            <p className="text-sm">{t('system.siem.testEmptyResult')}</p>
                                                        </div>
                                                    ) : (
                                                        <div className={`p-4 rounded-lg overflow-auto border ${testResult.status === 'success' ? 'bg-green-50/50 border-green-200 text-green-800' : 'bg-red-50/50 border-red-200 text-red-800'}`}>
                                                            <div className="flex items-center mb-3 pb-3 border-b border-white/20">
                                                                {testResult.status === 'success' ? <CheckCircle2 className="w-5 h-5 mr-2 flex-shrink-0 text-green-600" /> : <XCircle className="w-5 h-5 mr-2 flex-shrink-0 text-red-600" />}
                                                                <span className="font-semibold text-sm">{testResult.message}</span>
                                                            </div>
                                                            {testResult.status === 'success' && testResult.data && (
                                                                <div className="relative">
                                                                    <div className="absolute top-0 right-0 bg-slate-800 text-slate-200 text-[10px] px-2 py-1 rounded-bl-lg rounded-tr opacity-80 uppercase tracking-wider font-semibold">{t('system.siem.jsonResponse')}</div>
                                                                    <pre className="text-[11px] font-mono bg-slate-900 text-slate-300 p-3.5 rounded shadow-inner overflow-x-auto max-h-[300px] leading-relaxed custom-scrollbar">
                                                                        {JSON.stringify(testResult.data, null, 2)}
                                                                    </pre>
                                                                </div>
                                                            )}
                                                        </div>
                                                    )}
                                                </div>

                                                {/* 오른쪽 영역: Data Field Mapping */}
                                                <div>
                                                    <div className="flex items-center justify-between mb-4">
                                                        <h4 className="text-sm font-semibold text-slate-900 flex items-center">
                                                            <Database className="w-4 h-4 mr-2 text-indigo-500" />
                                                            {t('system.siem.fieldMapping')}
                                                        </h4>
                                                        <div className="flex items-center space-x-2">
                                                            <button
                                                                type="button"
                                                                onClick={handleCheckValues}
                                                                className="px-3 py-1.5 text-xs text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 rounded-lg font-medium transition shadow-sm"
                                                            >
                                                                {t('system.siem.checkValues')}
                                                            </button>
                                                            <button
                                                                type="button"
                                                                onClick={handleConvertCase}
                                                                disabled={isConverting}
                                                                className="px-3 py-1.5 text-xs text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg font-medium transition shadow-sm disabled:bg-indigo-300"
                                                            >
                                                                {isConverting ? `${t('system.siem.converting')} (${conversionProgress.current}/${conversionProgress.total})` : t('system.siem.send')}
                                                            </button>
                                                        </div>
                                                    </div>

                                                    <div className="border border-slate-200 rounded-lg overflow-hidden bg-white relative">
                                                        <div className="max-h-[340px] overflow-y-auto">
                                                            <table className="w-full text-sm table-fixed">
                                                                <thead className="bg-slate-50 text-xs font-medium text-slate-500 sticky top-0 z-10 shadow-sm">
                                                                    <tr>
                                                                        <th className="w-10 px-3 py-2 border-b border-slate-200 whitespace-nowrap"></th>
                                                                        <th className="px-1 py-2 text-left border-b border-slate-200 whitespace-nowrap">{t('system.siem.mappingTable')}</th>
                                                                        <th className="w-[30%] px-3 py-2 text-center border-l border-b border-slate-200 whitespace-nowrap">JSON Key</th>
                                                                        <th className="w-[30%] px-3 py-2 text-center border-l border-b border-slate-200 whitespace-nowrap">{t('system.siem.preview')}</th>
                                                                    </tr>
                                                                </thead>
                                                                <tbody className="divide-y divide-slate-100 bg-white">
                                                                    {MAPPING_COLUMNS.map((col) => {
                                                                        const mappingObj = formData.field_mapping || {};
                                                                        const isChecked = col.required || Object.prototype.hasOwnProperty.call(mappingObj, col.id);
                                                                        const jsonKey = mappingObj[col.id] || "";

                                                                        const previewVal = previewValues[col.id] || "";

                                                                        return (
                                                                            <tr key={col.id} className="hover:bg-slate-50/80 transition-colors group">
                                                                                <td className="px-3 py-2 w-10">
                                                                                    <input
                                                                                        type="checkbox"
                                                                                        checked={isChecked}
                                                                                        onChange={(e) => handleMappingCheckChange(col.id, e.target.checked)}
                                                                                        className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                                                                                        disabled={col.required}
                                                                                    />
                                                                                </td>
                                                                                <td className="px-1 py-2 truncate">
                                                                                    <div className="flex flex-col">
                                                                                        <span className={`font-medium ${isChecked ? 'text-slate-800' : 'text-slate-400'} text-xs truncate`}>
                                                                                            {t(`system.siem.mapping.${col.id}`)} {col.required && <span className="text-red-500 ml-0.5">*</span>}
                                                                                        </span>
                                                                                        <span className="text-[10px] text-slate-400 font-mono mt-0.5 truncate">{col.id}</span>
                                                                                    </div>
                                                                                </td>
                                                                                <td className="px-3 py-2 border-l border-slate-100">
                                                                                    <input
                                                                                        type="text"
                                                                                        disabled={!isChecked}
                                                                                        value={jsonKey}
                                                                                        onChange={(e) => handleMappingKeyChange(col.id, e.target.value)}
                                                                                        placeholder={isChecked ? t('system.siem.enterJsonKey') : ""}
                                                                                        className="w-full border border-slate-300 rounded px-2.5 py-1.5 focus:border-indigo-500 focus:ring-indigo-500 disabled:bg-slate-50 disabled:text-slate-400 text-xs shadow-sm"
                                                                                    />
                                                                                </td>
                                                                                <td className="px-3 py-2 border-l border-slate-200 bg-slate-100/50">
                                                                                    <div className="text-slate-700 truncate font-mono text-xs w-full" title={previewVal}>
                                                                                        {previewVal || <span className="text-slate-300 italic">-</span>}
                                                                                    </div>
                                                                                </td>
                                                                            </tr>
                                                                        );
                                                                    })}
                                                                </tbody>
                                                            </table>
                                                        </div>
                                                    </div>
                                                    <div className="mt-2 text-[11px] text-slate-500 flex items-start">
                                                        <AlertCircle className="w-3.5 h-3.5 mr-1 text-slate-400 flex-shrink-0 mt-0.5" />
                                                        <p>{t('system.siem.mappingHint')}</p>
                                                    </div>
                                                </div>
                                            </div>

                                            {/* Bottom Action buttons moved to mapping section header */}
                                        </div>
                                    </div>
                                </div>
                            )}

                            <div className="flex justify-end pt-5 border-t border-slate-100 mt-6">
                                <div className="flex space-x-3">
                                    <button
                                        type="button"
                                        onClick={() => { setIsEditing(false); setTestResult(null); setPreviewValues({}); }}
                                        className="px-5 py-2 text-slate-600 hover:bg-slate-100 rounded-lg font-medium transition focus:outline-none focus:ring-2 focus:ring-slate-200"
                                    >
                                        {t('common.cancel')}
                                    </button>
                                    <button
                                        type="submit"
                                        disabled={saving}
                                        className="px-5 py-2 bg-[#0ea5e9] text-white hover:bg-sky-600 rounded-lg font-medium transition flex items-center shadow-sm focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2"
                                    >
                                        {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                                        {t('common.save')}
                                    </button>
                                </div>
                            </div>

                        </form>
                    </div>
                </>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {configs.map((config) => (
                        <div key={config.siem_id} className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 hover:shadow-md transition">
                            <div className="flex items-start justify-between mb-4">
                                <div className="flex items-center">
                                    <div className="p-2 bg-blue-50 rounded-lg mr-3">
                                        <Shield className="w-6 h-6 text-blue-600" />
                                    </div>
                                    <div>
                                        <h3 className="font-semibold text-slate-900">{config.name}</h3>
                                        <span className="text-xs text-slate-500">{config.siem_type}</span>
                                    </div>
                                </div>
                                <div className="flex items-center space-x-2">
                                    <span className={`w-2.5 h-2.5 rounded-full ${config.is_active ? 'bg-green-500' : 'bg-slate-300'}`} />
                                    <button
                                        onClick={() => config.siem_id && handleDelete(config.siem_id, config.name)}
                                        className="p-1 text-slate-400 hover:text-red-500 transition"
                                        title={t('common.delete')}
                                    >
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                </div>
                            </div>
                            <div className="text-sm text-slate-500 space-y-2 mb-4">
                                <div className="flex justify-between">
                                    <span>{t('system.siem.hostLabel')}:</span>
                                    <span className="font-medium text-slate-700 truncate max-w-[150px]">{config.host_url}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span>{t('system.siem.lastCheckLabel')}:</span>
                                    <span className="font-medium text-slate-700">{t('system.siem.justNow')}</span>
                                </div>
                            </div>
                            <div className="flex space-x-2">
                                <button
                                    onClick={() => {
                                        setFormData(config);
                                        setIsEditing(true);
                                    }}
                                    className="flex-1 px-3 py-2 text-xs font-medium text-slate-600 bg-slate-50 hover:bg-slate-100 rounded-lg border border-slate-200"
                                >
                                    {t('system.siem.editConfig')}
                                </button>
                                <button
                                    onClick={async () => {
                                        try {
                                            if (confirm(t('system.siem.testConfirm', { name: config.name }))) {
                                                const res = await siemService.testConnection(config);
                                                alert(`[${res.status.toUpperCase()}] ${res.message}`);
                                            }
                                        } catch {
                                            alert(t('system.siem.testFail'));
                                        }
                                    }}
                                    className="flex-1 px-3 py-2 text-xs font-medium text-sky-600 bg-sky-50 hover:bg-sky-100 rounded-lg border border-sky-100">
                                    {t('system.siem.checkConnection')}
                                </button>
                            </div>
                        </div>
                    ))}

                    {configs.length === 0 && (
                        <div className="col-span-full py-12 text-center text-slate-500 bg-slate-50 rounded-xl border-2 border-dashed border-slate-200">
                            <Shield className="w-12 h-12 mx-auto text-slate-300 mb-3" />
                            <p>{t('system.siem.configEmpty')}</p>
                            <p className="text-sm mt-1">{t('system.siem.configEmptyHint')}</p>
                        </div>
                    )}
                </div>
            )
            }
        </div >
    );
};

export default SiemSettings;
