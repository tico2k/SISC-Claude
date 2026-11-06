// frontend/src/features/reports/api/reportService.ts
import { client as apiClient } from '../../../services/client'; // Adjust path if necessary
import { Report, ReportCreate } from '../types/report';

export const reportService = {
    getReports: async (): Promise<Report[]> => {
        const response = await apiClient.get<Report[]>('/reports');
        return response.data;
    },

    createReport: async (data: ReportCreate): Promise<Report> => {
        const response = await apiClient.post<Report>('/reports', data);
        return response.data;
    }
};
