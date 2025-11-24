import React, { useState, useRef, useEffect } from 'react';
import { Bot, Globe, ArrowRight, Upload, Paperclip, X, Loader2, Send } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface ChatMessage {
  role: 'user' | 'model';
  text: string;
  attachments?: AttachedFile[];
}

interface AttachedFile {
  name: string;
  mimeType: string;
  data: string;
}

const ChatGeneralView: React.FC = () => {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [files, setFiles] = useState<AttachedFile[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      if (file.size > 4 * 1024 * 1024) {
        alert('Il file è troppo grande. Massimo 4MB.');
        return;
      }
      setFiles(prev => [...prev, {
        name: file.name,
        mimeType: file.type || 'application/octet-stream',
        data: ''
      }]);
    }
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const sendMessage = () => {
    if (!input.trim() && files.length === 0) return;
    const userText = input;
    const currentFiles = [...files];
    setMessages(prev => [
      ...prev,
      {
        role: 'user',
        text: userText || (currentFiles.length > 0 ? `[Allegato ${currentFiles.length} file]` : ''),
        attachments: currentFiles
      }
    ]);
    setInput('');
    setFiles([]);
    setIsLoading(true);
    setTimeout(() => {
      setMessages(prev => [
        ...prev,
        {
          role: 'model',
          text: `Risposta simulata di Gemini 3 Pro per: "${userText}"`,
        }
      ]);
      setIsLoading(false);
    }, 1200);
  };

  return (
    <div className="w-full h-full p-8 flex flex-col animate-fade-in relative max-w-7xl mx-auto">
      <div className="flex justify-between items-center border-b border-slate-300 pb-4 mb-4 z-10 bg-[#f8fafc] shrink-0">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            Chat Assistant
            <span className="ml-2 text-xs bg-gradient-to-r from-blue-600 to-purple-600 text-white px-2 py-1 rounded font-mono shadow-sm">Gemini 3 Pro</span>
          </h2>
          <p className="text-xs text-slate-500 mt-1 flex items-center gap-1">
            <Globe size={10} /> Accesso internet attivo &bull; Ragionamento complesso
          </p>
        </div>
        <div className="text-sm text-slate-500 cursor-pointer hover:text-[#1e3a8a] flex items-center gap-1">Chat salvate <ArrowRight size={14} /></div>
      </div>
      {messages.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center">
          <div className="mb-8 flex flex-col items-center">
            <div className="w-16 h-16 bg-white rounded-2xl shadow-md flex items-center justify-center mb-4 text-[#1e3a8a]">
              <Bot size={32} />
            </div>
            <h3 className="text-2xl font-bold text-slate-800 text-center">Come posso esserti utile?</h3>
            <p className="text-slate-500 mt-2 text-center max-w-md">
              Sono potenziato da <strong>Gemini 3</strong>. Posso cercare sul web per normative aggiornate, analizzare documenti allegati e rispondere a quesiti complessi.
            </p>
          </div>
          <div className="w-full max-w-3xl">
            <div className="w-full bg-white p-2 rounded-xl shadow-sm border border-slate-300 relative">
              {files.length > 0 && (
                <div className="flex gap-2 p-2 overflow-x-auto border-b border-slate-200 mb-2">
                  {files.map((f, i) => (
                    <div key={i} className="flex items-center gap-2 bg-slate-100 text-xs px-2 py-1 rounded-lg text-slate-700 animate-fade-in border border-slate-200">
                      <Paperclip size={12} />
                      <span className="max-w-[100px] truncate">{f.name}</span>
                      <button onClick={() => removeFile(i)} className="hover:text-red-500"><X size={12} /></button>
                    </div>
                  ))}
                </div>
              )}
              <textarea
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), sendMessage())}
                placeholder="Scrivi qui la tua richiesta (es. 'Cerca le ultime sentenze sulla Cassazione...')"
                className="w-full p-4 text-lg outline-none text-slate-700 placeholder:text-slate-300 resize-none h-32 bg-transparent"
              />
              <div className="flex justify-between items-center px-4 pb-2">
                <div>
                  <input
                    type="file"
                    ref={fileInputRef}
                    className="hidden"
                    onChange={handleFileChange}
                    accept=".pdf,.doc,.docx,.txt,.jpg,.png"
                  />
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-300 rounded-lg text-slate-600 hover:border-[#1e3a8a] hover:text-[#1e3a8a] text-sm transition-colors"
                  >
                    <Upload size={16} /> Allega File
                  </button>
                </div>
                <button
                  onClick={sendMessage}
                  disabled={(!input.trim() && files.length === 0) || isLoading}
                  className="px-8 py-2 bg-slate-200 text-slate-500 font-medium rounded-lg hover:bg-[#1e3a8a] hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {isLoading ? <Loader2 className="animate-spin" size={18} /> : 'Invia'}
                </button>
              </div>
            </div>
          </div>
          <div className="mt-8 flex gap-4 text-sm text-slate-500">
            <span className="px-3 py-1 bg-slate-100 rounded-full border border-slate-300">⚖️ Ricerca Giurisprudenza</span>
            <span className="px-3 py-1 bg-slate-100 rounded-full border border-slate-300">📄 Analisi Contratti</span>
            <span className="px-3 py-1 bg-slate-100 rounded-full border border-slate-300">🌍 News Normative</span>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto space-y-6 pb-4 pr-2" ref={scrollRef}>
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`flex gap-4 max-w-[90%] lg:max-w-[80%] ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${m.role === 'user' ? 'bg-slate-200' : 'bg-gradient-to-br from-[#1e3a8a] to-purple-600 text-white shadow-md'}`}>
                    {m.role === 'user' ? 'TU' : <Bot size={18} />}
                  </div>
                  <div className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
                    <div className={`py-3 px-5 rounded-2xl shadow-sm border ${
                      m.role === 'user'
                        ? 'bg-white border-slate-300 rounded-tr-none'
                        : 'bg-white border-slate-200 rounded-tl-none'
                    }`}>
                      {m.role === 'user' && m.attachments && m.attachments.length > 0 && (
                        <div className="mb-2 flex flex-wrap gap-2 justify-end">
                          {m.attachments.map((att, idx) => (
                            <div key={idx} className="bg-slate-50 text-xs flex items-center gap-1 px-2 py-1 rounded border border-slate-300 text-slate-600">
                              <Paperclip size={10} /> {att.name}
                            </div>
                          ))}
                        </div>
                      )}
                      <div className="markdown-body text-sm leading-relaxed text-slate-800">
                        <ReactMarkdown>{m.text}</ReactMarkdown>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="flex gap-4 max-w-[80%]">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#1e3a8a] to-purple-600 text-white flex items-center justify-center shrink-0">
                    <Bot size={18} />
                  </div>
                  <div className="bg-white border border-slate-300 py-3 px-5 rounded-2xl rounded-tl-none shadow-sm flex items-center gap-2">
                    <Loader2 className="animate-spin text-[#1e3a8a]" size={16} />
                    <span className="text-sm text-slate-500">Sto analizzando e cercando informazioni...</span>
                  </div>
                </div>
              </div>
            )}
          </div>
          <div className="bg-white border border-slate-300 rounded-xl p-2 mt-4 shadow-sm shrink-0 relative">
            {files.length > 0 && (
              <div className="absolute bottom-full left-0 mb-2 ml-2 flex gap-2">
                {files.map((f, i) => (
                  <div key={i} className="flex items-center gap-2 bg-slate-800 text-white text-xs px-3 py-1.5 rounded-lg shadow-lg animate-fade-in">
                    <Paperclip size={12} />
                    <span className="max-w-[150px] truncate">{f.name}</span>
                    <button onClick={() => removeFile(i)} className="hover:text-red-300 ml-1"><X size={12} /></button>
                  </div>
                ))}
              </div>
            )}
            <textarea
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), sendMessage())}
              placeholder="Fai una domanda o chiedi di analizzare i file allegati..."
              className="w-full p-3 outline-none resize-none text-slate-700 max-h-32 bg-transparent text-sm"
              rows={1}
            />
            <div className="flex justify-between px-2 pb-1 items-center">
              <div>
                <input
                  type="file"
                  ref={fileInputRef}
                  className="hidden"
                  onChange={handleFileChange}
                  accept=".pdf,.doc,.docx,.txt,.jpg,.png"
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="text-slate-400 hover:text-[#1e3a8a] p-2 rounded-full hover:bg-slate-50 transition-colors"
                  title="Allega file"
                >
                  <Paperclip size={18} />
                </button>
              </div>
              <button
                onClick={sendMessage}
                disabled={(!input.trim() && files.length === 0) || isLoading}
                className="px-4 py-1.5 bg-[#1e3a8a] hover:bg-blue-900 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                Invia <Send size={14} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatGeneralView;
