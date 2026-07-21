import { api } from '../api/api';

export type NotificationType =
  | 'compliance_log'
  | 'newsletter_auto'
  | 'consumption_report'
  | 'consumption_low_balance'
  | 'consumption_threshold';

export interface Notification {
  id: string;
  notification_type: NotificationType;
  notification_type_display: string;
  title: string;
  body: string;
  reference_id: string;
  reference_type: string;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
}

export interface NotificationListResponse {
  results: Notification[];
  unread_count: number;
}

export const notificationService = {
  async list(params?: { type?: NotificationType; unread?: boolean }): Promise<NotificationListResponse> {
    const query: Record<string, string> = {};
    if (params?.type) query.type = params.type;
    if (params?.unread) query.unread = 'true';
    const { data } = await api.get<NotificationListResponse>('/notifications/', { params: query });
    return data;
  },

  async getUnreadCount(): Promise<number> {
    const { data } = await api.get<{ unread_count: number }>('/notifications/unread-count/');
    return data.unread_count;
  },

  async markRead(id: string): Promise<Notification> {
    const { data } = await api.post<Notification>(`/notifications/${id}/read/`);
    return data;
  },

  async markAllRead(): Promise<{ marked_read: number }> {
    const { data } = await api.post<{ marked_read: number }>('/notifications/read-all/');
    return data;
  },
};
