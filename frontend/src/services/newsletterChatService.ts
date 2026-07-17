import { api } from '../api/api';

export type NewsletterDraftType = 'newsletter' | 'pill';

export interface NewsletterChatResponse {
  answer: string;
  sessionKey: string;
}

export const newsletterChatService = {
  async sendMessage(
    message: string,
    draftType: NewsletterDraftType,
    sessionId?: string,
  ): Promise<NewsletterChatResponse> {
    const { data } = await api.post<NewsletterChatResponse>('/newsletter/chat/', {
      message,
      draft_type: draftType,
      ...(sessionId ? { session_id: sessionId } : {}),
    });
    return data;
  },
};
