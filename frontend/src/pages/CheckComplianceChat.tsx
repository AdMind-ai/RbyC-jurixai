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
  responseBlocks?: string[];
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

const STREAM_RESPONSE_BLOCK_GAP_MS = 8000;

const initialMessages: LocalChatMessage[] = [
  {
    id: 'welcome',
    role: 'assistant',
    content:
      "Carica uno o più documenti e descrivi l'analisi di compliance che vuoi effettuare.",
  },
];

const mapMessagesToStoredPayload = (items: LocalChatMessage[]): CheckComplianceStoredMessage[] =>
  items
    .filter((message) => message.id !== 'welcome')
    .map((message) => ({
      role: message.role,
      content: message.content,
      ...(message.responseBlocks && message.responseBlocks.length > 0
        ? { response_blocks: message.responseBlocks }
        : {}),
      ...(message.files && message.files.length > 0 ? { files: message.files } : {}),
    }));

const mapSessionSummary = (session: CheckComplianceConversationSummary): SavedConversation => ({
  id: session.id,
  title: session.title,
  updatedAt: session.updated_at,
  sessionId: session.vera_session_id,
});

const TypingIndicator: React.FC = () => (
  <div className="flex items-center gap-2 text-[15px] text-slate-500">
    <span className="flex items-center gap-1 pt-1">
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.2s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.1s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400" />
    </span>
  </div>
);

const reconcileResponseBlocks = (blocks: string[] | undefined, answer: string) => {
  if (!answer) return blocks;
  if (!blocks || blocks.length === 0) return [answer];

  const joinedBlocks = blocks.join('');
  if (joinedBlocks === answer) return blocks;
  if (answer.startsWith(joinedBlocks)) {
    const remainingAnswer = answer.slice(joinedBlocks.length);
    if (!remainingAnswer) return blocks;
    return [
      ...blocks.slice(0, -1),
      `${blocks[blocks.length - 1]}${remainingAnswer}`,
    ];
  }

  return [answer];
};

const MarkdownMessage: React.FC<{
  content: string;
  isUser: boolean;
  isStreaming?: boolean;
}> = ({
  content,
  isUser,
  isStreaming,
}) => {
  if (!content) {
    return <TypingIndicator />;
  }

  const linkClassName = isUser
    ? 'font-semibold text-white underline decoration-white/50 underline-offset-2 hover:decoration-white'
    : 'font-semibold text-[#1e3a8a] underline decoration-[#1e3a8a]/30 underline-offset-2 hover:decoration-[#1e3a8a]';
  const codeClassName = isUser
    ? 'rounded-md bg-white/15 px-1.5 py-0.5 font-mono text-[13px] text-white'
    : 'rounded-md bg-slate-100 px-1.5 py-0.5 font-mono text-[13px] text-slate-800';

  return (
    <div className="max-w-none text-[15px] leading-relaxed">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children }) => <p className="my-2 first:mt-0 last:mb-0">{children}</p>,
          strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
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
              className={`my-3 overflow-x-auto rounded-xl p-4 text-[13px] ${
                isUser
                  ? 'bg-white/10 text-white'
                  : 'border border-slate-100 bg-slate-50 text-slate-800'
              }`}
            >
              {children}
            </pre>
          ),
          blockquote: ({ children }) => (
            <blockquote
              className={`my-3 border-l-2 pl-4 italic ${
                isUser ? 'border-white/40 text-white/90' : 'border-slate-300 text-slate-600'
              }`}
            >
              {children}
            </blockquote>
          ),
          table: ({ children }) => (
            <div className="my-3 overflow-x-auto rounded-xl border border-slate-100">
              <table className="min-w-full border-collapse text-left text-[14px]">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-400">
              {children}
            </thead>
          ),
          th: ({ children }) => (
            <th className="border-b border-slate-100 px-4 py-3 font-medium text-slate-500">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border-b border-slate-100/60 px-4 py-3 group-hover:bg-slate-50/60">
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
  const lastAssistantDeltaAtRef = useRef<number | null>(null);
  const assistantResponseBlocksRef = useRef<string[]>([]);
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
          responseBlocks: message.response_blocks,
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
    lastAssistantDeltaAtRef.current = null;
    assistantResponseBlocksRef.current = [];

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
          const now = Date.now();
          const lastDeltaAt = lastAssistantDeltaAtRef.current;
          const shouldStartNewBlock =
            lastDeltaAt !== null && now - lastDeltaAt >= STREAM_RESPONSE_BLOCK_GAP_MS;
          lastAssistantDeltaAtRef.current = now;
          const currentBlocks = assistantResponseBlocksRef.current;
          const nextBlocks =
            currentBlocks.length === 0 || shouldStartNewBlock
              ? [...currentBlocks, delta]
              : [
                  ...currentBlocks.slice(0, -1),
                  `${currentBlocks[currentBlocks.length - 1]}${delta}`,
                ];
          assistantResponseBlocksRef.current = nextBlocks;

          setMessages((current) =>
            current.map((message) =>
              {
                if (message.id !== assistantMessageId) return message;

                return {
                  ...message,
                  content: `${message.content}${delta}`,
                  responseBlocks: nextBlocks,
                  isStreaming: true,
                };
              }
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
        const finalResponseBlocks = reconcileResponseBlocks(
          assistantResponseBlocksRef.current,
          response.answer
        );
        await updateStoredConversation([
          ...previousMessages,
          userMessage,
          {
            id: assistantMessageId,
            role: 'assistant',
            content: response.answer,
            responseBlocks: finalResponseBlocks,
            isStreaming: false,
          },
        ]);
        setMessages((current) =>
          current.map((message) =>
            message.id === assistantMessageId
              ? {
                  ...message,
                  content: response.answer,
                  responseBlocks: finalResponseBlocks,
                  isStreaming: false,
                }
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
    <div className="flex h-screen w-full overflow-hidden bg-[#f8fafc]">
      {/* Pannello storico */}
      {isHistoryOpen && (
        <div className="flex w-[280px] flex-col border-r border-slate-100 bg-white">
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-4">
            <h2 className="text-sm font-semibold text-slate-700">Storico chat</h2>
            <button
              type="button"
              onClick={() => setIsHistoryOpen(false)}
              className="rounded-md p-1.5 text-slate-400 hover:bg-slate-50 hover:text-slate-700 transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto">
            {historyLoading ? (
              <div className="px-4 py-5 text-center text-sm text-slate-500">
                Caricamento...
              </div>
            ) : savedConversations.length === 0 ? (
              <div className="px-4 py-5 text-center text-sm text-slate-500">
                Nessuna conversazione
              </div>
            ) : (
              savedConversations.map((conversation) => (
                <div
                  key={conversation.id}
                  className="group flex cursor-pointer items-start justify-between border-b border-slate-50 px-4 py-3 hover:bg-slate-50 transition-colors"
                >
                  <button
                    type="button"
                    onClick={() => handleLoadConversation(conversation)}
                    className="min-w-0 flex-1 text-left"
                  >
                    <div className="truncate text-sm text-slate-700">
                      {conversation.title}
                    </div>
                    <div className="mt-0.5 text-[11px] text-slate-400">
                      {new Date(conversation.updatedAt).toLocaleString('it-IT', { dateStyle: 'short', timeStyle: 'short' })}
                    </div>
                  </button>
                  <button
                    type="button"
                    onClick={() => setConversationToDelete(conversation)}
                    className="ml-2 hidden rounded-md p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600 group-hover:block transition-colors"
                    title="Elimina"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Area Chat */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Header chat */}
        <header className="flex items-center justify-between border-b border-slate-100 bg-white px-6 py-4">
          <div className="flex items-center gap-3">
            {!isHistoryOpen && (
              <button
                type="button"
                onClick={() => {
                  setIsHistoryOpen(true);
                  void loadSavedConversations();
                }}
                className="btn-secondary !px-2.5 !py-2.5"
                title="Storico"
              >
                <History className="h-4 w-4" />
              </button>
            )}
            <h1 className="text-base font-semibold text-slate-800">Agente Vera</h1>
          </div>
          <div className="flex items-center gap-3">
            {hasStartedConversation && (
              <button
                type="button"
                onClick={handleSaveConversation}
                disabled={saveLoading}
                className="btn-secondary !py-2 !px-3 text-sm"
              >
                <Save className="mr-1.5 h-4 w-4" />
                {saveLoading ? 'Salvataggio...' : 'Salva'}
              </button>
            )}
            <button
              type="button"
              onClick={handleNewAnalysis}
              className="btn-primary !py-2 !px-3 text-sm"
            >
              <Plus className="mr-1.5 h-4 w-4" />
              Nuova
            </button>
          </div>
        </header>

        {/* Messaggi */}
        <div className="flex-1 overflow-y-auto bg-[#f8fafc] px-6 py-6 space-y-6">
          {messages.map((message) => {
            const isUser = message.role === 'user';
            const isWelcome = message.id === 'welcome';
            
            if (isWelcome) {
              return (
                <div key={message.id} className="flex justify-start">
                  <div className="flex max-w-[80%] items-start gap-3 rounded-2xl bg-blue-50 p-4">
                    <div className="flex shrink-0 items-center justify-center">
                      <Bot className="h-5 w-5 text-[#1e3a8a]" />
                    </div>
                    <div className="text-sm text-slate-600 pt-0.5 leading-relaxed">
                      {message.content}
                    </div>
                  </div>
                </div>
              );
            }

            const assistantBlocks = !isUser && message.responseBlocks && message.responseBlocks.length > 0
              ? message.responseBlocks
              : null;

            if (assistantBlocks) {
              return (
                <React.Fragment key={message.id}>
                  {assistantBlocks.map((block, blockIndex) => {
                    const isLastBlock = blockIndex === assistantBlocks.length - 1;
                    return (
                      <div key={`${message.id}-${blockIndex}`} className="flex justify-start">
                        <div className="flex max-w-[80%] items-end gap-2.5">
                          <div className="flex h-[28px] w-[28px] shrink-0 items-center justify-center rounded-full mb-1 text-white font-semibold text-[11px] tracking-wide" style={{ background: 'linear-gradient(135deg, #1e3a8a 0%, #1b9162 100%)' }}>
                            V
                          </div>
                          <div className="chat-bubble-ai px-5 py-3.5">
                            <MarkdownMessage
                              content={block}
                              isUser={false}
                              isStreaming={message.isStreaming && isLastBlock}
                            />
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </React.Fragment>
              );
            }

            return (
              <div key={message.id} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
                {isUser ? (
                  <div className="flex max-w-[70%] flex-col items-end gap-1.5">
                    <div className="chat-bubble-user px-5 py-3.5">
                      <MarkdownMessage
                        content={message.content}
                        isUser={true}
                        isStreaming={message.isStreaming}
                      />
                      {message.files && message.files.length > 0 && (
                        <div className="mt-3 flex flex-wrap justify-end gap-1.5">
                          {message.files.map((file) => (
                            <div
                              key={`${message.id}-${file.name}-${file.size}`}
                              className="flex items-center gap-1.5 rounded-lg bg-white/15 px-2 py-1 text-xs font-medium text-white/80"
                            >
                              <FileText className="h-3 w-3" />
                              <span className="max-w-[120px] truncate">{file.name}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="flex max-w-[80%] items-end gap-2.5">
                    <div className="flex h-[28px] w-[28px] shrink-0 items-center justify-center rounded-full mb-1 text-white font-semibold text-[11px] tracking-wide" style={{ background: 'linear-gradient(135deg, #1e3a8a 0%, #1b9162 100%)' }}>
                      V
                    </div>
                    <div className="chat-bubble-ai px-5 py-3.5">
                      <MarkdownMessage
                        content={message.content}
                        isUser={false}
                        isStreaming={message.isStreaming}
                      />
                    </div>
                  </div>
                )}
              </div>
            );
          })}
          <div ref={messagesEndRef} />
        </div>

        {/* Input bar */}
        <div className="border-t border-slate-100 bg-white px-6 py-4">
          {selectedFiles.length > 0 && (
            <div className="mb-3 flex max-h-24 flex-wrap gap-2 overflow-y-auto">
              {selectedFiles.map((file, index) => (
                <div
                  key={`${file.name}-${file.size}-${index}`}
                  className="badge-gray flex items-center gap-1.5 py-1.5 px-3"
                >
                  <FileText className="h-3.5 w-3.5 text-slate-400" />
                  <span className="max-w-[150px] truncate text-xs font-medium text-slate-600">{file.name}</span>
                  <button
                    type="button"
                    onClick={() => handleRemoveFile(index)}
                    className="ml-1 rounded-full p-0.5 hover:bg-slate-200/50 text-slate-400 transition-colors"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              ))}
            </div>
          )}

          <div className="relative flex items-end">
            <input
              ref={fileInputRef}
              type="file"
              multiple
              onChange={handleFileChange}
              className="hidden"
            />
            <textarea
              ref={textareaRef}
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Scrivi un messaggio..."
              rows={1}
              className="apple-input w-full resize-none py-3.5 pl-12 pr-[56px] text-[15px] leading-relaxed min-h-[50px] max-h-[140px]"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit();
                }
              }}
            />
            
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isSubmitting}
              className="absolute left-3.5 bottom-3.5 text-slate-400 hover:text-[#1e3a8a] transition-colors disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Paperclip className="h-5 w-5" />
            </button>

            <button
              type="button"
              onClick={handleSubmit}
              disabled={!canSend || isSubmitting}
              className="absolute right-2.5 bottom-2.5 flex h-[34px] w-[34px] items-center justify-center rounded-xl bg-[#1e3a8a] text-white disabled:bg-slate-100 disabled:text-slate-300 transition-colors"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Modal Eliminazione */}
      {conversationToDelete && (
        <div className="modal-overlay">
          <div className="modal-box w-full max-w-md">
            <div className="mb-6">
              <h2 className="text-lg font-semibold text-slate-800">Eliminare conversazione?</h2>
              <p className="mt-2 text-sm text-slate-500">
                La conversazione verrà eliminata definitivamente dalla lista.
              </p>
              <div className="mt-4 rounded-xl bg-slate-50 px-4 py-3 text-sm font-medium text-slate-700 border border-slate-100">
                {conversationToDelete.title}
              </div>
            </div>

            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setConversationToDelete(null)}
                className="btn-secondary"
              >
                Annulla
              </button>
              <button
                type="button"
                onClick={handleConfirmDeleteConversation}
                className="btn-danger"
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
