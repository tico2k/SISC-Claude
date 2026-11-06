import React, { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Activity } from 'lucide-react';
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer
} from 'recharts';

interface DailyStatsChartProps {
    dailyStatsData: any[];
}

const DailyStatsChart: React.FC<DailyStatsChartProps> = ({ dailyStatsData }) => {
    const { t } = useTranslation();
    const chartData = useMemo(() => {
        if (!dailyStatsData || dailyStatsData.length === 0) return [];

        return dailyStatsData.map(stat => ({
            name: stat.date.slice(5), // MM-DD
            fullDate: stat.date,
            [t('dashboard.daily.unclassified')]: stat.unclassified,
            [t('dashboard.daily.requested')]: stat.request,
            [t('dashboard.daily.submitted')]: stat.submit,
            [t('dashboard.daily.reviewed')]: stat.reviewed
        }));
    }, [dailyStatsData, t]);

    if (!dailyStatsData || dailyStatsData.length === 0) {
        return (
            <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 mt-2 mb-2 h-full min-h-[350px] flex flex-col justify-between">
                <div className="flex items-center space-x-2">
                    <Activity className="w-5 h-5 text-indigo-500" />
                    <h3 className="text-sm md:text-base font-bold text-slate-900">{t('dashboard.daily.title')}</h3>
                </div>
                <div className="flex flex-col items-center justify-center my-auto py-8 text-center">
                    <div className="w-12 h-12 rounded-full bg-slate-50 flex items-center justify-center mb-3 border border-slate-100">
                        <Activity className="w-6 h-6 text-slate-400" />
                    </div>
                    <p className="text-sm font-medium text-slate-600">{t('dashboard.daily.noData')}</p>
                    <p className="text-xs text-slate-400 mt-1 max-w-sm">{t('dashboard.daily.noDataSub')}</p>
                </div>
            </div>
        );
    }

    return (
        <div className="bg-white p-3 md:p-4 rounded-xl shadow-sm border border-slate-200 mt-2 mb-2 h-full min-h-[350px] flex flex-col">
            <div className="flex items-center space-x-2 mb-4">
                <Activity className="w-5 h-5 text-indigo-500" />
                <h3 className="text-sm md:text-base font-bold text-slate-900">{t('dashboard.daily.title')}</h3>
            </div>

            <div className="w-full h-[300px] mt-2">
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart
                        data={chartData}
                        margin={{ top: 10, right: 20, left: -20, bottom: 0 }}
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
                            cursor={{ stroke: '#e2e8f0', strokeWidth: 2 }}
                            contentStyle={{
                                backgroundColor: '#fff',
                                borderRadius: '12px',
                                border: '1px solid #e2e8f0',
                                boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)',
                                padding: '10px'
                            }}
                            itemStyle={{ fontSize: '12px', fontWeight: 'bold' }}
                            labelStyle={{ fontSize: '12px', color: '#64748b', marginBottom: '4px' }}
                        />
                        <Legend
                            verticalAlign="bottom"
                            height={36}
                            iconType="circle"
                            wrapperStyle={{ fontSize: '11px', fontWeight: 'bold', color: '#64748b', paddingTop: '15px' }}
                        />
                        <Line type="monotone" dataKey={t('dashboard.daily.unclassified')} stroke="#94a3b8" strokeWidth={3} dot={{ r: 4, strokeWidth: 2 }} activeDot={{ r: 6 }} />
                        <Line type="monotone" dataKey={t('dashboard.daily.requested')} stroke="#3b82f6" strokeWidth={3} dot={{ r: 4, strokeWidth: 2 }} activeDot={{ r: 6 }} />
                        <Line type="monotone" dataKey={t('dashboard.daily.submitted')} stroke="#f59e0b" strokeWidth={3} dot={{ r: 4, strokeWidth: 2 }} activeDot={{ r: 6 }} />
                        <Line type="monotone" dataKey={t('dashboard.daily.reviewed')} stroke="#10b981" strokeWidth={3} dot={{ r: 4, strokeWidth: 2 }} activeDot={{ r: 6 }} />
                    </LineChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};

export default DailyStatsChart;
