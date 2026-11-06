import React from 'react';
import { useTranslation } from 'react-i18next';

interface DateRangeFilterProps {
    startDate: string;
    endDate: string;
    onStartDateChange: (date: string) => void;
    onEndDateChange: (date: string) => void;
}

const DateRangeFilter: React.FC<DateRangeFilterProps> = ({
    startDate,
    endDate,
    onStartDateChange,
    onEndDateChange
}) => {
    const { t } = useTranslation();

    return (
        <div className="flex items-center border border-slate-200 rounded-xl bg-white px-3 py-1.5 shadow-sm space-x-3 w-full sm:w-auto overflow-x-auto min-h-[44px]">
            <div className="flex items-center space-x-2 flex-shrink-0 border-r border-slate-100 pr-3 mr-1">
                <span className="text-xs font-bold text-slate-500 whitespace-nowrap uppercase tracking-tighter">
                    {t('common.detectionDate', '탐지일')}
                </span>
            </div>
            <div className="flex items-center space-x-2">
                <input
                    type="date"
                    value={startDate}
                    onChange={(e) => onStartDateChange(e.target.value)}
                    className="text-sm border-none focus:ring-0 text-slate-600 font-semibold outline-none w-full max-w-[130px] py-0 bg-transparent"
                    placeholder={t('cases.filter.startDate', '시작일')}
                />
                <span className="text-slate-300 text-sm font-bold">~</span>
                <input
                    type="date"
                    value={endDate}
                    onChange={(e) => onEndDateChange(e.target.value)}
                    className="text-sm border-none focus:ring-0 text-slate-600 font-semibold outline-none w-full max-w-[130px] py-0 bg-transparent"
                    placeholder={t('cases.filter.endDate', '종료일')}
                />
            </div>
        </div>
    );
};

export default DateRangeFilter;
