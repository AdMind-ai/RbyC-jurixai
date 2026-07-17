import React, { useState, useEffect, useRef } from 'react';
import { fetchWithAuth } from '../../api/fetchWithAuth';
import { Paperclip, Send, X } from 'lucide-react';
import { ModelId } from '../../types/types'
import { StoredChatSelection } from '../../types/chat';

interface ChatInputAreaProps {
  onSend: (content: string, sender: 'user' | 'ai', isStream?: boolean) => void;
  selectedChat: StoredChatSelection | null;
  setSelectedChat: React.Dispatch<React.SetStateAction<StoredChatSelection | null>>;
  searchWebEnabled: boolean;
  setSearchWebEnabled: (enabled: boolean) => void;
  setIsOverview: React.Dispatch<React.SetStateAction<boolean>>;
  setIsTyping: React.Dispatch<React.SetStateAction<boolean>>;
  conversationId: string | null;
  selectedModel: ModelId;
  onConversationIdChange?: (model: ModelId, conversationId: string | null) => void;
  onConversationUpdated?: () => void;
  messages: Message[];
}

interface Attachment {
  name: string;
  mimeType?: string;
  data?: string;
}

interface Message {
  sender: 'user' | 'ai';
  content: string;
  citations?: string[];
  attachments?: Attachment[];
}

const ChatInputArea: React.FC<ChatInputAreaProps> = ({
  onSend,
  selectedChat,
  setSearchWebEnabled,
  setIsOverview,
  setIsTyping,
  conversationId,
  onConversationUpdated,
}) => {
  const [input, setInput] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      if (file.size > 4 * 1024 * 1024) {
        alert('Il file è troppo grande. Massimo 4MB.');
        return;
      }
      setFiles(prev => [...prev, file]);
    }
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleFileUploadClick = () => {
    setSearchWebEnabled(false);
    fileInputRef.current?.click();
  };

  function handleDeepResearchReady(e: CustomEvent<{
    conversationId: string | number,
    messageId: string | number,
    chatName: string,
    content: string,
    citations: string[]
  }>) {
    if (selectedChat && e.detail.conversationId === selectedChat.id) {
      setIsLoading(false);
      onSend(e.detail.content, "ai", true);
    }
  }

  useEffect(() => {
    const handler = handleDeepResearchReady as EventListener;
    window.addEventListener("deepResearchReady", handler);
    return () => window.removeEventListener("deepResearchReady", handler);
  }, [selectedChat, onSend]);

  const sendMessageWithGPT = async (payload: FormData) => {
    const response = await fetchWithAuth('/openai/chat/send-message/', {
      method: 'POST',
      body: payload
    });

    if (!response.ok || !response.body) {
      console.error('Erro ao conectar:', response.statusText);
      onSend('Erro ao conectar.', 'ai');
      setIsTyping(false);
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let done = false;

    while (!done) {
      const { value, done: doneReading } = await reader.read();
      done = doneReading;
      const chunkValue = decoder.decode(value, { stream: true });
      if (chunkValue) {
        onSend(chunkValue, 'ai', true);
      }
    }

    onConversationUpdated?.();
    setIsTyping(false);
  };

  const handleSubmit = async () => {
    if (!input.trim() && files.length === 0) {
      return;
    }

    const userMessage = input;
    const filesToUpload = [...files];
    const conversationRef = selectedChat?.thread_id ?? conversationId ?? null;

    setIsOverview(false);
    setIsTyping(true);
    setIsLoading(true);

    onSend(userMessage, 'user', false);
    setInput('');
    setFiles([]);

    try {
      const formData = new FormData();
      formData.append('content', userMessage);
      filesToUpload.forEach(file => formData.append('file', file));
      if (conversationRef) {
        formData.append('conversation_id', conversationRef);
      }
      await sendMessageWithGPT(formData);
    } catch (error) {
      console.error('Error sending message:', error);
      setIsTyping(false);
      onSend('Erro ao enviar mensagem.', 'ai');
    } finally {
      setIsLoading(false);
    }
  };

  const adjustTextareaHeight = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
  };

  return (
    <div className="bg-white border-t border-slate-100 px-6 py-4 w-full shrink-0">
      <div className="max-w-4xl mx-auto relative">
        {files.length > 0 && (
          <div className="flex gap-2 mb-2">
            {files.map((f, i) => (
              <div key={i} className="flex items-center gap-1.5 bg-slate-100 text-xs px-2 py-1 rounded-lg text-slate-600 border border-slate-200">
                <Paperclip size={12} />
                <span className="max-w-[120px] truncate">{f.name}</span>
                <button onClick={() => setFiles(prev => prev.filter((_, idx) => idx !== i))} className="hover:text-red-500"><X size={12} /></button>
              </div>
            ))}
          </div>
        )}
        <div className="relative flex items-end">
          <input
            type="file"
            ref={fileInputRef}
            className="hidden"
            onChange={handleFileChange}
            accept=".pdf,.txt,.jpg,.png"
          />
          <button
            type="button"
            onClick={handleFileUploadClick}
            className="absolute left-3 bottom-2.5 p-1.5 text-slate-400 hover:text-[#1e3a8a] transition-colors"
            title="Allega file"
          >
            <Paperclip size={18} />
          </button>
          
          <textarea
            ref={inputRef}
            value={input}
            onChange={adjustTextareaHeight}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey && (input.trim() || files.length > 0)) {
                e.preventDefault();
                handleSubmit();
              }
            }}
            placeholder="Scrivi la tua richiesta..."
            className="apple-input w-full pl-11 pr-14 resize-none overflow-y-auto"
            style={{ minHeight: '44px', maxHeight: '120px' }}
            rows={1}
          />
          
          <button
            onClick={handleSubmit}
            disabled={(!input.trim() && files.length === 0) || isLoading}
            className="absolute right-1.5 bottom-1.5 p-1.5 btn-primary rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
            title="Invia"
          >
            {isLoading ? (
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <Send size={18} />
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatInputArea;
