import { client } from './client';
import { SiemConfiguration, SiemSyncHistory } from '../types';

/** SIEM 연결 테스트 결과. 성공 시 data에 조회된 원본 로그 행이 들어 있다 */
export interface SiemTestResult {
    status: string;
    message: string;
    data?: Record<string, unknown>[];
}

export const siemService = {
    getConfigs: async (): Promise<SiemConfiguration[]> => {
        const response = await client.get<SiemConfiguration[]>('/siem/config');
        return response.data;
    },

    createConfig: async (config: SiemConfiguration): Promise<SiemConfiguration> => {
        const response = await client.post<SiemConfiguration>('/siem/config', config);
        return response.data;
    },

    updateConfig: async (configId: number, config: SiemConfiguration): Promise<SiemConfiguration> => {
        const response = await client.put<SiemConfiguration>(`/siem/config/${configId}`, config);
        return response.data;
    },

    testConnection: async (config: SiemConfiguration): Promise<SiemTestResult> => {
        const response = await client.post<SiemTestResult>('/siem/test-connection', config);
        return response.data;
    },

    deleteConfig: async (configId: number): Promise<void> => {
        await client.delete(`/siem/config/${configId}`);
    },

    convertCase: async (logData: Record<string, unknown>, mappingOverride?: Record<string, string>): Promise<{ status: string; case_id: number; message: string }> => {
        const payload: { log_data: Record<string, unknown>; mapping_override?: Record<string, string> } = { log_data: logData };
        if (mappingOverride) {
            payload.mapping_override = mappingOverride;
        }
        const response = await client.post<{ status: string; case_id: number; message: string }>('/siem/convert-case', payload);
        return response.data;
    },

    getHistory: async (configId?: number): Promise<SiemSyncHistory[]> => {
        const url = configId ? `/siem/history?config_id=${configId}` : '/siem/history';
        const response = await client.get<SiemSyncHistory[]>(url);
        return response.data;
    }
};
