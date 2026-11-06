import { client } from './client';
import { SiemConfiguration, SiemSyncHistory } from '../types';

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

    testConnection: async (config: SiemConfiguration): Promise<{ status: string; message: string }> => {
        const response = await client.post<{ status: string; message: string }>('/siem/test-connection', config);
        return response.data;
    },

    deleteConfig: async (configId: number): Promise<void> => {
        await client.delete(`/siem/config/${configId}`);
    },

    convertCase: async (logData: any, mappingOverride?: Record<string, string>): Promise<{ status: string; case_id: number; message: string }> => {
        const payload: any = { log_data: logData };
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
