import React from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import {
    LayoutDashboard,
    FileText,
    CheckSquare,
    ShieldAlert,
    LogOut,
    Menu,
    User as UserIcon,
    X,
    Settings,
    Key,
    ShieldCheck,
    Plug
} from 'lucide-react';
import { clsx } from 'clsx';

import ChangePasswordModal from './ChangePasswordModal';
import LanguageSwitcher from './LanguageSwitcher';
import { systemService } from '../services/system.service';

const Layout: React.FC = () => {
    const { t, i18n } = useTranslation();
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const [isMobileMenuOpen, setIsMobileMenuOpen] = React.useState(false);
    const [isPasswordModalOpen, setIsPasswordModalOpen] = React.useState(false);
    const [allowedPaths, setAllowedPaths] = React.useState<string[]>([]);
    const [isPermissionsLoading, setIsPermissionsLoading] = React.useState(true);

    React.useEffect(() => {
        const fetchPermissions = async () => {
            try {
                const paths = await systemService.getMyMenuPermissions();
                setAllowedPaths(paths);
            } catch (error) {
                console.error('Failed to fetch menu permissions:', error);
            } finally {
                setIsPermissionsLoading(false);
            }
        };
        fetchPermissions();
    }, [user]);

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    const navItems = [
        { name: t('common.dashboard'), path: '/dashboard', icon: LayoutDashboard },
        { name: t('common.myCases'), path: '/cases', icon: FileText },
        { name: t('common.reviewCases'), path: '/reviews', icon: CheckSquare },
        { name: t('common.systemAudit'), path: '/logs', icon: ShieldAlert },
        { name: t('common.siemIntegration'), path: '/siem', icon: Settings },
        { name: t('common.userManagement'), path: '/users', icon: UserIcon },
        { name: t('common.envManagement'), path: '/env', icon: Settings },
        { name: t('common.backgroundJobs'), path: '/jobs', icon: LayoutDashboard },
        { name: t('common.menuPermissions'), path: '/permissions', icon: ShieldCheck },
        { name: t('common.integrations'), path: '/integrations', icon: Plug },
    ];

    return (
        <div className="h-screen bg-slate-50 flex overflow-hidden">
            {/* Sidebar */}
            <aside className={clsx(
                "fixed inset-y-0 left-0 z-50 w-64 bg-slate-900 text-white transition-transform duration-300 transform lg:translate-x-0 lg:relative lg:flex lg:flex-col shadow-2xl",
                isMobileMenuOpen ? "translate-x-0" : "-translate-x-full"
            )}>
                <div className="flex flex-col h-full">
                    {/* Logo */}
                    <div className="h-16 flex items-center px-6 border-b border-slate-800">
                        <ShieldAlert className="w-8 h-8 text-sky-500 mr-3" />
                        <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-sky-400 to-blue-600">
                            SICS
                        </span>
                        <button
                            className="ml-auto lg:hidden text-slate-400 hover:text-white"
                            onClick={() => setIsMobileMenuOpen(false)}
                        >
                            <X className="w-6 h-6" />
                        </button>
                    </div>

                    {/* Nav Items */}
                    <nav className="flex-1 px-3 py-6 space-y-1 overflow-y-auto scrollbar-hide">
                        {!isPermissionsLoading && navItems.filter(item => allowedPaths.includes(item.path)).map((item) => (
                            <NavLink
                                key={item.path}
                                to={item.path}
                                className={({ isActive }) => clsx(
                                    "flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-colors duration-200 group",
                                    isActive
                                        ? "bg-sky-600/20 text-sky-400"
                                        : "text-slate-400 hover:bg-slate-800 hover:text-white"
                                )}
                                onClick={() => setIsMobileMenuOpen(false)}
                            >
                                <item.icon className="w-5 h-5 mr-3 group-hover:animate-pulse" />
                                {item.name}
                            </NavLink>
                        ))}
                    </nav>

                    {/* User Profile & Logout */}
                    <div className="p-4 border-t border-slate-800">
                        <div className="flex items-center mb-4 px-2">
                            <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center text-slate-300 mr-3">
                                <UserIcon className="w-4 h-4" />
                            </div>
                            <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-white truncate">{user?.user_name || t('common.profile')}</p>
                                <p className="text-xs text-slate-500 truncate">{user?.role || t('common.role')}</p>
                            </div>
                        </div>
                        <div className="space-y-2">
                             <LanguageSwitcher variant="sidebar" />
                            <button
                                onClick={() => setIsPasswordModalOpen(true)}
                                className="w-full flex items-center justify-center px-4 py-2 text-sm font-medium text-slate-400 bg-slate-800/50 hover:bg-sky-500/10 hover:text-sky-400 rounded-lg transition-colors border border-transparent hover:border-sky-500/20"
                            >
                                <Key className="w-4 h-4 mr-2" />
                                {t('common.changePassword')}
                            </button>
                            <button
                                onClick={handleLogout}
                                className="w-full flex items-center justify-center px-4 py-2 text-sm font-medium text-slate-400 bg-slate-800/50 hover:bg-red-500/10 hover:text-red-400 rounded-lg transition-colors border border-transparent hover:border-red-500/20"
                            >
                                <LogOut className="w-4 h-4 mr-2" />
                                {t('common.logout')}
                            </button>
                        </div>
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
                {/* Mobile Header */}
                <header className="bg-white border-b border-slate-200 lg:hidden h-16 flex items-center px-4 justify-between">
                    <button
                        className="text-slate-500 hover:text-slate-700"
                        onClick={() => setIsMobileMenuOpen(true)}
                    >
                        <Menu className="w-6 h-6" />
                    </button>
                    <span className="font-semibold text-slate-900">SICS</span>
                    <div className="w-6" /> {/* Spacer */}
                </header>

                {/* Content Area */}
                <main className="flex-1 overflow-y-auto bg-slate-50 p-4 lg:p-8">
                    <Outlet key={i18n.language} />
                </main>
            </div>

            <ChangePasswordModal
                isOpen={isPasswordModalOpen}
                onClose={() => setIsPasswordModalOpen(false)}
            />

            {/* Mobile Overlay */}
            {isMobileMenuOpen && (
                <div
                    className="fixed inset-0 bg-black/50 z-40 lg:hidden backdrop-blur-sm"
                    onClick={() => setIsMobileMenuOpen(false)}
                />
            )}
        </div>
    );
};

export default Layout;
