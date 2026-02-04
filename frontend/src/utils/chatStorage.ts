import { StoredChatMessageDTO } from '../services/chatSessionService';

export type SimpleChatMessage = {
  sender: 'user' | 'ai';
  content: string;
};

export const mapMessagesToStoredPayload = (
  messages: Array<SimpleChatMessage>
): StoredChatMessageDTO[] =>
  messages.map((message) => ({
    role: message.sender === 'user' ? 'user' : 'assistant',
    content: [
      {
        type: 'text',
        text: message.content,
      },
    ],
  }));
