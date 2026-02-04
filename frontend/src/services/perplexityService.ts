import { fetchWithAuth } from '../api/fetchWithAuth';

type ConversationMessage = {
    role: 'user' | 'ai';
    content: string;
};

type GeneratePerplexityOptions = {
    prompt: string;
    files?: File[];
    conversation?: ConversationMessage[];
    conversationId?: string | null;
    onChunk?: (chunk: string, isFinal: boolean) => void;
};

interface GeneratePerplexityResult {
    fullResponse: string;
    conversationId: string | null;
}

class PerplexityService {

    public async generatePerplexityResponse({
        prompt,
        files = [],
        conversation = [],
        conversationId,
        onChunk
    }: GeneratePerplexityOptions): Promise<GeneratePerplexityResult> {
        try {
            const historyMessages = conversation.map(message => ({
                role: message.role === 'user' ? 'user' : 'assistant',
                content: [
                    {
                        type: 'text',
                        text: message.content
                    }
                ]
            }));

            const formData = new FormData();
            formData.append('input', prompt);
            files.forEach(file => formData.append('file', file));
            if (historyMessages.length > 0) {
                formData.append('conversation', JSON.stringify(historyMessages));
            }
            if (conversationId) {
                formData.append('conversation_id', conversationId);
            }

            const response = await fetchWithAuth('/perplexity/chat/assistant', {
                method: 'POST',
                body: formData
            });

            if (!response.ok || !response.body) {
                throw new Error(`Perplexity backend error: ${response.status} ${response.statusText}`);
            }

            const headerConversationId = response.headers.get('X-Conversation-ID');

            const reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let fullResponse = '';
            let isDone = false;

            while (!isDone) {
                const { value, done } = await reader.read();
                isDone = done;
                const chunkText = decoder.decode(value || new Uint8Array(), { stream: !done });
                if (chunkText) {
                    fullResponse += chunkText;
                    onChunk?.(chunkText, false);
                }
            }

            onChunk?.('', true);
            return {
                fullResponse,
                conversationId: headerConversationId || conversationId || null,
            };
        } catch (error) {
            console.error('Error generating Perplexity response:', error);
            throw error;
        }
    }
}

export const perplexityService = new PerplexityService();