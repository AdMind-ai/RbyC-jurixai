import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Bot,
  History,
  Paperclip,
  Plus,
  Save,
  Send,
  User,
  X,
} from 'lucide-react';
import { checkComplianceChatService } from '../services/checkComplianceChatService';

type LocalChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  files?: {
    name: string;
    size: number;
  }[];
};

type SavedConversation = {
  id: string;
  title: string;
  createdAt: string;
  messages: LocalChatMessage[];
};

const SAVED_CONVERSATIONS_KEY = 'check-compliance-saved-conversations';

const initialMessages: LocalChatMessage[] = [
  {
    id: 'welcome',
    role: 'assistant',
    content:
      'Carica uno o piu documenti e descrivi l analisi di compliance che vuoi effettuare.',
  },
];

const CheckComplianceChat: React.FC = () => {
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const [messages, setMessages] = useState<LocalChatMessage[]>(initialMessages);
  const [question, setQuestion] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [savedConversations, setSavedConversations] = useState<SavedConversation[]>([]);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);

  const canSend = useMemo(() => {
    return question.trim().length > 0;
  }, [question]);

  const hasStartedConversation = messages.length > 1;

  useEffect(() => {
    const stored = localStorage.getItem(SAVED_CONVERSATIONS_KEY);
    if (!stored) return;

    try {
      const parsed = JSON.parse(stored) as SavedConversation[];
      if (Array.isArray(parsed)) {
        setSavedConversations(parsed);
      }
    } catch {
      setSavedConversations([]);
    }
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages]);

  const persistSavedConversations = (items: SavedConversation[]) => {
    setSavedConversations(items);
    localStorage.setItem(SAVED_CONVERSATIONS_KEY, JSON.stringify(items));
  };

  const handleNewAnalysis = () => {
    setMessages(initialMessages);
    setQuestion('');
  };

  const handleSaveConversation = () => {
    if (!hasStartedConversation) return;

    const firstUserMessage = messages.find((message) => message.role === 'user');
    const title = firstUserMessage?.content.slice(0, 72) || 'Analisi compliance';
    const conversation: SavedConversation = {
      id: crypto.randomUUID(),
      title,
      createdAt: new Date().toISOString(),
      messages,
    };

    persistSavedConversations([conversation, ...savedConversations]);
    setIsHistoryOpen(true);
  };

  const handleLoadConversation = (conversation: SavedConversation) => {
    setMessages(conversation.messages);
    setQuestion('');
    setIsHistoryOpen(false);
  };

  const handleSubmit = async () => {
    if (!canSend || isSubmitting) return;

    const userMessage: LocalChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: question.trim(),
    };

    const userQuestion = userMessage.content;
    const assistantMessageId = crypto.randomUUID();

    setMessages((current) => [
      ...current,
      userMessage,
      {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
      },
    ]);
    setQuestion('');
    setIsSubmitting(true);

    try {
      const response = await checkComplianceChatService.streamMessage(
        userQuestion,
        (delta) => {
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantMessageId
                ? { ...message, content: `${message.content}${delta}` }
                : message
            )
          );
        }
      );
      if (!response.answer) {
        setMessages((current) =>
          current.map((message) =>
            message.id === assistantMessageId
              ? { ...message, content: 'Nessuna risposta ricevuta.' }
              : message
          )
        );
      }
    } catch (error) {
      const detail =
        error instanceof Error
          ? error.message
          : 'Non e stato possibile completare la richiesta. Riprova tra poco.';
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantMessageId ? { ...message, content: detail } : message
        )
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex h-full w-full flex-col overflow-hidden bg-slate-50">
      <div className="border-b border-slate-200 bg-white px-8 py-6 lg:px-12">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-[#172554]">Check Compliance</h1>
            <p className="mt-2 text-sm text-slate-500">
              Analisi documentale di compliance
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setIsHistoryOpen(true)}
              className="inline-flex w-fit items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-[#172554] shadow-sm transition-colors hover:bg-slate-50"
            >
              <History className="h-4 w-4" />
              Conversazioni
            </button>
            <button
              type="button"
              onClick={handleSaveConversation}
              disabled={!hasStartedConversation}
              className="inline-flex w-fit items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-[#172554] shadow-sm transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:text-slate-400"
            >
              <Save className="h-4 w-4" />
              Salva
            </button>
            <button
              type="button"
              onClick={handleNewAnalysis}
              className="inline-flex w-fit items-center justify-center gap-2 rounded-lg bg-[#1F3A8B] px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-[#172554]"
            >
              <Plus className="h-4 w-4" />
              Nuova analisi
            </button>
          </div>
        </div>
      </div>

      <div className="mx-auto flex min-h-0 w-full max-w-7xl flex-1 p-6 lg:p-8">
        <section className="relative flex min-h-0 w-full flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
          {isHistoryOpen && (
            <div className="absolute right-4 top-4 z-10 w-[360px] max-w-[calc(100%-2rem)] rounded-lg border border-slate-200 bg-white p-4 shadow-xl">
              <div className="mb-3 flex items-center justify-between gap-3">
                <div>
                  <h2 className="text-sm font-bold text-[#172554]">Conversazioni salvate</h2>
                  <p className="mt-1 text-xs text-slate-500">
                    Seleziona una conversazione per riaprirla.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setIsHistoryOpen(false)}
                  className="inline-flex h-8 w-8 items-center justify-center rounded-md text-slate-400 hover:bg-slate-50 hover:text-slate-700"
                  title="Chiudi"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="max-h-80 space-y-2 overflow-y-auto">
                {savedConversations.length === 0 ? (
                  <div className="rounded-lg border border-dashed border-slate-200 px-4 py-5 text-center text-sm text-slate-500">
                    Nessuna conversazione salvata.
                  </div>
                ) : (
                  savedConversations.map((conversation) => (
                    <button
                      key={conversation.id}
                      type="button"
                      onClick={() => handleLoadConversation(conversation)}
                      className="w-full rounded-lg border border-slate-200 px-3 py-3 text-left transition-colors hover:border-[#1F3A8B] hover:bg-slate-50"
                    >
                      <div className="truncate text-sm font-semibold text-slate-800">
                        {conversation.title}
                      </div>
                      <div className="mt-1 text-xs text-slate-400">
                        {new Date(conversation.createdAt).toLocaleString('it-IT')}
                      </div>
                    </button>
                  ))
                )}
              </div>
            </div>
          )}

          <div
            className="flex-1 space-y-5 overflow-y-auto p-5"
          >
            {messages.map((message) => {
              const isUser = message.role === 'user';
              return (
                <div
                  key={message.id}
                  className={`flex gap-3 ${
                    messages.length === 1
                      ? 'justify-start'
                      : isUser
                        ? 'justify-end'
                        : 'justify-start'
                  }`}
                >
                  {!isUser && (
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[#1F3A8B]/10 text-[#1F3A8B]">
                      <Bot className="h-5 w-5" />
                    </div>
                  )}

                  <div
                    className={`rounded-lg px-4 py-3 ${
                      messages.length === 1 ? 'max-w-2xl text-left' : 'max-w-[78%]'
                    } ${
                      isUser
                        ? 'bg-[#1F3A8B] text-white'
                        : 'border border-slate-200 bg-slate-50 text-slate-800'
                    }`}
                  >
                    <p className="whitespace-pre-wrap text-[15px] leading-7">
                      {message.content || 'Scrivendo...'}
                    </p>
                  </div>

                  {isUser && (
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-600">
                      <User className="h-5 w-5" />
                    </div>
                  )}
                </div>
              );
            })}
            <div ref={messagesEndRef} />
          </div>

          <div
            className={`bg-white p-4 ${
              messages.length === 1 ? '' : 'border-t border-slate-200'
            }`}
          >
            <div className="flex items-end gap-3">
              <button
                type="button"
                disabled
                className="inline-flex h-11 w-11 shrink-0 cursor-not-allowed items-center justify-center rounded-lg border border-slate-200 bg-slate-50 text-slate-300"
                title="Allegati disponibili nella prossima fase"
              >
                <Paperclip className="h-5 w-5" />
              </button>

              <textarea
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="Scrivi la richiesta di analisi compliance..."
                rows={1}
                className="max-h-32 min-h-11 flex-1 resize-none rounded-lg border border-slate-200 px-4 py-3 text-[15px] leading-6 text-slate-800 outline-none transition-colors focus:border-[#1F3A8B]"
              />

              <button
                type="button"
                onClick={handleSubmit}
                disabled={!canSend || isSubmitting}
                className="inline-flex h-11 shrink-0 items-center justify-center gap-2 rounded-lg bg-[#1F3A8B] px-5 text-sm font-semibold text-white transition-colors hover:bg-[#172554] disabled:bg-slate-300"
              >
                <Send className="h-4 w-4" />
                {isSubmitting ? 'Invio...' : 'Invia'}
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};

export default CheckComplianceChat;
