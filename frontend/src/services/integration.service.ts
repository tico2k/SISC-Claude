import { client } from './client';
import { EntraIntegration, EntraIntegrationUpdate, IntegrationTestResult } from '../types';

export const integrationService = {
    getEntra: async (): Promise<EntraIntegration> => {
        const response = await client.get<EntraIntegration>('/integrations/entra');
        return response.data;
    },

    updateEntra: async (data: EntraIntegrationUpdate): Promise<EntraIntegration> => {
        const response = await client.put<EntraIntegration>('/integrations/entra', data);
        return response.data;
    },

    testEntra: async (): Promise<IntegrationTestResult> => {
        const response = await client.post<IntegrationTestResult>('/integrations/entra/test');
        return response.data;
    },
};
