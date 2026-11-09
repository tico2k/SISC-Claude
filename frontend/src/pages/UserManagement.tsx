import React, { useEffect, useState } from 'react';
import { userService } from '../services/user.service';
import { authService } from '../services/auth.service';
import { User, UserRegisterRequest, UserUploadStats } from '../types';
import { Users, Plus, Edit2, Trash2, Search, RefreshCw } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { getApiErrorBody, getErrorMessage } from '../utils/error';

const UserManagement: React.FC = () => {
    const { t } = useTranslation();
    const { user: currentUser } = useAuth();
    const [users, setUsers] = useState<User[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');

    // Modal State
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [isEditMode, setIsEditMode] = useState(false);
    const [editingId, setEditingId] = useState<number | null>(null);
    const [formData, setFormData] = useState<UserRegisterRequest>({
        user_email: '',
        user_name: '',
        password: '',
        company: '',
        department: '',
        role: '일반'
    });
    const [saving, setSaving] = useState(false);

    // Bulk Upload State
    const [isBulkModalOpen, setIsBulkModalOpen] = useState(false);
    const [uploadFile, setUploadFile] = useState<File | null>(null);
    const [uploadFormat, setUploadFormat] = useState('auto');
    const [uploading, setUploading] = useState(false);
    const [uploadResult, setUploadResult] = useState<UserUploadStats | null>(null);

    const [syncing, setSyncing] = useState(false);
    // Entra 연동이 설정된 경우에만 동기화 버튼 표시
    const [entraEnabled, setEntraEnabled] = useState(false);

    useEffect(() => {
        fetchUsers();
        authService.getAuthConfig()
            .then((cfg) => setEntraEnabled(cfg.allow_entra))
            .catch(() => setEntraEnabled(false));
    }, []);

    const fetchUsers = async () => {
        try {
            const data = await userService.getUsers();
            setUsers(data);
        } catch {
            console.error("Failed to fetch users");
        } finally {
            setLoading(false);
        }
    };

    const handleSyncEntra = async () => {
        if (!window.confirm(t('system.user.alerts.syncConfirm'))) return;

        setSyncing(true);
        try {
            const result = await userService.syncUsersFromEntra();
            alert(t('system.user.alerts.syncSuccess', {
                total: result.stats.total,
                created: result.stats.created,
                updated: result.stats.updated
            }));
            fetchUsers();
        } catch (error: unknown) {
            alert(t('system.user.alerts.syncFailed', { message: getApiErrorBody(error).detail || getErrorMessage(error) }));
        } finally {
            setSyncing(false);
        }
    };

    const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
        setSearchTerm(e.target.value);
    };

    const filteredUsers = users.filter(u =>
        u.user_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        u.user_email.toLowerCase().includes(searchTerm.toLowerCase()) ||
        u.department?.toLowerCase().includes(searchTerm.toLowerCase())
    );

    const openCreateModal = () => {
        setIsEditMode(false);
        setFormData({
            user_email: '',
            user_name: '',
            password: '',
            company: '',
            department: '',
            role: '일반'
        });
        setIsModalOpen(true);
    };

    const openEditModal = (user: User) => {
        setIsEditMode(true);
        setEditingId(user.user_id);
        setFormData({
            user_email: user.user_email,
            user_name: user.user_name,
            password: '', // Password not shown
            company: user.company || '',
            department: user.department || '',
            role: user.role
        });
        setIsModalOpen(true);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setSaving(true);
        try {
            if (isEditMode && editingId) {
                // Update
                const updatePayload: Partial<UserRegisterRequest> = { ...formData };
                if (!updatePayload.password) {
                    delete updatePayload.password;
                }
                await userService.updateUser(editingId, updatePayload);
                alert(t('system.user.alerts.modified'));
            } else {
                // Create
                if (!formData.password) {
                    alert(t('system.user.alerts.passwordRequired'));
                    setSaving(false);
                    return;
                }
                await userService.createUser(formData);
                alert(t('system.user.alerts.created'));
            }
            setIsModalOpen(false);
            fetchUsers();
        } catch (error) {
            alert(t('common.error') + ': ' + error);
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async (userId: number) => {
        if (!window.confirm(t('system.user.alerts.deleteConfirm'))) return;
        try {
            await userService.deleteUser(userId);
            setUsers(users.filter(u => u.user_id !== userId));
        } catch {
            alert(t('system.user.alerts.deleteFailed'));
        }
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            const file = e.target.files[0];
            setUploadFile(file);

            // Auto-detect format
            const ext = file.name.split('.').pop()?.toLowerCase();
            if (ext === 'csv') setUploadFormat('csv');
            else if (ext === 'json') setUploadFormat('json');
            else setUploadFormat('auto');

            setUploadResult(null); // Clear previous results
        }
    };

    const handleBulkUpload = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!uploadFile) return;

        setUploading(true);
        const formData = new FormData();
        formData.append('file', uploadFile);
        formData.append('format', uploadFormat);

        try {
            const responseStats = await userService.uploadUsers(formData);
            setUploadResult(responseStats.stats); // API returns { message, stats } or just stats? 
            // My backend returns { "message": ..., "stats": ... }
            // user.service.ts returns response.data which is the whole JSON.
            // So responseStats is the whole object.

            // Wait, let's check backend return: return {"message": "...", "stats": stats}
            // Frontend code in step 312 was: const data = await response.json(); setUploadResult(data.stats);
            // So I should use responseStats.stats.

            fetchUsers();
        } catch (error: unknown) {
            alert(t('system.user.alerts.uploadFailed', { message: getApiErrorBody(error).detail || getErrorMessage(error) }));
        } finally {
            setUploading(false);
        }
    };

    const closeBulkModal = () => {
        setIsBulkModalOpen(false);
        setUploadFile(null);
        setUploadResult(null);
        setUploadFormat('auto');
    };

    return (
        <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-slate-900">{t('system.user.title')}</h1>
                    <p className="text-slate-500 mt-1">{t('system.user.description')}</p>
                </div>
                <div className="flex space-x-2">
                    {currentUser?.role === '시스템관리자' && (
                        <>
                            {entraEnabled && (
                            <button
                                onClick={handleSyncEntra}
                                disabled={syncing}
                                className="flex items-center justify-center px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition disabled:opacity-50"
                            >
                                <RefreshCw className={`w-5 h-5 mr-2 ${syncing ? 'animate-spin' : ''}`} />
                                {t('system.user.syncEntra')}
                            </button>
                            )}
                            <button
                                onClick={() => setIsBulkModalOpen(true)}
                                className="flex items-center justify-center px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition"
                            >
                                <Users className="w-5 h-5 mr-2" />
                                {t('system.user.bulkUpload')}
                            </button>
                        </>
                    )}
                    <button
                        onClick={openCreateModal}
                        className="flex items-center justify-center px-4 py-2 bg-sky-600 text-white rounded-lg hover:bg-sky-700 transition"
                    >
                        <Plus className="w-5 h-5 mr-2" />
                        {t('system.user.addUser')}
                    </button>
                </div>
            </div>

            {/* Search */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 w-5 h-5" />
                    <input
                        type="text"
                        placeholder={t('system.user.searchPlaceholder')}
                        value={searchTerm}
                        onChange={handleSearch}
                        className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg focus:ring-sky-500 focus:border-sky-500"
                    />
                </div>
            </div>

            {/* Table */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                {loading ? (
                    <div className="p-12 text-center text-slate-500">{t('common.loading')}</div>
                ) : (
                    <table className="min-w-full divide-y divide-slate-200">
                        <thead className="bg-slate-50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider whitespace-nowrap">{t('system.user.table.user')}</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider whitespace-nowrap">{t('system.user.table.org')}</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider whitespace-nowrap">{t('system.user.table.role')}</th>
                                <th className="px-6 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wider whitespace-nowrap">{t('system.user.table.manage')}</th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-slate-200">
                            {filteredUsers.map((user) => (
                                <tr key={user.user_id} className="hover:bg-slate-50">
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <div className="flex items-center">
                                            <div className="h-10 w-10 rounded-full bg-slate-100 flex items-center justify-center text-slate-500 mr-3">
                                                <Users className="w-5 h-5" />
                                            </div>
                                            <div>
                                                <div className="text-sm font-medium text-slate-900">{user.user_name}</div>
                                                <div className="text-sm text-slate-500">{user.user_email}</div>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <div className="text-sm text-slate-900">{user.company || '-'}</div>
                                        <div className="text-sm text-slate-500">{user.department || '-'}</div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                                            ${user.role === '시스템관리자' ? 'bg-purple-100 text-purple-800' :
                                                user.role === '보안관리자' ? 'bg-blue-100 text-blue-800' :
                                                    user.role === '감사팀' ? 'bg-amber-100 text-amber-800' :
                                                        'bg-slate-100 text-slate-800'}`}>
                                            {user.role === '시스템관리자' ? t('system.user.roles.admin') :
                                                user.role === '보안관리자' ? t('system.user.roles.security_admin') :
                                                    user.role === '감사팀' ? t('system.user.roles.audit') :
                                                        t('system.user.roles.user')}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                        <button
                                            onClick={() => openEditModal(user)}
                                            className="text-sky-600 hover:text-sky-900 mr-4"
                                            title={t('common.edit')}
                                        >
                                            <Edit2 className="w-4 h-4" />
                                        </button>
                                        {user.user_id !== currentUser?.user_id && (
                                            <button
                                                onClick={() => handleDelete(user.user_id)}
                                                className="text-red-600 hover:text-red-900"
                                                title={t('common.delete')}
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </button>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>

            {/* Create/Edit Modal */}
            {isModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
                    <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
                        <h3 className="text-lg font-bold text-slate-900 mb-4">
                            {isEditMode ? t('system.user.modal.editUser') : t('system.user.modal.addUser')}
                        </h3>
                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">{t('system.user.modal.email')}</label>
                                <input
                                    type="email"
                                    value={formData.user_email}
                                    onChange={(e) => setFormData({ ...formData, user_email: e.target.value })}
                                    disabled={isEditMode}
                                    className="block w-full border border-slate-300 rounded-lg p-2.5 disabled:bg-slate-100"
                                    required
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">{t('system.user.modal.name')}</label>
                                <input
                                    type="text"
                                    value={formData.user_name}
                                    onChange={(e) => setFormData({ ...formData, user_name: e.target.value })}
                                    className="block w-full border border-slate-300 rounded-lg p-2.5"
                                    required
                                />
                            </div>
                            {!isEditMode && (
                                <div>
                                    <label className="block text-sm font-medium text-slate-700 mb-1">{t('system.user.modal.password')}</label>
                                    <input
                                        type="password"
                                        value={formData.password}
                                        onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                                        className="block w-full border border-slate-300 rounded-lg p-2.5"
                                        required={!isEditMode}
                                    />
                                </div>
                            )}
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-slate-700 mb-1">{t('system.user.modal.company')}</label>
                                    <input
                                        type="text"
                                        value={formData.company}
                                        onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                                        className="block w-full border border-slate-300 rounded-lg p-2.5"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-slate-700 mb-1">{t('system.user.modal.department')}</label>
                                    <input
                                        type="text"
                                        value={formData.department}
                                        onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                                        className="block w-full border border-slate-300 rounded-lg p-2.5"
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-700">{t('system.user.modal.role')}</label>
                                <select
                                    value={formData.role}
                                    onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                                    className="mt-1 block w-full rounded-md border-slate-300 shadow-sm focus:border-sky-500 focus:ring-sky-500 sm:text-sm"
                                >
                                    <option value="일반">{t('system.user.roles.user')}</option>
                                    <option value="보안관리자">{t('system.user.roles.security_admin')}</option>
                                    <option value="감사팀">{t('system.user.roles.audit')}</option>
                                    <option value="시스템관리자">{t('system.user.roles.admin')}</option>
                                </select>
                            </div>

                            {/* Password Reset Section (Only for Edit) */}
                            {isEditMode && (
                                <div className="pt-4 border-t border-slate-200 mt-4">
                                    <label className="block text-sm font-medium text-slate-700">{t('system.user.modal.passwordChange')}</label>
                                    <input
                                        type="password"
                                        placeholder={t('system.user.modal.password')}
                                        value={formData.password || ''}
                                        onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                                        className="mt-1 block w-full rounded-md border-slate-300 shadow-sm focus:border-sky-500 focus:ring-sky-500 sm:text-sm"
                                    />
                                    <p className="mt-1 text-xs text-slate-500">
                                        {t('system.user.modal.passwordHint')}
                                    </p>
                                </div>
                            )}

                            <div className="mt-6 flex justify-end space-x-3">
                                <button
                                    type="button"
                                    onClick={() => setIsModalOpen(false)}
                                    className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 font-medium"
                                >
                                    {t('common.cancel')}
                                </button>
                                <button
                                    type="submit"
                                    disabled={saving}
                                    className="px-4 py-2 bg-sky-600 text-white rounded-lg hover:bg-sky-700 font-medium disabled:opacity-50"
                                >
                                    {saving ? t('common.saving') : t('common.save')}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Bulk Upload Modal */}
            {isBulkModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
                    <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
                        <h3 className="text-lg font-bold text-slate-900 mb-4">
                            {t('system.user.bulk.title')}
                        </h3>
                        <form onSubmit={handleBulkUpload} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">
                                    {t('system.user.bulk.fileSelect')}
                                </label>
                                <input
                                    type="file"
                                    accept=".csv,.json"
                                    onChange={handleFileChange}
                                    className="block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-sky-50 file:text-sky-700 hover:file:bg-sky-100"
                                    required
                                />
                            </div>

                            {/* Format Selection */}
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-2">
                                    {t('system.user.bulk.format')}
                                </label>
                                <div className="flex space-x-4">
                                    <label className="inline-flex items-center">
                                        <input
                                            type="radio"
                                            className="form-radio text-sky-600"
                                            name="format"
                                            value="auto"
                                            checked={uploadFormat === 'auto'}
                                            onChange={(e) => setUploadFormat(e.target.value)}
                                        />
                                        <span className="ml-2">{t('system.user.bulk.auto')}</span>
                                    </label>
                                    <label className="inline-flex items-center">
                                        <input
                                            type="radio"
                                            className="form-radio text-sky-600"
                                            name="format"
                                            value="csv"
                                            checked={uploadFormat === 'csv'}
                                            onChange={(e) => setUploadFormat(e.target.value)}
                                        />
                                        <span className="ml-2">CSV</span>
                                    </label>
                                    <label className="inline-flex items-center">
                                        <input
                                            type="radio"
                                            className="form-radio text-sky-600"
                                            name="format"
                                            value="json"
                                            checked={uploadFormat === 'json'}
                                            onChange={(e) => setUploadFormat(e.target.value)}
                                        />
                                        <span className="ml-2">JSON</span>
                                    </label>
                                </div>
                            </div>

                            {/* Result Display */}
                            {uploadResult && (
                                <div className="bg-slate-50 p-4 rounded-lg text-sm">
                                    <p className="font-semibold text-slate-900 mb-2">{t('system.user.bulk.result')}:</p>
                                    <p>{t('system.user.bulk.total')}: <span className="font-medium">{uploadResult.total}</span></p>
                                    <p className="text-emerald-600">{t('system.user.bulk.success')}: <span className="font-medium">{uploadResult.created}</span></p>
                                    <p className="text-amber-600">{t('system.user.bulk.skipped')}: <span className="font-medium">{uploadResult.skipped}</span></p>
                                    <p className="text-red-600">{t('system.user.bulk.failed')}: <span className="font-medium">{uploadResult.errors}</span></p>
                                    {uploadResult.details.length > 0 && (
                                        <div className="mt-2 text-xs text-slate-500 max-h-24 overflow-y-auto">
                                            {uploadResult.details.map((msg: string, i: number) => (
                                                <div key={i}>{msg}</div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}

                            <div className="mt-6 flex justify-end space-x-3">
                                <button
                                    type="button"
                                    onClick={closeBulkModal}
                                    className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 font-medium"
                                >
                                    {t('common.close')}
                                </button>
                                <button
                                    type="submit"
                                    disabled={uploading || !uploadFile}
                                    className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 font-medium disabled:opacity-50"
                                >
                                    {uploading ? t('system.user.bulk.uploading') : t('common.upload')}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
};

export default UserManagement;
