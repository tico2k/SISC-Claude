import { client } from './client';
import { NotificationPreview, NotificationTemplate } from '../types';

export const notificationService = {
    getTemplates: async (): Promise<NotificationTemplate[]> => {
        const response = await client.get<NotificationTemplate[]>('/notifications/templates');
        return response.data;
    },

    updateTemplate: async (key: string, subject: string, body_html: string): Promise<NotificationTemplate> => {
        const response = await client.put<NotificationTemplate>(`/notifications/templates/${encodeURIComponent(key)}`, { subject, body_html });
        return response.data;
    },

    resetTemplate: async (key: string): Promise<NotificationTemplate> => {
        const response = await client.delete<NotificationTemplate>(`/notifications/templates/${encodeURIComponent(key)}`);
        return response.data;
    },

    previewTemplate: async (key: string, subject: string, body_html: string): Promise<NotificationPreview> => {
        const response = await client.post<NotificationPreview>(`/notifications/templates/${encodeURIComponent(key)}/preview`, { subject, body_html });
        return response.data;
    },
};
