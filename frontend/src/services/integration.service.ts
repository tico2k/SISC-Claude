import { client } from './client';
import { EntraIntegration, EntraIntegrationUpdate, IntegrationTestResult, TeamsIntegration, TeamsIntegrationUpdate } from '../types';

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

    getTeams: async (): Promise<TeamsIntegration> => {
        const response = await client.get<TeamsIntegration>('/integrations/teams');
        return response.data;
    },

    updateTeams: async (data: TeamsIntegrationUpdate): Promise<TeamsIntegration> => {
        const response = await client.put<TeamsIntegration>('/integrations/teams', data);
        return response.data;
    },

    testTeams: async (): Promise<IntegrationTestResult> => {
        const response = await client.post<IntegrationTestResult>('/integrations/teams/test');
        return response.data;
    },
};
