import React, { ChangeEvent, useEffect, useMemo, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
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
import {
  CheckComplianceChatDocumentReference,
  checkComplianceChatService,
} from '../services/checkComplianceChatService';
import {
  checkComplianceConversationService,
  CheckComplianceConversationSummary,
  CheckComplianceStoredMessage,
} from '../services/checkComplianceConversationService';

type LocalChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  isStreaming?: boolean;
  files?: {
    name: string;
    size: number;
  }[];
};

type SavedConversation = {
  id: string;
  title: string;
  updatedAt: string;
  sessionId: string | null;
};

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

const mapMessagesToStoredPayload = (items: LocalChatMessage[]): CheckComplianceStoredMessage[] =>
  items
    .filter((message) => message.id !== 'welcome')
    .map((message) => ({
      role: message.role,
      content: message.content,
      ...(message.files && message.files.length > 0 ? { files: message.files } : {}),
    }));

const mapSessionSummary = (session: CheckComplianceConversationSummary): SavedConversation => ({
  id: session.id,
  title: session.title,
  updatedAt: session.updated_at,
  sessionId: session.vera_session_id,
});

const TypingIndicator: React.FC = () => (
  <div className="flex items-center gap-2 text-[15px] leading-7 text-slate-500">
    <span>Scrivendo</span>
    <span className="flex items-center gap-1 pt-1">
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.2s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.1s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400" />
    </span>
  </div>
);

const MarkdownMessage: React.FC<{ content: string; isUser: boolean; isStreaming?: boolean }> = ({
  content,
  isUser,
  isStreaming,
}) => {
  if (!content) {
    return <TypingIndicator />;
  }

  const linkClassName = isUser
    ? 'font-semibold text-white underline decoration-white/50 underline-offset-2'
    : 'font-semibold text-[#1F3A8B] underline decoration-[#1F3A8B]/30 underline-offset-2';
  const codeClassName = isUser
    ? 'rounded bg-white/15 px-1.5 py-0.5 font-mono text-[13px] text-white'
    : 'rounded bg-slate-200 px-1.5 py-0.5 font-mono text-[13px] text-slate-900';

  return (
    <div className="max-w-none text-[15px] leading-7">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children }) => <p className="my-2 first:mt-0 last:mb-0">{children}</p>,
          strong: ({ children }) => <strong className="font-bold">{children}</strong>,
          em: ({ children }) => <em className="italic">{children}</em>,
          ul: ({ children }) => <ul className="my-2 list-disc space-y-1 pl-5">{children}</ul>,
          ol: ({ children }) => <ol className="my-2 list-decimal space-y-1 pl-5">{children}</ol>,
          li: ({ children }) => <li className="pl-1">{children}</li>,
          a: ({ children, href }) => (
            <a
              href={href}
              target="_blank"
              rel="noreferrer"
              className={linkClassName}
            >
              {children}
            </a>
          ),
          code: ({ children }) => <code className={codeClassName}>{children}</code>,
          pre: ({ children }) => (
            <pre
              className={`my-3 overflow-x-auto rounded-lg p-3 text-sm ${
                isUser
                  ? 'bg-white/15 text-white'
                  : 'border border-slate-200 bg-white text-slate-900'
              }`}
            >
              {children}
            </pre>
          ),
          blockquote: ({ children }) => (
            <blockquote
              className={`my-3 border-l-4 pl-3 ${
                isUser ? 'border-white/40 text-blue-50' : 'border-slate-300 text-slate-700'
              }`}
            >
              {children}
            </blockquote>
          ),
          table: ({ children }) => (
            <div className="my-3 overflow-x-auto">
              <table
                className={`min-w-full border-collapse text-left text-sm ${
                  isUser ? 'border-white/20' : 'border-slate-200'
                }`}
              >
                {children}
              </table>
            </div>
          ),
          th: ({ children }) => (
            <th
              className={`border px-3 py-2 font-bold ${
                isUser ? 'border-white/20 bg-white/10' : 'border-slate-200 bg-slate-100'
              }`}
            >
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className={`border px-3 py-2 ${isUser ? 'border-white/20' : 'border-slate-200'}`}>
              {children}
            </td>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
      {isStreaming && (
        <div className="mt-3">
          <TypingIndicator />
        </div>
      )}
    </div>
  );
};

const CheckComplianceChat: React.FC = () => {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const [messages, setMessages] = useState<LocalChatMessage[]>(initialMessages);
  const [question, setQuestion] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [savedConversations, setSavedConversations] = useState<SavedConversation[]>([]);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [sessionId, setSessionId] = useState<string>(() => crypto.randomUUID());
  const [storedSessionId, setStoredSessionId] = useState<string | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [saveLoading, setSaveLoading] = useState(false);
  const [conversationToDelete, setConversationToDelete] = useState<SavedConversation | null>(null);

  const canSend = useMemo(() => {
    return question.trim().length > 0 || selectedFiles.length > 0;
  }, [question, selectedFiles]);

  const hasStartedConversation = messages.length > 1;

  const loadSavedConversations = async () => {
    setHistoryLoading(true);
    try {
      const sessions = await checkComplianceConversationService.listConversations();
      setSavedConversations(sessions.map(mapSessionSummary));
    } catch (error) {
      console.error('Errore nel caricamento delle conversazioni Check Compliance:', error);
      setSavedConversations([]);
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    void loadSavedConversations();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages]);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    textarea.style.height = '44px';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px`;
  }, [question]);

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
    setSessionId(crypto.randomUUID());
    setStoredSessionId(null);
  };

  const handleSaveConversation = async () => {
    if (!hasStartedConversation) return;

    const firstUserMessage = messages.find((message) => message.role === 'user');
    const title = firstUserMessage?.content.slice(0, 72) || 'Analisi compliance';
    setSaveLoading(true);
    try {
      const savedSession = await checkComplianceConversationService.saveConversation({
        title,
        vera_session_id: sessionId,
        conversation_id: storedSessionId ?? undefined,
        messages: mapMessagesToStoredPayload(messages),
      });

      setStoredSessionId(savedSession.id);
      await loadSavedConversations();
      setIsHistoryOpen(true);
    } catch (error) {
      console.error('Errore nel salvataggio della conversazione Check Compliance:', error);
    } finally {
      setSaveLoading(false);
    }
  };

  const handleLoadConversation = async (conversation: SavedConversation) => {
    try {
      const session = await checkComplianceConversationService.getConversation(conversation.id);
      const restoredMessages: LocalChatMessage[] = session.messages
        .filter((message) => message.role === 'user' || message.role === 'assistant')
        .map((message) => ({
          id: crypto.randomUUID(),
          role: message.role as 'user' | 'assistant',
          content: message.content,
          files: message.files,
        }));

      setMessages(restoredMessages.length > 0 ? [initialMessages[0], ...restoredMessages] : initialMessages);
      setSessionId(session.vera_session_id || conversation.sessionId || crypto.randomUUID());
      setStoredSessionId(session.id);
      setQuestion('');
      setSelectedFiles([]);
      setIsHistoryOpen(false);
    } catch (error) {
      console.error('Errore nel caricamento della conversazione Check Compliance:', error);
    }
  };

  const handleDeleteConversation = async (conversation: SavedConversation) => {
    try {
      await checkComplianceConversationService.deleteConversation(conversation.id);
      setSavedConversations((current) =>
        current.filter((item) => item.id !== conversation.id)
      );
      if (storedSessionId === conversation.id) {
        handleNewAnalysis();
      }
    } catch (error) {
      console.error('Errore durante eliminazione della conversazione Check Compliance:', error);
    }
  };

  const handleConfirmDeleteConversation = async () => {
    if (!conversationToDelete) return;
    await handleDeleteConversation(conversationToDelete);
    setConversationToDelete(null);
  };

  const updateStoredConversation = async (nextMessages: LocalChatMessage[]) => {
    if (!storedSessionId) return;

    const firstUserMessage = nextMessages.find((message) => message.role === 'user');
    const title = firstUserMessage?.content.slice(0, 72) || 'Analisi compliance';
    try {
      await checkComplianceConversationService.saveConversation({
        title,
        vera_session_id: sessionId,
        conversation_id: storedSessionId,
        messages: mapMessagesToStoredPayload(nextMessages),
      });
      await loadSavedConversations();
    } catch (error) {
      console.error('Errore nell aggiornamento automatico della conversazione:', error);
    }
  };

  const handleSubmit = async () => {
    if (!canSend || isSubmitting) return;

    const previousMessages = messages;
    const filesSnapshot = selectedFiles.map((file) => ({
      name: file.name,
      size: file.size,
    }));
    const userQuestion = question.trim() || 'Analizza i documenti allegati.';

    const userMessage: LocalChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: userQuestion,
      files: filesSnapshot,
    };

    const assistantMessageId = crypto.randomUUID();
    const filesToUpload = [...selectedFiles];

    setMessages((current) => [
      ...current,
      userMessage,
      {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        isStreaming: true,
      },
    ]);
    setQuestion('');
    setSelectedFiles([]);
    setIsSubmitting(true);

    try {
      let documentReferences: CheckComplianceChatDocumentReference[] = [];
      if (filesToUpload.length > 0) {
        const uploadResponse = await checkComplianceChatService.uploadAttachments(
          filesToUpload,
          sessionId
        );
        documentReferences = uploadResponse.documents;
      }

      const response = await checkComplianceChatService.streamMessage(
        userQuestion,
        sessionId,
        documentReferences,
        (delta) => {
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantMessageId
                ? { ...message, content: `${message.content}${delta}`, isStreaming: true }
                : message
            )
          );
        },
        () => {
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantMessageId
                ? { ...message, isStreaming: true }
                : message
            )
          );
        }
      );
      if (!response.answer) {
        const fallbackAssistantMessage: LocalChatMessage = {
          id: assistantMessageId,
          role: 'assistant',
          content: 'Nessuna risposta ricevuta.',
          isStreaming: false,
        };
        setMessages((current) =>
          current.map((message) =>
            message.id === assistantMessageId
              ? fallbackAssistantMessage
              : message
          )
        );
        await updateStoredConversation([...previousMessages, userMessage, fallbackAssistantMessage]);
      } else {
        await updateStoredConversation([
          ...previousMessages,
          userMessage,
          {
            id: assistantMessageId,
            role: 'assistant',
            content: response.answer,
            isStreaming: false,
          },
        ]);
        setMessages((current) =>
          current.map((message) =>
            message.id === assistantMessageId
              ? { ...message, content: response.answer, isStreaming: false }
              : message
          )
        );
      }
    } catch (error) {
      const detail =
        error instanceof Error
          ? error.message
          : 'Non e stato possibile completare la richiesta. Riprova tra poco.';
      const errorAssistantMessage: LocalChatMessage = {
        id: assistantMessageId,
        role: 'assistant',
        content: detail,
        isStreaming: false,
      };
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantMessageId ? errorAssistantMessage : message
        )
      );
      await updateStoredConversation([...previousMessages, userMessage, errorAssistantMessage]);
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
              onClick={() => {
                setIsHistoryOpen(true);
                void loadSavedConversations();
              }}
              className="inline-flex w-fit items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-[#172554] shadow-sm transition-colors hover:bg-slate-50"
            >
              <History className="h-4 w-4" />
              Conversazioni
            </button>
            <button
              type="button"
              onClick={handleSaveConversation}
              disabled={!hasStartedConversation || saveLoading}
              className="inline-flex w-fit items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-[#172554] shadow-sm transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:text-slate-400"
            >
              <Save className="h-4 w-4" />
              {saveLoading ? 'Salvataggio...' : 'Salva'}
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
                {historyLoading ? (
                  <div className="rounded-lg border border-dashed border-slate-200 px-4 py-5 text-center text-sm text-slate-500">
                    Caricamento conversazioni...
                  </div>
                ) : savedConversations.length === 0 ? (
                  <div className="rounded-lg border border-dashed border-slate-200 px-4 py-5 text-center text-sm text-slate-500">
                    Nessuna conversazione salvata.
                  </div>
                ) : (
                  savedConversations.map((conversation) => (
                    <div
                      key={conversation.id}
                      className="flex items-start gap-2 rounded-lg border border-slate-200 px-3 py-3 transition-colors hover:border-[#1F3A8B] hover:bg-slate-50"
                    >
                      <button
                        type="button"
                        onClick={() => handleLoadConversation(conversation)}
                        className="min-w-0 flex-1 text-left"
                      >
                        <div className="truncate text-sm font-semibold text-slate-800">
                          {conversation.title}
                        </div>
                        <div className="mt-1 text-xs text-slate-400">
                          {new Date(conversation.updatedAt).toLocaleString('it-IT')}
                        </div>
                      </button>
                      <button
                        type="button"
                        onClick={() => setConversationToDelete(conversation)}
                        className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-slate-400 transition-colors hover:bg-red-50 hover:text-red-600"
                        title="Elimina conversazione"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
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
                    <MarkdownMessage
                      content={message.content}
                      isUser={isUser}
                      isStreaming={message.isStreaming}
                    />

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
            <div ref={messagesEndRef} />
          </div>

          <div
            className={`bg-white p-4 ${
              messages.length === 1 ? '' : 'border-t border-slate-200'
            }`}
          >
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
                disabled={isSubmitting}
                className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-300"
                title="Allega documenti"
              >
                <Paperclip className="h-5 w-5" />
              </button>

              <textarea
                ref={textareaRef}
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="Scrivi la richiesta di analisi compliance..."
                rows={1}
                className="max-h-40 min-h-11 flex-1 resize-none overflow-y-auto rounded-lg border border-slate-200 px-4 py-3 text-[15px] leading-6 text-slate-800 outline-none transition-colors focus:border-[#1F3A8B]"
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

      {conversationToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 px-4">
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
            <div className="mb-5">
              <h2 className="text-lg font-bold text-slate-900">Eliminare conversazione?</h2>
              <p className="mt-2 text-sm leading-6 text-slate-500">
                La conversazione salvata verra eliminata definitivamente dalla lista.
              </p>
              <p className="mt-3 truncate rounded-lg bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-700">
                {conversationToDelete.title}
              </p>
            </div>

            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setConversationToDelete(null)}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 transition-colors hover:bg-slate-50"
              >
                Annulla
              </button>
              <button
                type="button"
                onClick={handleConfirmDeleteConversation}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-red-700"
              >
                Elimina
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CheckComplianceChat;
