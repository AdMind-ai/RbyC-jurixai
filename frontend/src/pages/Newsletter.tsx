import React, { useCallback, useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Archive,
  Check,
  Copy,
  Download,
  FileText,
  Newspaper,
  Paperclip,
  Plus,
  Send,
  Sparkles,
  Trash2,
  User,
  X,
} from 'lucide-react';
import { newsletterChatService } from '../services/newsletterChatService';
import { savedNewsletterService, SavedNewsletterSummary, SavedNewsletter } from '../services/savedNewsletterService';
import { useLocation, useNavigate } from 'react-router-dom';

// ─── Types ────────────────────────────────────────────────────────────────────

type Role = 'user' | 'assistant';

type ChatMessage = {
  id: string;
  role: Role;
  content: string;
  isStreaming?: boolean;
  liveStatus?: string;
  files?: { name: string; size: number }[];
};

type DraftType = 'newsletter' | 'pill';
type TabKey = 'new' | 'archive';

// ─── Helpers ──────────────────────────────────────────────────────────────────

const uid = () => Math.random().toString(36).slice(2);

const formatFileSize = (bytes: number) => {
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
};

const stripBozzaTag = (text: string) =>
  text
    .replace(/<bozza>[\s\S]*?<\/bozza>/gi, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();

const extractBozza = (text: string): string | null => {
  const match = text.match(/<bozza>([\s\S]*?)<\/bozza>/i);
  return match ? match[1].trim() : null;
};

const formatDate = (iso: string) => {
  return new Date(iso).toLocaleDateString('it-IT', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
};

const WELCOME: ChatMessage = {
  id: 'welcome',
  role: 'assistant',
  content:
    'Ciao! Sono Agente Vera. Descrivimi l\'aggiornamento normativo o l\'argomento su cui vuoi generare la newsletter o il PILL formativo, e creerò una bozza pronta da rivedere.',
};

// ─── Sub-components ───────────────────────────────────────────────────────────

const TypingDots: React.FC<{ message?: string }> = ({ message }) => (
  <span className="inline-flex items-center gap-2 pt-1 text-slate-500">
    {message && <span className="text-xs">{message}</span>}
    <span className="inline-flex items-center gap-1">
      {[0, 100, 200].map((d) => (
        <span
          key={d}
          className="block h-1.5 w-1.5 rounded-full bg-slate-400 animate-bounce"
          style={{ animationDelay: `${d}ms` }}
        />
      ))}
    </span>
  </span>
);

const MarkdownContent: React.FC<{ content: string; isUser: boolean }> = ({ content, isUser }) => (
  <ReactMarkdown
    remarkPlugins={[remarkGfm]}
    components={{
      p: ({ children }) => <p className="my-1.5 first:mt-0 last:mb-0">{children}</p>,
      strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
      ul: ({ children }) => <ul className="my-2 list-disc pl-5 space-y-1">{children}</ul>,
      ol: ({ children }) => <ol className="my-2 list-decimal pl-5 space-y-1">{children}</ol>,
      li: ({ children }) => <li className="pl-0.5">{children}</li>,
      h1: ({ children }) => <h1 className="text-lg font-bold mt-3 mb-1">{children}</h1>,
      h2: ({ children }) => <h2 className="text-base font-semibold mt-2.5 mb-1">{children}</h2>,
      h3: ({ children }) => <h3 className="text-sm font-semibold mt-2 mb-0.5">{children}</h3>,
      code: ({ children }) => (
        <code className={`rounded px-1.5 py-0.5 font-mono text-[12px] ${isUser ? 'bg-white/15' : 'bg-slate-100'}`}>
          {children}
        </code>
      ),
      blockquote: ({ children }) => (
        <blockquote className={`my-2 border-l-4 pl-3 ${isUser ? 'border-white/40' : 'border-[#1b9162]/40 text-slate-600'}`}>
          {children}
        </blockquote>
      ),
    }}
  >
    {content}
  </ReactMarkdown>
);

const getDraftTypeLabel = (type: DraftType) => type === 'newsletter' ? 'Newsletter' : 'PILL Formativo';
const getDraftTypeObjectLabel = (type: DraftType) => type === 'newsletter' ? 'newsletter' : 'PILL';

const PreviewDocument: React.FC<{ content: string; type: DraftType }> = ({ content, type }) => (
  <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
    <div
      className="px-8 py-5 flex items-center justify-between"
      style={{ background: 'linear-gradient(135deg, #1e3a8a 0%, #1e3a8a 60%, #1b9162 100%)' }}
    >
      <div>
        <p className="text-white/60 text-[11px] uppercase tracking-widest font-medium mb-0.5">
          {getDraftTypeLabel(type)} — Bozza
        </p>
        <p className="text-white text-sm font-light tracking-wide">
          {new Date().toLocaleDateString('it-IT', { day: '2-digit', month: 'long', year: 'numeric' })}
        </p>
      </div>
      <img src="/logo-dark.svg" alt="Refink" style={{ height: 28, opacity: 0.9 }} />
    </div>
    <div className="px-8 py-6 text-slate-700 text-[14px] leading-7">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => <h1 className="text-2xl font-bold text-slate-800 mt-6 mb-3 first:mt-0">{children}</h1>,
          h2: ({ children }) => <h2 className="text-lg font-semibold text-slate-800 mt-5 mb-2 pb-1 border-b border-slate-100">{children}</h2>,
          h3: ({ children }) => <h3 className="text-base font-semibold text-slate-700 mt-4 mb-1.5">{children}</h3>,
          p: ({ children }) => <p className="my-2 first:mt-0">{children}</p>,
          strong: ({ children }) => <strong className="font-semibold text-slate-800">{children}</strong>,
          ul: ({ children }) => <ul className="my-2.5 space-y-1.5 pl-5 list-disc marker:text-[#1b9162]">{children}</ul>,
          ol: ({ children }) => <ol className="my-2.5 space-y-1.5 pl-5 list-decimal marker:text-[#1b9162] marker:font-semibold">{children}</ol>,
          li: ({ children }) => <li className="pl-1">{children}</li>,
          blockquote: ({ children }) => <blockquote className="my-3 border-l-4 border-[#1b9162] pl-4 text-slate-600 bg-green-50/50 py-2 rounded-r-lg">{children}</blockquote>,
          hr: () => <hr className="my-5 border-slate-100" />,
          code: ({ children }) => <code className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[12px]">{children}</code>,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
    <div className="px-8 py-4 border-t border-slate-100 flex items-center justify-between">
      <div className="flex items-center gap-1.5">
        <span className="block rounded-full" style={{ width: 5, height: 5, background: '#365142' }} />
        <span className="block rounded-full" style={{ width: 5, height: 5, background: '#1b9162' }} />
        <span className="block rounded-full" style={{ width: 5, height: 5, background: '#4ade80' }} />
      </div>
      <p className="text-[11px] text-slate-400">Generato da Agente Vera · Refink Suite</p>
    </div>
  </div>
);

// ─── Archive tab ──────────────────────────────────────────────────────────────

const ArchiveTab: React.FC<{
  onOpen: (n: SavedNewsletter) => void;
}> = ({ onOpen }) => {
  const [items, setItems] = useState<SavedNewsletterSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  useEffect(() => {
    savedNewsletterService.list().then(setItems).catch(console.error).finally(() => setLoading(false));
  }, []);

  const handleOpen = async (id: string) => {
    setSelectedId(id);
    try {
      const full = await savedNewsletterService.get(id);
      onOpen(full);
    } catch (e) {
      console.error(e);
    }
  };

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setDeleting(id);
    try {
      await savedNewsletterService.delete(id);
      setItems((prev) => prev.filter((x) => x.id !== id));
      if (selectedId === id) setSelectedId(null);
    } catch (e) {
      console.error(e);
    } finally {
      setDeleting(null);
    }
  };

  if (loading) return (
    <div className="flex items-center justify-center h-48 text-slate-400 text-sm">Caricamento…</div>
  );

  if (items.length === 0) return (
    <div className="flex flex-col items-center justify-center h-full gap-3 py-16 text-center px-4">
      <div className="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center">
        <Archive size={28} className="text-slate-300" />
      </div>
      <p className="text-slate-600 font-medium">Nessuna newsletter salvata</p>
      <p className="text-slate-400 text-[12px] max-w-[260px] leading-relaxed">
        Le newsletter generate verranno salvate automaticamente qui dopo ogni sessione.
      </p>
    </div>
  );

  return (
    <div className="flex flex-col gap-2 p-4">
      {items.map((item) => (
        <button
          key={item.id}
          onClick={() => handleOpen(item.id)}
          className={`w-full text-left rounded-xl border p-4 transition-all duration-150 group
            ${selectedId === item.id
              ? 'border-[#1e3a8a]/30 bg-blue-50/50 shadow-sm'
              : 'border-slate-100 bg-white hover:border-slate-200 hover:shadow-sm'}`}
        >
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <p className="text-[13px] font-medium text-slate-800 truncate leading-snug">
                {item.title}
              </p>
              <p className="text-[11px] text-slate-400 mt-0.5 line-clamp-2 leading-relaxed">
                {item.preview}
              </p>
              <div className="flex items-center gap-2 mt-2">
                <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full
                  ${item.newsletter_type === 'newsletter' ? 'bg-blue-50 text-blue-600' : 'bg-purple-50 text-purple-600'}`}>
                  {item.newsletter_type_display}
                </span>
                <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full
                  ${item.source === 'auto' ? 'bg-green-50 text-green-700' : 'bg-slate-100 text-slate-500'}`}>
                  {item.source_display}
                </span>
                <span className="text-[10px] text-slate-400">{formatDate(item.created_at)}</span>
              </div>
            </div>
            <button
              onClick={(e) => handleDelete(e, item.id)}
              disabled={deleting === item.id}
              className="shrink-0 p-1.5 rounded-lg text-slate-300 hover:text-red-400 hover:bg-red-50 transition-colors opacity-0 group-hover:opacity-100"
              title="Elimina"
            >
              <Trash2 size={13} />
            </button>
          </div>
        </button>
      ))}
    </div>
  );
};

// ─── Main page ────────────────────────────────────────────────────────────────

const Newsletter: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();

  const getInitialTab = (): TabKey => {
    const params = new URLSearchParams(location.search);
    return params.get('tab') === 'archive' ? 'archive' : 'new';
  };

  const [activeTab, setActiveTab] = useState<TabKey>(getInitialTab);
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState<{ name: string; size: number; data: string; type: string }[]>([]);
  const [draftType, setDraftType] = useState<DraftType>('newsletter');
  const [previewContent, setPreviewContent] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [sessionId, setSessionId] = useState<string>(() => crypto.randomUUID());
  const [savedId, setSavedId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 140)}px`;
  }, [input]);

  // Extract <bozza> and auto-save when streaming is done
  useEffect(() => {
    const aiMessages = messages.filter((m) => m.role === 'assistant' && m.id !== 'welcome');
    if (aiMessages.length === 0) return;
    const last = aiMessages[aiMessages.length - 1];
    if (!last.content || last.isStreaming) return;
    const bozza = extractBozza(last.content);
    if (bozza) {
      setPreviewContent(bozza);
      autoSave(bozza);
    }
  }, [messages]);

  const autoSave = useCallback(async (content: string) => {
    if (saving || savedId) return;
    setSaving(true);
    try {
      const saved = await savedNewsletterService.save({ content, newsletter_type: draftType });
      setSavedId(saved.id);
    } catch (e) {
      console.error('Auto-save failed', e);
    } finally {
      setSaving(false);
    }
  }, [saving, savedId, draftType]);

  const handleFileAttach = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    files.forEach((file) => {
      const reader = new FileReader();
      reader.onload = () => {
        const base64 = (reader.result as string).split(',')[1];
        setAttachedFiles((prev) => [...prev, { name: file.name, size: file.size, data: base64, type: file.type }]);
      };
      reader.readAsDataURL(file);
    });
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleSend = async () => {
    if (!input.trim() && attachedFiles.length === 0) return;
    if (isTyping) return;

    const userMsg: ChatMessage = {
      id: uid(),
      role: 'user',
      content: input.trim(),
      files: attachedFiles.map((f) => ({ name: f.name, size: f.size })),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setAttachedFiles([]);
    setIsTyping(true);

    const aiId = uid();
    setMessages((prev) => [...prev, { id: aiId, role: 'assistant', content: '', isStreaming: true }]);

    try {
      const data = await newsletterChatService.streamMessage(
        userMsg.content,
        draftType,
        sessionId,
        (delta) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === aiId ? { ...m, content: `${m.content}${delta}`, isStreaming: true, liveStatus: undefined } : m
            )
          );
        },
        (statusMessage) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === aiId && !m.content ? { ...m, liveStatus: statusMessage, isStreaming: true } : m
            )
          );
        }
      );

      const answer: string = data.answer ?? '';
      const returnedKey: string = data.sessionKey ?? '';

      setMessages((prev) =>
        prev.map((m) =>
          m.id === aiId
            ? { ...m, content: answer || m.content || 'Nessuna risposta ricevuta.', isStreaming: false, liveStatus: undefined }
            : m
        )
      );

      if (returnedKey) setSessionId(returnedKey);
    } catch (err) {
      console.error('Newsletter chat error:', err);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === aiId
            ? { ...m, content: 'Si è verificato un errore. Riprova.', isStreaming: false, liveStatus: undefined }
            : m
        )
      );
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const handleNewSession = () => {
    setMessages([WELCOME]);
    setSessionId(crypto.randomUUID());
    setPreviewContent(null);
    setInput('');
    setAttachedFiles([]);
    setSavedId(null);
  };

  const handleCopy = async () => {
    if (!previewContent) return;
    await navigator.clipboard.writeText(previewContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    if (!previewContent) return;
    const blob = new Blob([previewContent], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${draftType === 'newsletter' ? 'newsletter' : 'pill'}_bozza.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleOpenArchived = (newsletter: SavedNewsletter) => {
    setPreviewContent(newsletter.content);
    setActiveTab('new');
  };

  const switchTab = (tab: TabKey) => {
    setActiveTab(tab);
    navigate(`/newsletter${tab === 'archive' ? '?tab=archive' : ''}`, { replace: true });
  };

  return (
    <div className="flex h-full w-full overflow-hidden bg-[#f8fafc]">

      {/* ── LEFT: Chat / Archive ─────────────────────────────────────────── */}
      <div className="flex flex-col w-[420px] shrink-0 bg-white border-r border-slate-100 h-full">

        {/* Header */}
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between shrink-0">
          <div>
            <p className="text-[11px] text-slate-400 uppercase tracking-widest font-medium">Agente Vera</p>
            <h2 className="text-base font-semibold text-slate-800 leading-tight">Newsletter & PILL</h2>
          </div>
          {activeTab === 'new' && (
            <button onClick={handleNewSession} className="btn-secondary py-1.5 px-3 text-xs gap-1.5" title="Nuova sessione">
              <Plus size={13} />
              Nuova
            </button>
          )}
        </div>

        {/* Tabs */}
        <div className="px-5 py-3 border-b border-slate-100 shrink-0">
          <div className="flex bg-slate-100 rounded-xl p-1 gap-0.5">
            <button
              onClick={() => switchTab('new')}
              className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-[12px] font-medium transition-all duration-200
                ${activeTab === 'new' ? 'bg-white shadow-sm text-[#1e3a8a]' : 'text-slate-400 hover:text-slate-600'}`}
            >
              <Sparkles size={12} />
              Nova
            </button>
            <button
              onClick={() => switchTab('archive')}
              className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-[12px] font-medium transition-all duration-200
                ${activeTab === 'archive' ? 'bg-white shadow-sm text-[#1e3a8a]' : 'text-slate-400 hover:text-slate-600'}`}
            >
              <Archive size={12} />
              Archivio
            </button>
          </div>
        </div>

        {activeTab === 'archive' ? (
          <div className="flex-1 overflow-y-auto [scrollbar-width:thin]">
            <ArchiveTab onOpen={handleOpenArchived} />
          </div>
        ) : (
          <>
            {/* Draft type selector */}
            <div className="px-5 py-3 border-b border-slate-100 shrink-0">
              <div className="flex bg-slate-100 rounded-xl p-1 w-fit gap-0.5">
                <button
                  onClick={() => setDraftType('newsletter')}
                  className={`px-4 py-1.5 rounded-lg text-[12px] font-medium transition-all duration-200
                    ${draftType === 'newsletter' ? 'bg-white shadow-sm text-[#1e3a8a]' : 'text-slate-400 hover:text-slate-600'}`}
                >
                  Newsletter
                </button>
                <button
                  onClick={() => setDraftType('pill')}
                  className={`px-4 py-1.5 rounded-lg text-[12px] font-medium transition-all duration-200
                    ${draftType === 'pill' ? 'bg-white shadow-sm text-[#1e3a8a]' : 'text-slate-400 hover:text-slate-600'}`}
                >
                  PILL Formativo
                </button>
              </div>
            </div>

            {/* Auto-save indicator */}
            {(saving || savedId) && (
              <div className="px-5 py-1.5 border-b border-slate-100 shrink-0 flex items-center gap-1.5">
                {saving ? (
                  <>
                    <span className="block w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                    <span className="text-[11px] text-slate-400">Salvataggio in corso…</span>
                  </>
                ) : (
                  <>
                    <Check size={11} className="text-green-500" />
                    <span className="text-[11px] text-slate-400">Salvata nell'Archivio</span>
                  </>
                )}
              </div>
            )}

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-4 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
              {messages.map((msg) => (
                <div key={msg.id} className={`flex gap-2.5 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                  {msg.role === 'user' ? (
                    <div className="shrink-0 w-7 h-7 rounded-full bg-slate-200 flex items-center justify-center">
                      <User size={13} className="text-slate-500" />
                    </div>
                  ) : (
                    <div
                      className="shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-white font-semibold text-[11px] tracking-wide"
                      style={{ background: 'linear-gradient(135deg, #1e3a8a 0%, #1b9162 100%)' }}
                    >
                      V
                    </div>
                  )}
                  <div className={`flex flex-col gap-1 max-w-[82%] ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                    {msg.files && msg.files.length > 0 && (
                      <div className={`flex flex-wrap gap-1 ${msg.role === 'user' ? 'justify-end' : ''}`}>
                        {msg.files.map((f, i) => (
                          <span key={i} className="flex items-center gap-1.5 bg-white border border-slate-200 rounded-lg px-2 py-1 text-[11px] text-slate-500">
                            <FileText size={10} />
                            {f.name}
                            <span className="text-slate-400">({formatFileSize(f.size)})</span>
                          </span>
                        ))}
                      </div>
                    )}
                    <div className={msg.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-ai'}>
                      {msg.id === 'welcome' ? (
                        <p className="text-sm leading-relaxed">{msg.content}</p>
                      ) : msg.content ? (
                        <div className="text-sm leading-relaxed">
                          <MarkdownContent
                            content={msg.role === 'assistant' ? stripBozzaTag(msg.content) : msg.content}
                            isUser={msg.role === 'user'}
                          />
                        </div>
                      ) : msg.isStreaming ? (
                        <TypingDots message={msg.liveStatus} />
                      ) : null}
                      {msg.isStreaming && msg.content && (
                        <div className="mt-2"><TypingDots /></div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>

            {/* File chips */}
            {attachedFiles.length > 0 && (
              <div className="px-5 pt-2 flex flex-wrap gap-1.5 shrink-0">
                {attachedFiles.map((f, i) => (
                  <span key={i} className="flex items-center gap-1.5 bg-blue-50 border border-blue-100 text-[#1e3a8a] rounded-lg px-2.5 py-1 text-[11px]">
                    <FileText size={10} />
                    {f.name}
                    <button onClick={() => setAttachedFiles((prev) => prev.filter((_, j) => j !== i))}>
                      <X size={10} className="text-blue-400 hover:text-red-400 transition-colors" />
                    </button>
                  </span>
                ))}
              </div>
            )}

            {/* Input */}
            <div className="px-5 py-4 border-t border-slate-100 shrink-0">
              <div className="relative flex items-end gap-2">
                <button onClick={() => fileInputRef.current?.click()} className="shrink-0 p-2 text-slate-400 hover:text-[#1e3a8a] transition-colors rounded-lg hover:bg-slate-100" title="Allega documento">
                  <Paperclip size={16} />
                </button>
                <input ref={fileInputRef} type="file" className="hidden" multiple onChange={handleFileAttach} />
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={`Descrivi la ${getDraftTypeObjectLabel(draftType)} da generare...`}
                  className="flex-1 resize-none rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-800 placeholder:text-slate-400 focus:border-[#1e3a8a] focus:outline-none transition min-h-[44px] max-h-[140px]"
                  rows={1}
                  style={{ lineHeight: '1.5' }}
                />
                <button
                  onClick={handleSend}
                  disabled={!input.trim() && attachedFiles.length === 0}
                  className={`shrink-0 p-2.5 rounded-xl transition-all duration-150
                    ${input.trim() || attachedFiles.length > 0 ? 'bg-[#1e3a8a] text-white hover:bg-[#172554]' : 'bg-slate-100 text-slate-300 cursor-not-allowed'}`}
                >
                  <Send size={15} />
                </button>
              </div>
              <p className="text-[11px] text-slate-400 mt-2 pl-1">Invio con Enter · Shift+Enter per andare a capo</p>
            </div>
          </>
        )}
      </div>

      {/* ── RIGHT: Preview ──────────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        <div className="px-8 py-4 border-b border-slate-100 bg-white flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-[#1e3a8a]/8 flex items-center justify-center">
              <Sparkles size={15} className="text-[#1e3a8a]" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-slate-800">
                Anteprima {getDraftTypeLabel(draftType)}
              </h2>
              {previewContent && (
                <p className="text-[11px] text-slate-400">Aggiornata automaticamente dall'ultima risposta</p>
              )}
            </div>
          </div>
          {previewContent && (
            <div className="flex items-center gap-2">
              <button onClick={handleCopy} className="btn-secondary py-1.5 px-3 text-xs gap-1.5">
                {copied ? <Check size={12} className="text-green-500" /> : <Copy size={12} />}
                {copied ? 'Copiato!' : 'Copia'}
              </button>
              <button onClick={handleDownload} className="btn-secondary py-1.5 px-3 text-xs gap-1.5">
                <Download size={12} />
                Scarica
              </button>
            </div>
          )}
        </div>

        <div className="flex-1 overflow-y-auto px-8 py-6 [scrollbar-width:thin]">
          {previewContent ? (
            <PreviewDocument content={previewContent} type={draftType} />
          ) : (
            <div className="h-full flex flex-col items-center justify-center gap-4 text-center">
              <div className="relative">
                <div className="w-24 h-24 rounded-3xl bg-slate-100 flex items-center justify-center">
                  <FileText size={36} className="text-slate-300" />
                </div>
                <div className="absolute -bottom-1 -right-1 w-8 h-8 rounded-xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #1b9162, #4ade80)' }}>
                  <Sparkles size={14} className="text-white" />
                </div>
              </div>
              <div>
                <p className="text-slate-600 font-medium text-[15px]">Nessuna bozza generata</p>
                <p className="text-slate-400 text-[13px] mt-1 max-w-[280px] leading-relaxed">
                  {`Chiedi ad Agente Vera di generare una ${draftType === 'newsletter' ? 'newsletter normativa' : 'PILL formativa'}. Apparirà qui l'anteprima formattata.`}
                </p>
              </div>
              <div className="flex flex-col gap-2 mt-2">
                <p className="text-[11px] text-slate-400 font-medium uppercase tracking-wide">Esempi di richiesta</p>
                {(draftType === 'newsletter'
                  ? ['Crea una newsletter sulle novità del D.Lgs. 231/01', 'Genera una newsletter sul GDPR aggiornato', 'Scrivi una newsletter su antiriciclaggio per il mese di luglio']
                  : ['Crea un PILL formativo sulla responsabilità d\'impresa', 'Genera un PILL sul whistleblowing', 'Scrivi un PILL formativo sulla privacy in azienda']
                ).map((ex) => (
                  <button key={ex} onClick={() => { setInput(ex); switchTab('new'); }} className="text-[12px] text-[#1e3a8a] bg-blue-50 hover:bg-blue-100 rounded-xl px-4 py-2 text-left transition-colors">
                    "{ex}"
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Newsletter;
