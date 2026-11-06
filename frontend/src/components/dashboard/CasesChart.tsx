import React, { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { TrendingUp } from 'lucide-react';
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer
} from 'recharts';
import { CaseStatsChartPoint, DashboardFilters } from '../../types';

interface CasesChartProps {
    chartDataRaw?: CaseStatsChartPoint[];
    filters: DashboardFilters;
    toggleFilter: (type: string, value: string) => void;
}

const CasesChart: React.FC<CasesChartProps> = ({ chartDataRaw, filters, toggleFilter }) => {
    const { t } = useTranslation();
    // Process backend raw chart data into Recharts format
    const chartData = useMemo(() => {
        if (!chartDataRaw) return [];

        // Ensure we show last 20 days sequentially
        const last20Days = Array.from({ length: 20 }, (_, i) => {
            const d = new Date();
            d.setDate(d.getDate() - i);
            return d.toISOString().split('T')[0];
        }).reverse();

        return last20Days.map(date => {
            const dayRecords = chartDataRaw.filter(c => c.date === date);
            return {
                name: date.slice(5), // MM-DD
                fullDate: date,
                '정보유출': dayRecords.find(c => c.case_type === '정보유출')?.count || 0,
                '보안위반': dayRecords.find(c => c.case_type === '보안위반')?.count || 0,
                '시스템접근': dayRecords.find(c => c.case_type === '시스템접근')?.count || 0,
                '권한오남용': dayRecords.find(c => c.case_type === '권한오남용')?.count || 0,
            };
        });
    }, [chartDataRaw]);

    return (
        <div className="md:col-span-2 lg:col-span-8 bg-white p-3 md:p-4 rounded-xl shadow-sm border border-slate-200 flex flex-col h-full min-h-[400px]">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-2 space-y-1 sm:space-y-0">
                <div className="flex items-center space-x-2">
                    <TrendingUp className="w-4 h-4 text-sky-500" />
                    <h3 className="text-sm md:text-base font-bold text-slate-900 line-clamp-1">{t('dashboard.chartTitle')}</h3>
                </div>
                {filters.date && (
                    <span className="self-start px-2 py-1 bg-sky-50 text-sky-700 text-xs font-bold rounded-md border border-sky-100">
                        {t('dashboard.filterLabel')}: {filters.date}
                    </span>
                )}
            </div>

            <div className="flex-grow">
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                        data={chartData}
                        onClick={(data) => {
                            if (data && data.activeTooltipIndex != null) {
                                const idx = Number(data.activeTooltipIndex);
                                if (chartData[idx]) toggleFilter('date', chartData[idx].fullDate);
                            }
                        }}
                        margin={{ top: 10, right: 10, left: -25, bottom: 0 }}
                    >
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                        <XAxis
                            dataKey="name"
                            fontSize={11}
                            tickLine={false}
                            axisLine={false}
                            tick={{ fill: '#94a3b8' }}
                        />
                        <YAxis
                            fontSize={11}
                            tickLine={false}
                            axisLine={false}
                            tick={{ fill: '#94a3b8' }}
                        />
                        <Tooltip
                            cursor={{ fill: '#f8fafc' }}
                            contentStyle={{
                                backgroundColor: '#fff',
                                borderRadius: '12px',
                                border: '1px solid #e2e8f0',
                                boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)',
                                padding: '10px'
                            }}
                            itemStyle={{ fontSize: '12px', fontWeight: 'bold' }}
                        />
                        <Legend
                            verticalAlign="bottom"
                            height={36}
                            iconType="circle"
                            wrapperStyle={{ fontSize: '11px', fontWeight: 'bold', color: '#64748b', paddingTop: '15px' }}
                        />
                        <Bar dataKey="정보유출" name={t('dashboard.typeLeak')} stackId="a" fill="#3b82f6" />
                        <Bar dataKey="보안위반" name={t('dashboard.typeViolation')} stackId="a" fill="#f59e0b" />
                        <Bar dataKey="시스템접근" name={t('dashboard.typeSystem')} stackId="a" fill="#6366f1" />
                        <Bar dataKey="권한오남용" name={t('dashboard.typeAbuse')} stackId="a" fill="#22c55e" radius={[4, 4, 0, 0]} />
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};

export default CasesChart;
