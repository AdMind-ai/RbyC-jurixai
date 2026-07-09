import React, { ChangeEvent, useEffect, useMemo, useRef, useState } from 'react';
import {
  Bot,
  FileText,
  History,
  Paperclip,
  Plus,
  Save,
  Send,
  User,
  X,
} from 'lucide-react';

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

const formatFileSize = (bytes: number) => {
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / Math.pow(1024, index);
  return `${value.toFixed(value >= 10 || index === 0 ? 0 : 1)} ${units[index]}`;
};

const initialMessages: LocalChatMessage[] = [
  {
    id: 'welcome',
    role: 'assistant',
    content:
      'Carica uno o piu documenti e descrivi l analisi di compliance che vuoi effettuare.',
  },
];

const suggestedPrompts = [
  'Analizza questo contratto rispetto alla normativa AML.',
  'Verifica eventuali criticita rispetto al GDPR.',
  'Controlla la conformita del documento per una SGR.',
];

const CheckComplianceChat: React.FC = () => {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [messages, setMessages] = useState<LocalChatMessage[]>(initialMessages);
  const [question, setQuestion] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [savedConversations, setSavedConversations] = useState<SavedConversation[]>([]);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);

  const canSend = useMemo(() => {
    return question.trim().length > 0 || selectedFiles.length > 0;
  }, [question, selectedFiles]);

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

  const persistSavedConversations = (items: SavedConversation[]) => {
    setSavedConversations(items);
    localStorage.setItem(SAVED_CONVERSATIONS_KEY, JSON.stringify(items));
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    setSelectedFiles((current) => [...current, ...files]);
    event.target.value = '';
  };

  const handleRemoveFile = (indexToRemove: number) => {
    setSelectedFiles((current) =>
      current.filter((_, index) => index !== indexToRemove)
    );
  };

  const handleNewAnalysis = () => {
    setMessages(initialMessages);
    setQuestion('');
    setSelectedFiles([]);
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
    setSelectedFiles([]);
    setIsHistoryOpen(false);
  };

  const handleSubmit = () => {
    if (!canSend || isSubmitting) return;

    const filesSnapshot = selectedFiles.map((file) => ({
      name: file.name,
      size: file.size,
    }));

    const userMessage: LocalChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: question.trim() || 'Analisi compliance sui documenti allegati.',
      files: filesSnapshot,
    };

    setMessages((current) => [
      ...current,
      userMessage,
      {
        id: crypto.randomUUID(),
        role: 'assistant',
        content:
          'Richiesta ricevuta. L analisi verra elaborata dal servizio Check Compliance.',
      },
    ]);
    setQuestion('');
    setSelectedFiles([]);
    setIsSubmitting(false);
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
                        : 'border border-slate-200 bg-slate-50 text-slate-700'
                    }`}
                  >
                    <p className="whitespace-pre-wrap text-sm leading-6">{message.content}</p>

                    {message.files && message.files.length > 0 && (
                      <div className="mt-3 space-y-2">
                        {message.files.map((file) => (
                          <div
                            key={`${message.id}-${file.name}-${file.size}`}
                            className={`flex items-center gap-2 rounded-lg px-3 py-2 text-xs ${
                              isUser
                                ? 'bg-white/10 text-blue-50'
                                : 'border border-slate-200 bg-white text-slate-600'
                            }`}
                          >
                            <FileText className="h-4 w-4 shrink-0" />
                            <span className="min-w-0 flex-1 truncate">{file.name}</span>
                            <span className="shrink-0 opacity-80">{formatFileSize(file.size)}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {isUser && (
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-600">
                      <User className="h-5 w-5" />
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <div
            className={`bg-white p-4 ${
              messages.length === 1 ? '' : 'border-t border-slate-200'
            }`}
          >
            {messages.length === 1 && (
              <div className="mx-auto mb-10 flex max-w-4xl flex-wrap justify-center gap-4">
                {suggestedPrompts.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => setQuestion(prompt)}
                    className="rounded-full border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-medium text-slate-600 transition-colors hover:border-[#1F3A8B] hover:bg-white hover:text-[#1F3A8B]"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            )}

            {selectedFiles.length > 0 && (
              <div className="mb-3 flex max-h-28 flex-wrap gap-2 overflow-y-auto">
                {selectedFiles.map((file, index) => (
                  <div
                    key={`${file.name}-${file.size}-${index}`}
                    className="inline-flex max-w-full items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-medium text-slate-600"
                  >
                    <FileText className="h-4 w-4 shrink-0 text-[#1F3A8B]" />
                    <span className="truncate">{file.name}</span>
                    <span className="shrink-0 text-slate-400">{formatFileSize(file.size)}</span>
                    <button
                      type="button"
                      onClick={() => handleRemoveFile(index)}
                      className="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-slate-400 hover:bg-red-50 hover:text-red-600"
                      title="Rimuovi file"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div className="flex items-end gap-3">
              <input
                ref={fileInputRef}
                type="file"
                multiple
                onChange={handleFileChange}
                className="hidden"
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 transition-colors hover:bg-slate-50"
                title="Allega documenti"
              >
                <Paperclip className="h-5 w-5" />
              </button>

              <textarea
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="Scrivi la richiesta di analisi compliance..."
                rows={1}
                className="max-h-32 min-h-11 flex-1 resize-none rounded-lg border border-slate-200 px-4 py-3 text-sm text-slate-700 outline-none transition-colors focus:border-[#1F3A8B]"
              />

              <button
                type="button"
                onClick={handleSubmit}
                disabled={!canSend || isSubmitting}
                className="inline-flex h-11 shrink-0 items-center justify-center gap-2 rounded-lg bg-[#1F3A8B] px-5 text-sm font-semibold text-white transition-colors hover:bg-[#172554] disabled:bg-slate-300"
              >
                <Send className="h-4 w-4" />
                Invia
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};

export default CheckComplianceChat;
