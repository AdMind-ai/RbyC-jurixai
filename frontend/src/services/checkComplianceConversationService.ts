import { api } from '../api/api';
import { CheckComplianceChatDocumentReference } from './checkComplianceChatService';

export interface CheckComplianceStoredFile {
  name: string;
  size: number;
}

export interface CheckComplianceStoredMessage {
  id?: string;
  role: 'user' | 'assistant';
  content: string;
  files?: CheckComplianceStoredFile[];
  documents?: CheckComplianceChatDocumentReference[];
  created_at?: string;
}

export interface CheckComplianceConversationSummary {
  id: string;
  title: string;
  vera_session_id: string;
  created_at: string;
  updated_at: string;
}

export interface CheckComplianceConversationDetail extends CheckComplianceConversationSummary {
  messages: CheckComplianceStoredMessage[];
}

export interface SaveCheckComplianceConversationPayload {
  conversation_id?: string;
  title: string;
  vera_session_id: string;
  messages: CheckComplianceStoredMessage[];
}

export const checkComplianceConversationService = {
  async listConversations() {
    const { data } = await api.get<CheckComplianceConversationSummary[]>(
      '/check-compliance/chat/conversations/'
    );
    return data;
  },

  async saveConversation(payload: SaveCheckComplianceConversationPayload) {
    const { data } = await api.post<CheckComplianceConversationSummary>(
      '/check-compliance/chat/conversations/',
      payload
    );
    return data;
  },

  async getConversation(conversationId: string) {
    const { data } = await api.get<CheckComplianceConversationDetail>(
      `/check-compliance/chat/conversations/${conversationId}/`
    );
    return data;
  },

  async deleteConversation(conversationId: string) {
    await api.delete(`/check-compliance/chat/conversations/${conversationId}/`);
  },
};
