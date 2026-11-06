import React, { useEffect, useState } from 'react';
import { reportService } from '../api/reportService';
import { Report } from '../types/report';

const ReportList: React.FC = () => {
    const [reports, setReports] = useState<Report[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchReports = async () => {
            try {
                const data = await reportService.getReports();
                setReports(data);
            } catch (error) {
                console.error('Failed to fetch reports:', error);
            } finally {
                setLoading(false);
            }
        };

        fetchReports();
    }, []);

    if (loading) return <div>Loading reports...</div>;

    return (
        <div className="p-4 bg-white rounded-lg shadow-sm border border-gray-100">
            <h2 className="text-xl font-bold mb-4 text-gray-800">보고서 현황 (Sample Skill)</h2>
            <div className="space-y-3">
                {reports.length === 0 ? (
                    <p className="text-gray-500">등록된 보고서가 없습니다.</p>
                ) : (
                    reports.map((report) => (
                        <div key={report.id} className="p-3 bg-gray-50 rounded border border-gray-200">
                            <h3 className="font-semibold text-gray-700">{report.title}</h3>
                            <p className="text-sm text-gray-600">{report.summary}</p>
                            <span className="text-xs text-gray-400">
                                {new Date(report.created_at).toLocaleString()}
                            </span>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};

export default ReportList;
