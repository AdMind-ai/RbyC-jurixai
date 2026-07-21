import { api } from '../api/api';
import { fetchWithAuth } from '../api/fetchWithAuth';

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

  async streamMessage(
    message: string,
    draftType: NewsletterDraftType,
    sessionId: string,
    onDelta: (delta: string) => void,
    onStatus?: (message: string) => void,
  ): Promise<NewsletterChatResponse> {
    const response = await fetchWithAuth('/newsletter/chat/', {
      method: 'POST',
      body: JSON.stringify({
        message,
        draft_type: draftType,
        session_id: sessionId,
        stream: true,
      }),
    });

    if (!response?.ok) {
      let detail = 'Non e stato possibile completare la richiesta. Riprova tra poco.';
      try {
        const payload = await response.json();
        detail = payload.detail || detail;
      } catch {
        // Keep the fallback message for non-JSON errors.
      }
      throw new Error(detail);
    }

    if (!response.body) {
      throw new Error('Streaming non disponibile per questa risposta.');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let answer = '';
    let sessionKey = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split('\n\n');
      buffer = events.pop() || '';

      for (const rawEvent of events) {
        const dataLine = rawEvent
          .split('\n')
          .find((line) => line.startsWith('data: '));

        if (!dataLine) continue;

        const payload = JSON.parse(dataLine.slice(6));

        if (payload.type === 'answer_delta') {
          const delta = payload.delta || '';
          answer += delta;
          sessionKey = payload.session_key || sessionKey;
          onDelta(delta);
        }

        if (payload.type === 'run_status') {
          sessionKey = payload.session_key || sessionKey;
          if (payload.message) {
            onStatus?.(payload.message);
          }
        }

        if (payload.type === 'answer_completed') {
          answer = payload.answer || answer;
          sessionKey = payload.session_key || sessionKey;
        }

        if (payload.type === 'error') {
          throw new Error(payload.message || 'Errore durante lo streaming.');
        }
      }
    }

    return { answer, sessionKey };
  },
};
