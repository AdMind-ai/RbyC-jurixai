import { StoredChatProvider } from '../services/chatSessionService';

export interface StoredChatSelection {
  id: string;
  name: string;
  provider: StoredChatProvider;
  thread_id: string | null;
}
