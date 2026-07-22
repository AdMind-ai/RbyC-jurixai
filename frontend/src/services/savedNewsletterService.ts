import { api } from '../api/api';

export type NewsletterType = 'newsletter' | 'pill';
export type NewsletterSource = 'manual' | 'auto';

export interface SavedNewsletterSummary {
  id: string;
  title: string;
  newsletter_type: NewsletterType;
  newsletter_type_display: string;
  source: NewsletterSource;
  source_display: string;
  preview: string;
  generated_at: string | null;
  created_at: string;
}

export interface SavedNewsletter extends SavedNewsletterSummary {
  content: string;
  metadata?: Record<string, unknown>;
}

export const savedNewsletterService = {
  async list(): Promise<SavedNewsletterSummary[]> {
    const { data } = await api.get<SavedNewsletterSummary[]>('/newsletter/saved/');
    return data;
  },

  async get(id: string): Promise<SavedNewsletter> {
    const { data } = await api.get<SavedNewsletter>(`/newsletter/saved/${id}/`);
    return data;
  },

  async save(payload: {
    title?: string;
    content: string;
    metadata?: Record<string, unknown>;
    newsletter_type?: NewsletterType;
  }): Promise<SavedNewsletter> {
    const { data } = await api.post<SavedNewsletter>('/newsletter/saved/', payload);
    return data;
  },

  async delete(id: string): Promise<void> {
    await api.delete(`/newsletter/saved/${id}/`);
  },
};
