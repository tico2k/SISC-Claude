import { client } from './client';
import { JobTriggerPayload } from '../types';

export interface AuditLog {
    log_id: number;
    actor_id?: number;
    user_id?: number;
    action: string;
    ip_address?: string;
    occurred_at: string;
    actor?: {
        user_name: string;
        user_email: string;
    };
}

export interface EnvEntry {
    key: string;
    value: string;
    is_sensitive: boolean;
    category: string;
    description: string;
}

export interface EnvResponse {
    backend: EnvEntry[];
    frontend: EnvEntry[];
}

export interface JobResponse {
    id: string;
    name: string;
    next_run_time?: string;
    status: 'RUNNING' | 'PAUSED';
    cron_expression?: string;
}

export interface BackgroundJobLog {
    log_id: number;
    job_id: string;
    job_name: string;
    status: string;
    execution_type: 'AUTO' | 'MANUAL';
    execution_time: string;
    records_processed: number;
    message?: string;
}

export interface JobLogFilter {
    job_id: string;
    job_name: string;
}

export interface MenuPermission {
    permission_id: number;
    role: string;
    menu_path: string;
    is_visible: boolean;
}

export const systemService = {
    getAuditLogs: async (skip = 0, limit = 100): Promise<AuditLog[]> => {
        const response = await client.get<AuditLog[]>('/audit-logs', {
            params: { skip, limit }
        });
        return response.data;
    },
    getEnv: async (): Promise<EnvResponse> => {
        const response = await client.get<EnvResponse>('/system/env');
        return response.data;
    },
    updateEnv: async (fileType: 'backend' | 'frontend', key: string, value: string): Promise<{ message: string }> => {
        const response = await client.post<{ message: string }>('/system/env', {
            file_type: fileType,
            key,
            value
        });
        return response.data;
    },
    getJobs: async (): Promise<JobResponse[]> => {
        const response = await client.get<JobResponse[]>('/system/jobs');
        return response.data;
    },
    pauseJob: async (jobId: string): Promise<{ message: string }> => {
        const response = await client.post<{ message: string }>(`/system/jobs/${jobId}/pause`);
        return response.data;
    },
    resumeJob: async (jobId: string): Promise<{ message: string }> => {
        const response = await client.post<{ message: string }>(`/system/jobs/${jobId}/resume`);
        return response.data;
    },
    triggerJob: async (jobId: string, payload?: JobTriggerPayload): Promise<{ message: string }> => {
        const response = await client.post<{ message: string }>(`/system/jobs/${jobId}/trigger`, payload || {});
        return response.data;
    },
    getJobLogs: async (jobId?: string, limit = 100): Promise<BackgroundJobLog[]> => {
        const response = await client.get<BackgroundJobLog[]>('/system/jobs/logs', {
            params: { job_id: jobId, limit }
        });
        return response.data;
    },
    getJobLogFilters: async (): Promise<JobLogFilter[]> => {
        const response = await client.get<JobLogFilter[]>('/system/jobs/log-filters');
        return response.data;
    },
    rescheduleJob: async (jobId: string, cronExpression: string): Promise<{ message: string }> => {
        const response = await client.post<{ message: string }>(`/system/jobs/${jobId}/reschedule`, {
            cron_expression: cronExpression
        });
        return response.data;
    },
    getMenuPermissions: async (): Promise<MenuPermission[]> => {
        const response = await client.get<MenuPermission[]>('/system/permissions');
        return response.data;
    },
    updateMenuPermissions: async (payload: MenuPermission[]): Promise<{ message: string }> => {
        const response = await client.post<{ message: string }>('/system/permissions/bulk-update', payload);
        return response.data;
    },
    getMyMenuPermissions: async (): Promise<string[]> => {
        const response = await client.get<string[]>('/system/permissions/my');
        return response.data;
    }
};
