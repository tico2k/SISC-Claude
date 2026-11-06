import { client } from './client';
import { LoginCredentials, RegisterData, AuthResponse, User, EntraLoginRequest, AuthConfig, LoginHistoryResponse } from '../types';

export const authService = {
    login: async (credentials: LoginCredentials): Promise<AuthResponse> => {
        // OAuth2PasswordRequestForm expects form data
        const formData = new URLSearchParams();
        formData.append('username', credentials.user_email);
        formData.append('password', credentials.password);

        const response = await client.post<AuthResponse>('/login', formData, {
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
        });
        return response.data;
    },

    register: async (data: RegisterData): Promise<User> => {
        const response = await client.post<User>('/register', data);
        return response.data;
    },

    loginEntra: async (data: EntraLoginRequest): Promise<AuthResponse> => {
        const response = await client.post<AuthResponse>('/login/entra', data);
        return response.data;
    },

    getAuthConfig: async (): Promise<AuthConfig> => {
        const response = await client.get<AuthConfig>('/config');
        return response.data;
    },

    // Helper to decode token or get user profile if needed
    // For now assuming we just store token and role is in token payload or separate profile call

    changePassword: async (oldPassword: string, newPassword: string): Promise<void> => {
        await client.post('/pwchange', { old_password: oldPassword, new_password: newPassword });
    },

    createLoginHistory: async (status: string): Promise<void> => {
        await client.post('/loginhistory', null, { params: { status } });
    },

    getLoginHistory: async (skip = 0, limit = 100): Promise<LoginHistoryResponse[]> => {
        const response = await client.get<LoginHistoryResponse[]>('/loginhistory', { params: { skip, limit } });
        return response.data;
    }
};
