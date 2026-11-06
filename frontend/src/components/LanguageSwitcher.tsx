import React from 'react';
import { useTranslation } from 'react-i18next';
import { Languages } from 'lucide-react';
import { clsx } from 'clsx';

interface LanguageSwitcherProps {
  variant?: 'sidebar' | 'header';
}

const LanguageSwitcher: React.FC<LanguageSwitcherProps> = ({ variant = 'header' }) => {
  const { i18n } = useTranslation();

  const toggleLanguage = () => {
    const currentLang = i18n.resolvedLanguage || i18n.language;
    const newLang = currentLang.startsWith('ko') ? 'en' : 'ko';
    i18n.changeLanguage(newLang);
  };

  const isKorean = (i18n.resolvedLanguage || i18n.language || '').startsWith('ko');

  if (variant === 'sidebar') {
    return (
      <button
        onClick={toggleLanguage}
        className="w-full flex items-center justify-center px-4 py-2 text-sm font-medium text-slate-400 bg-slate-800/50 hover:bg-sky-500/10 hover:text-sky-400 rounded-lg transition-colors border border-transparent hover:border-sky-500/20 mb-2"
      >
        <Languages className="w-4 h-4 mr-2" />
        {isKorean ? 'English' : '한국어'}
      </button>
    );
  }

  return (
    <button
      onClick={toggleLanguage}
      className={clsx(
        "flex items-center px-3 py-1.5 text-sm font-medium rounded-md transition-all",
        "bg-white border border-slate-200 text-slate-600 hover:bg-slate-50 hover:border-slate-300"
      )}
    >
      <Languages className="w-4 h-4 mr-2 text-sky-500" />
      {isKorean ? 'EN' : 'KO'}
    </button>
  );
};

export default LanguageSwitcher;
