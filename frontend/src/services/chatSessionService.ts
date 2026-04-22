import { api } from '../api/api';

export type StoredChatProvider = 'gpt' | 'perplexity';

export interface StoredChatMessageDTO {
  role: 'system' | 'user' | 'assistant';
  content: unknown;
}

export interface StoredChatSessionSummary {
  id: string;
  provider: StoredChatProvider;
  title: string;
  display_model: string;
  external_conversation_id: string | null;
  updated_at: string;
}

export interface StoredChatSessionDetail extends StoredChatSessionSummary {
  metadata: Record<string, unknown>;
  messages: StoredChatMessageDTO[];
}

export interface SaveChatSessionPayload {
  provider: StoredChatProvider;
  title: string;
  display_model?: string;
  conversation_id?: string | null;
  session_id?: string;
  messages?: StoredChatMessageDTO[];
}

export const chatSessionService = {
  async saveSession(payload: SaveChatSessionPayload) {
    const { data } = await api.post<StoredChatSessionSummary>('/chat/sessions/save', payload);
    return data;
  },

  async listSessions(provider?: StoredChatProvider) {
    const { data } = await api.get<StoredChatSessionSummary[]>(
      '/chat/sessions/',
      {
        params: provider ? { provider } : undefined,
      }
    );
    return data;
  },

  async getSession(sessionId: string) {
    const { data } = await api.get<StoredChatSessionDetail>(`/chat/sessions/${sessionId}/`);
    return data;
  },

  async deleteSession(sessionId: string) {
    await api.delete(`/chat/sessions/${sessionId}/`);
  },
};
