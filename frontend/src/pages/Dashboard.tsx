import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { caseService } from '../services/case.service';
import DateRangeFilter from '../components/DateRangeFilter';
import StatsCards from '../components/dashboard/StatsCards';
import CasesChart from '../components/dashboard/CasesChart';
import StatusFilter from '../components/dashboard/StatusFilter';
import CasesTable from '../components/dashboard/CasesTable';
import DailyStatsChart from '../components/dashboard/DailyStatsChart';
import WeeklyReportWidget from '../components/dashboard/WeeklyReportWidget';

interface FilterState {
    case_status: string | null;
    priority: string | null;
    case_type: string | null;
    date: string | null;
    startDate: string | null;
    endDate: string | null;
}

const Dashboard: React.FC = () => {
    const { t } = useTranslation();
    const { user, role } = useAuth();

    // 관리자(보안/시스템) 및 감사팀 권한 여부 확인 (일반 사용자는 전사 통계 미노출)
    const isAdminOrAudit = role === '보안관리자' || role === '감사팀' || role === '시스템관리자';

    const [filters, setFilters] = useState<FilterState>(() => {
        const today = new Date();
        const twoWeeksAgo = new Date();
        twoWeeksAgo.setDate(today.getDate() - 14);

        return {
            case_status: null,
            priority: null,
            case_type: null,
            date: null,
            startDate: twoWeeksAgo.toISOString().split('T')[0],
            endDate: today.toISOString().split('T')[0]
        };
    });

    const { data: stats } = useQuery({
        queryKey: ['caseStats', filters.startDate, filters.endDate, filters.case_status, filters.priority, filters.case_type],
        queryFn: () => caseService.getCaseStats(
            filters.startDate,
            filters.endDate,
            filters.case_status,
            filters.priority,
            filters.case_type
        )
    });

    // 일일 통계 로딩 (최근 14일, 관리자 및 감사팀 전용)
    const { data: dailyStatsData } = useQuery({
        queryKey: ['dailyStats', 14],
        queryFn: () => caseService.getDailyStats(14),
        staleTime: 5 * 60 * 1000, // 5분 캐싱
        enabled: isAdminOrAudit
    });

    // 주간 보고서 로딩 (최근 5주, 관리자 및 감사팀 전용)
    const { data: weeklyReportsData } = useQuery({
        queryKey: ['weeklyReports', 5],
        queryFn: () => caseService.getWeeklyReports(5),
        staleTime: 5 * 60 * 1000,
        enabled: isAdminOrAudit
    });

    const toggleFilter = (type: string, value: string) => {
        const key = type as keyof FilterState;
        setFilters(prev => ({
            ...prev,
            [key]: prev[key] === value ? null : value
        }));
    };

    const clearFilters = () => {
        const today = new Date();
        const twoWeeksAgo = new Date();
        twoWeeksAgo.setDate(today.getDate() - 14);

        setFilters({
            case_status: null,
            priority: null,
            case_type: null,
            date: null,
            startDate: twoWeeksAgo.toISOString().split('T')[0],
            endDate: today.toISOString().split('T')[0]
        });
    };

    const activeFilterCount = Object.values(filters).filter(v => v !== null).length;

    return (
        <div className="-mt-[10px] space-y-2 max-w-full mx-auto pb-4 px-2">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between space-y-1 lg:space-y-0">
                <div>
                    <h1 className="text-xl md:text-2xl font-bold text-slate-900">{t('dashboard.title')}</h1>
                    <p className="text-sm text-slate-500 mt-1">
                        {t('dashboard.welcome', { name: user?.user_name })}
                    </p>
                </div>

                <DateRangeFilter
                    startDate={filters.startDate || ''}
                    endDate={filters.endDate || ''}
                    onStartDateChange={(val) => setFilters(p => ({ ...p, startDate: val || null }))}
                    onEndDateChange={(val) => setFilters(p => ({ ...p, endDate: val || null }))}
                />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-10 gap-2 items-stretch">
                <StatsCards
                    stats={stats}
                    filters={filters}
                    toggleFilter={toggleFilter}
                    clearFilters={clearFilters}
                    activeFilterCount={activeFilterCount}
                />

                <CasesChart
                    chartDataRaw={stats?.chart_data}
                    filters={filters}
                    toggleFilter={toggleFilter}
                />
            </div>

            {isAdminOrAudit && (
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
                    <div className="lg:col-span-8">
                        <DailyStatsChart dailyStatsData={dailyStatsData || []} />
                    </div>
                    <div className="lg:col-span-4">
                        <WeeklyReportWidget data={weeklyReportsData || []} />
                    </div>
                </div>
            )}

            <StatusFilter
                stats={stats}
                filters={filters}
                toggleFilter={toggleFilter}
            />

            <CasesTable
                filters={filters}
                activeFilterCount={activeFilterCount}
            />
        </div>
    );
};

export default Dashboard;
