import React, { useEffect, useState } from 'react';
import { systemService, MenuPermission } from '../services/system.service';
import { Shield, Save, RefreshCw, CheckCircle2, AlertCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { clsx } from 'clsx';

const ROLES = ["일반", "보안관리자", "감사팀", "시스템관리자"];

// 사이드바 메뉴 배치 순서와 일치하도록 기본 메뉴 경로 순서 정의
const ORDERED_MENU_PATHS = [
    "/dashboard",
    "/cases",
    "/reviews",
    "/logs",
    "/siem",
    "/users",
    "/env",
    "/jobs",
    "/permissions",
    "/integrations",
    "/notifications"
];

const RolePermissions: React.FC = () => {
    const { t } = useTranslation();
    const [permissions, setPermissions] = useState<MenuPermission[]>([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

    const fetchPermissions = async () => {
        try {
            setLoading(true);
            const data = await systemService.getMenuPermissions();
            setPermissions(data);
        } catch (error) {
            console.error('Failed to fetch permissions:', error);
            setMessage({ type: 'error', text: t('system.permissions.fetchFailed') });
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchPermissions();
    }, []);

    const handleToggle = (role: string, path: string) => {
        setPermissions(prev => prev.map(p => {
            if (p.role === role && p.menu_path === path) {
                return { ...p, is_visible: !p.is_visible };
            }
            return p;
        }));
    };

    const handleSave = async () => {
        try {
            setSaving(true);
            await systemService.updateMenuPermissions(permissions);
            setMessage({ type: 'success', text: t('system.permissions.saveSuccess') });
            setTimeout(() => setMessage(null), 3000);
        } catch (error) {
            console.error('Failed to save permissions:', error);
            setMessage({ type: 'error', text: t('system.permissions.saveError') });
        } finally {
            setSaving(false);
        }
    };

    // 사이드바 메뉴 배치 순서에 맞추어 메뉴 경로 그룹화 및 정렬
    const uniquePaths = Array.from(new Set(permissions.map(p => p.menu_path)));
    const menuPaths = [
        ...ORDERED_MENU_PATHS.filter(path => uniquePaths.includes(path)),
        ...uniquePaths.filter(path => !ORDERED_MENU_PATHS.includes(path)).sort()
    ];

    const getMenuName = (path: string) => {
        const names: Record<string, string> = {
            "/dashboard": t('system.permissions.menus.dashboard'),
            "/cases": t('system.permissions.menus.cases'),
            "/reviews": t('system.permissions.menus.reviews'),
            "/logs": t('system.permissions.menus.logs'),
            "/siem": t('system.permissions.menus.siem'),
            "/users": t('system.permissions.menus.users'),
            "/env": t('system.permissions.menus.env'),
            "/jobs": t('system.permissions.menus.jobs'),
            "/permissions": t('system.permissions.menus.permissions'),
            "/integrations": t('system.permissions.menus.integrations'),
            "/notifications": t('system.permissions.menus.notifications')
        };
        return names[path] || path;
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <RefreshCw className="w-8 h-8 text-sky-500 animate-spin" />
            </div>
        );
    }

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-slate-900 flex items-center">
                        <Shield className="w-6 h-6 mr-2 text-sky-500" />
                        {t('system.permissions.title')}
                    </h1>
                    <p className="text-slate-500 mt-1 text-sm">
                        {t('system.permissions.description')}
                    </p>
                </div>
                <div className="flex gap-3">
                    <button
                        onClick={fetchPermissions}
                        className="flex items-center px-4 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
                    >
                        <RefreshCw className="w-4 h-4 mr-2" />
                        {t('common.refresh')}
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={saving}
                        className="flex items-center px-4 py-2 text-sm font-medium text-white bg-sky-600 rounded-lg hover:bg-sky-700 transition-colors disabled:opacity-50"
                    >
                        {saving ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                        {t('common.save')}
                    </button>
                </div>
            </div>

            {message && (
                <div className={clsx(
                    "p-4 rounded-lg flex items-center gap-3 animate-in zoom-in-95 duration-200",
                    message.type === 'success' ? "bg-emerald-50 text-emerald-700 border border-emerald-100" : "bg-red-50 text-red-700 border border-red-100"
                )}>
                    {message.type === 'success' ? <CheckCircle2 className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
                    <span className="text-sm font-medium">{message.text}</span>
                </div>
            )}

            <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr className="bg-slate-50 border-b border-slate-200">
                                <th className="px-6 py-4 text-sm font-semibold text-slate-700">{t('system.permissions.header.menu')}</th>
                                {ROLES.map(role => (
                                    <th key={role} className="px-6 py-4 text-sm font-semibold text-slate-700 text-center">
                                        {t(`system.user.roles.${role === '일반' ? 'user' : role === '보안관리자' ? 'security_admin' : role === '감사팀' ? 'audit' : 'admin'}`)}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-200">
                            {menuPaths.map(path => (
                                <tr key={path} className="hover:bg-slate-50/50 transition-colors">
                                    <td className="px-6 py-4 text-sm font-medium text-slate-900">
                                        {getMenuName(path)}
                                        <div className="text-xs text-slate-400 font-normal mt-0.5">{path}</div>
                                    </td>
                                    {ROLES.map(role => {
                                        const perm = permissions.find(p => p.role === role && p.menu_path === path);
                                        return (
                                            <td key={role} className="px-6 py-4 text-center">
                                                <label className="inline-flex items-center justify-center cursor-pointer group">
                                                    <input
                                                        type="checkbox"
                                                        className="sr-only peer"
                                                        checked={perm?.is_visible || false}
                                                        onChange={() => handleToggle(role, path)}
                                                    />
                                                    <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-sky-300 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-sky-600 relative transition-colors"></div>
                                                </label>
                                            </td>
                                        );
                                    })}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

export default RolePermissions;
