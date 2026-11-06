import { client } from './client';
import { Case, Submission, CaseStats, DailyStat, WeeklyReport, PaginatedCases } from '../types';

/** 쿼리 파라미터 (값이 있는 것만 담는다) */
type QueryParams = Record<string, string | number>;

export const caseService = {
    getCases: async (
        skip = 0,
        limit = 1000,
        case_status?: string | null,
        priority?: string | null,
        case_type?: string | null,
        start_date?: string | null,
        end_date?: string | null,
        sort_by?: string | null,
        order?: string | null,
        search?: string | null
    ): Promise<Case[]> => {
        const params: QueryParams = { skip, limit };
        if (case_status) params.case_status = case_status;
        if (priority) params.priority = priority;
        if (case_type) params.case_type = case_type;
        if (start_date) params.start_date = start_date;
        if (end_date) params.end_date = end_date;
        if (search) params.search = search;
        if (sort_by) params.sort_by = sort_by;
        if (order) params.order = order;

        const response = await client.get<PaginatedCases>('/cases', { params });
        // 임시 하위 호환성 유지: 아직 Dashboard가 list를 기대하므로 items만 반환
        return response.data.items || [];
    },

    getCasesPaginated: async (
        skip = 0,
        limit = 10,
        case_status?: string | null,
        priority?: string | null,
        case_type?: string | null,
        start_date?: string | null,
        end_date?: string | null,
        sort_by?: string | null,
        order?: string | null,
        search?: string | null
    ): Promise<PaginatedCases> => {
        const params: QueryParams = { skip, limit };
        if (case_status) params.case_status = case_status;
        if (priority) params.priority = priority;
        if (case_type) params.case_type = case_type;
        if (start_date) params.start_date = start_date;
        if (end_date) params.end_date = end_date;
        if (search) params.search = search;
        if (sort_by) params.sort_by = sort_by;
        if (order) params.order = order;

        console.log("getCasesPaginated params:", params);

        const response = await client.get<PaginatedCases>('/cases', { params });
        return response.data;
    },

    getCaseStats: async (
        start_date?: string | null,
        end_date?: string | null,
        case_status?: string | null,
        priority?: string | null,
        case_type?: string | null
    ): Promise<CaseStats> => {
        const params: QueryParams = {};
        if (start_date) params.start_date = start_date;
        if (end_date) params.end_date = end_date;
        if (case_status) params.case_status = case_status;
        if (priority) params.priority = priority;
        if (case_type) params.case_type = case_type;

        const response = await client.get<CaseStats>('/cases/stats', { params });
        return response.data;
    },

    getCaseById: async (id: number): Promise<Case> => {
        const response = await client.get<Case>(`/cases/${id}`);
        return response.data; // Note: Ensure backend supports get by ID if implemented, otherwise filter from list
    },

    getDailyStats: async (days: number = 14): Promise<DailyStat[]> => {
        const response = await client.get<DailyStat[]>('/cases/daily-stats', {
            params: { days }
        });
        return response.data;
    },

    // Note: createCase is admin only

    getCaseHistory: async (): Promise<Case[]> => {
        const response = await client.get<Case[]>('/cases/history');
        return response.data;
    },

    submitClarification: async (caseId: number, content: string, classification?: string, files?: File[]): Promise<Submission> => {
        const formData = new FormData();
        formData.append('case_id', caseId.toString());
        formData.append('content', content);
        if (classification) formData.append('classification', classification);
        if (files) {
            files.forEach(file => {
                formData.append('files', file);
            });
        }

        const response = await client.post<Submission>('/submissions', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
        return response.data;
    },

    reviewCase: async (caseId: number, status: '승인' | '반려' | '종결', result: string, comments: string) => {
        const response = await client.post('/reviews', {
            case_id: caseId,
            case_status: status,
            case_result: result,
            comments: comments
        });
        return response.data;
    },

    updateStatus: async (caseId: number, status: string): Promise<void> => {
        await client.put(`/cases/${caseId}/status?status=${status}`);
    },

    downloadAttachment: async (fileId: number): Promise<Blob> => {
        const response = await client.get(`/attachments/${fileId}`, {
            responseType: 'blob'
        });
        return response.data;
    },

    requestClarification: async (caseId: number, dueDate: string, requestReason: string, files?: File[]): Promise<Case> => {
        const formData = new FormData();
        formData.append('due_date', dueDate);
        formData.append('request_reason', requestReason);
        if (files) {
            files.forEach(file => {
                formData.append('files', file);
            });
        }

        const response = await client.post<Case>(`/cases/${caseId}/request`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
        return response.data;
    },

    closeCase: async (caseId: number, result: string, reason: string): Promise<Case> => {
        const response = await client.post<Case>(`/cases/${caseId}/close`, {
            case_result: result,
            close_reason: reason
        });
        return response.data;
    },

    getWeeklyReports: async (limit: number = 5): Promise<WeeklyReport[]> => {
        const response = await client.get<WeeklyReport[]>(`/cases/weekly-reports?limit=${limit}`);
        return response.data;
    }
};
