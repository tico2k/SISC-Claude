import { client } from './client';
import { User, UserRegisterRequest } from '../types';

export const userService = {
    getUsers: async (): Promise<User[]> => {
        const response = await client.get<User[]>('/users');
        return response.data;
    },

    createUser: async (user: UserRegisterRequest): Promise<User> => {
        const response = await client.post<User>('/users', user);
        return response.data;
    },

    updateUser: async (userId: number, userData: Partial<User>): Promise<User> => {
        const response = await client.put<User>(`/users/${userId}`, userData);
        return response.data;
    },

    deleteUser: async (userId: number): Promise<void> => {
        await client.delete(`/users/${userId}`);
    },

    uploadUsers: async (formData: FormData): Promise<any> => {
        const response = await client.post<any>('/system/users/upload', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
        return response.data;
    },

    syncUsersFromEntra: async (): Promise<any> => {
        const response = await client.post<any>('/users/sync-entra');
        return response.data;
    }
};
