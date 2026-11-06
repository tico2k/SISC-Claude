import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { authService } from '../services/auth.service';
import { Mail, Lock, User as UserIcon, Building, Shield } from 'lucide-react';
import LanguageSwitcher from '../components/LanguageSwitcher';

const RegisterPage: React.FC = () => {
    const { t } = useTranslation();
    const navigate = useNavigate();
    const [formData, setFormData] = useState({
        user_email: '',
        password: '',
        user_name: '',
        company: '',
        department: '',
        role: '일반'
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError('');
        try {
            await authService.register(formData);
            alert(t('register.successAlert'));
            navigate('/login');
        } catch (err) {
            setError(t('register.failError'));
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
            <div className="absolute top-4 right-4">
                <LanguageSwitcher />
            </div>
            <div className="w-full max-w-md bg-white/10 backdrop-blur-lg rounded-2xl shadow-xl overflow-hidden border border-white/20">
                <div className="p-8">
                    <div className="text-center mb-8">
                        <h1 className="text-3xl font-bold text-white mb-2">{t('register.title')}</h1>
                        <p className="text-slate-300">{t('register.subtitle')}</p>
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div className="relative">
                            <UserIcon className="absolute left-3 top-3 h-5 w-5 text-slate-400" />
                            <input
                                name="user_name"
                                placeholder={t('register.name')}
                                value={formData.user_name}
                                onChange={handleChange}
                                required
                                className="w-full pl-10 pr-3 py-2.5 bg-slate-800/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-500"
                            />
                        </div>
                        <div className="relative">
                            <Mail className="absolute left-3 top-3 h-5 w-5 text-slate-400" />
                            <input
                                name="user_email"
                                type="email"
                                placeholder={t('register.email')}
                                value={formData.user_email}
                                onChange={handleChange}
                                required
                                className="w-full pl-10 pr-3 py-2.5 bg-slate-800/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-500"
                            />
                        </div>
                        <div className="relative">
                            <Lock className="absolute left-3 top-3 h-5 w-5 text-slate-400" />
                            <input
                                name="password"
                                type="password"
                                placeholder={t('register.password')}
                                value={formData.password}
                                onChange={handleChange}
                                required
                                className="w-full pl-10 pr-3 py-2.5 bg-slate-800/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-500"
                            />
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="relative">
                                <Building className="absolute left-3 top-3 h-5 w-5 text-slate-400" />
                                <input
                                    name="company"
                                    placeholder={t('register.company')}
                                    value={formData.company}
                                    onChange={handleChange}
                                    className="w-full pl-10 pr-3 py-2.5 bg-slate-800/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-500"
                                />
                            </div>
                            <div className="relative">
                                <input
                                    name="department"
                                    placeholder={t('register.department')}
                                    value={formData.department}
                                    onChange={handleChange}
                                    className="w-full px-3 py-2.5 bg-slate-800/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-500"
                                />
                            </div>
                        </div>

                        <div className="relative">
                            <Shield className="absolute left-3 top-3 h-5 w-5 text-slate-400" />
                            <select
                                name="role"
                                value={formData.role}
                                onChange={handleChange}
                                className="w-full pl-10 pr-3 py-2.5 bg-slate-800/50 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-sky-500 appearance-none"
                            >
                                <option value="일반" className="bg-slate-800 text-white">{t('system.user.roles.user')}</option>
                                <option value="보안관리자" className="bg-slate-800 text-white">{t('system.user.roles.security_admin')}</option>
                                <option value="감사팀" className="bg-slate-800 text-white">{t('system.user.roles.audit')}</option>
                            </select>
                        </div>

                        {error && (
                            <div className="text-red-400 text-sm text-center">{error}</div>
                        )}

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full bg-sky-600 hover:bg-sky-500 text-white font-semibold py-3 px-4 rounded-lg transition-all flex items-center justify-center"
                        >
                            {loading ? t('register.submitting') : t('register.submit')}
                        </button>

                        <div className="text-center mt-4">
                            <Link to="/login" className="text-slate-400 hover:text-white text-sm">
                                {t('register.alreadyHaveAccount')}
                            </Link>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
};

export default RegisterPage;
