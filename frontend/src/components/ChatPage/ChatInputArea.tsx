import React, { useState, useEffect, useRef } from 'react';
import { fetchWithAuth } from '../../api/fetchWithAuth';

interface ChatInputAreaProps {
  onSend: (content: string, sender: 'user' | 'ai', isStream?: boolean) => void;
  selectedChat: { id: number | string; name: string; thread_id: string | null} | null;
  setSelectedChat: React.Dispatch<React.SetStateAction<{ id: number | string; name: string; thread_id: string | null} | null>>;
  searchWebEnabled: boolean;
  setSearchWebEnabled: (enabled: boolean) => void;
  setCitations?: React.Dispatch<React.SetStateAction<string[]>>;
  setIsOverview: React.Dispatch<React.SetStateAction<boolean>>;
  setIsTyping: React.Dispatch<React.SetStateAction<boolean>>;
  conversationId: string
}

const ChatInputArea: React.FC<ChatInputAreaProps & { messages: unknown[] }> = ({
  onSend,
  selectedChat,
  setSearchWebEnabled,
  setCitations,
  setIsOverview,
  setIsTyping,
  conversationId,
  messages
}) => {
  const [input, setInput] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Show empty state if no messages have been sent yet
  const showEmptyState = !selectedChat && messages.length === 0;


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
      if (setCitations && e.detail.citations) {
        setCitations(e.detail.citations);
      }
    }
  }

  useEffect(() => {
    const handler = handleDeepResearchReady as EventListener;
    window.addEventListener("deepResearchReady", handler as EventListener);
    return () => window.removeEventListener("deepResearchReady", handler as EventListener);
  }, [selectedChat, onSend]);


  const handleSubmit = async () => {
    setIsOverview(false);
    setIsTyping(true);
    if (!input.trim() && files.length === 0) return;

    onSend(input, 'user');
    setInput('');
    setFiles([]);

    try {
      const formData = new FormData();
      formData.append('content', input);
      files.forEach(file => formData.append('file', file));
      if (selectedChat) {
        formData.append('conversation_id', selectedChat.thread_id as string);
      } else if (conversationId) {
        formData.append('conversation_id', conversationId);
      }
      const response = await fetchWithAuth('/openai/chat/send-message/', {
        method: 'POST',
        body: formData
      });
      setIsTyping(false);
      if (!response.ok || !response.body) {
        onSend('Erro ao conectar.', 'ai');
        return;
      }
      if (response.ok) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let done = false;
        while (!done) {
          const { value, done: doneReading } = await reader.read();
          done = doneReading;
          const chunkValue = decoder.decode(value, { stream: true });
          onSend(chunkValue, 'ai', true);
        }
      } else {
        console.error('Erro ao conectar:', response.statusText);
        onSend('Erro ao gerar resposta.', 'ai');
      }
    } catch (error) {
      console.error('Error sending message:', error);
      setIsTyping(false);
      onSend('Erro ao enviar mensagem.', 'ai');
    }
  };



  return (
    <div className={
      messages.length > 0 || selectedChat
        ? "w-[100%] max-w-6xl flex flex-col items-center justify-center mt-0 pt-0 absolute bottom-0 left-1/2 -translate-x-1/2 z-40 bg-transparent mb-6"
        : "w-full flex flex-col items-center justify-center mt-0 pt-0"
    }>
      {showEmptyState && (
        <>
          <div className="flex flex-col items-center justify-center mb-4">
            <div className="w-14 h-14 bg-white rounded-xl shadow-md flex items-center justify-center mb-3 text-[#1e3a8a]">
              {/* Bot icon */}
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-10 h-10">
                <rect x="4" y="8" width="16" height="10" rx="4" fill="#fff" stroke="#1e3a8a" />
                <rect x="8" y="12" width="2" height="2" rx="1" fill="#1e3a8a" />
                <rect x="14" y="12" width="2" height="2" rx="1" fill="#1e3a8a" />
                <rect x="10" y="16" width="4" height="1.5" rx="0.75" fill="#1e3a8a" />
              </svg>
            </div>
            <h3 className="text-xl font-bold text-slate-800 text-center">Come posso esserti utile?</h3>
            <p className="text-slate-500 mt-1 text-center max-w-md">
              Sono potenziato da <strong>GPT-5.1</strong>. Posso cercare sul web per normative aggiornate, analizzare documenti allegati e rispondere a quesiti complessi.
            </p>
          </div>
          <div className="w-full max-w-2xl">
            <div className="w-full bg-white p-1.5 rounded-lg shadow-sm border border-slate-300 relative">
              {files.length > 0 && (
                <div className="flex gap-2 p-2 overflow-x-auto border-b border-slate-200 mb-2">
                  {files.map((f, i) => (
                    <div key={i} className="flex items-center gap-2 bg-slate-100 text-xs px-2 py-1 rounded-lg text-slate-700 animate-fade-in border border-slate-200">
                      <span className="inline-block w-4 h-4 bg-slate-300 rounded-full mr-1" />
                      <span className="max-w-[100px] truncate">{f.name}</span>
                      <button onClick={() => setFiles(prev => prev.filter((_, idx) => idx !== i))} className="hover:text-red-500"><span className="inline-block w-3 h-3 bg-red-400 rounded-full" /></button>
                    </div>
                  ))}
                </div>
              )}
              <textarea
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleSubmit())}
                placeholder="Scrivi qui la tua richiesta (es. 'Cerca le ultime sentenze sulla Cassazione...')"
                className="w-full p-3 text-base outline-none text-slate-700 placeholder:text-slate-300 resize-none h-24 bg-transparent"
              />
              <div className="flex justify-between items-center px-2 pb-1">
                <div>
                  <input
                    type="file"
                    ref={fileInputRef}
                    className="hidden"
                    onChange={handleFileChange}
                    accept=".pdf,.doc,.docx,.txt,.jpg,.png"
                  />
                  <button
                    onClick={handleFileUploadClick}
                    className="flex items-center gap-2 px-3 py-1.5 bg-white border border-slate-300 rounded-md text-slate-600 hover:border-[#1e3a8a] hover:text-[#1e3a8a] text-sm transition-colors"
                  >
                    <span className="inline-block w-4 h-4 bg-slate-300 rounded-full mr-1" /> Allega File
                  </button>
                </div>
                <button
                  onClick={handleSubmit}
                  disabled={(!input.trim() && files.length === 0) || isLoading}
                  className="px-6 py-1.5 bg-slate-200 text-slate-500 font-medium rounded-md hover:bg-[#1e3a8a] hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {isLoading ? <span className="inline-block w-4 h-4 bg-slate-300 rounded-full animate-spin" /> : 'Invia'}
                </button>
              </div>
            </div>
          </div>
          <div className="mt-6 flex gap-2 text-sm text-slate-500 justify-center">
            <span className="px-2.5 py-0.5 bg-slate-100 rounded-full border border-slate-300 flex items-center gap-2"><span className="mr-1">⚖️</span> Ricerca Giurisprudenza</span>
            <span className="px-2.5 py-0.5 bg-slate-100 rounded-full border border-slate-300 flex items-center gap-2"><span className="mr-1">📄</span> Analisi Contratti</span>
            <span className="px-2.5 py-0.5 bg-slate-100 rounded-full border border-slate-300 flex items-center gap-2"><span className="mr-1">🌍</span> News Normative</span>
          </div>
        </>
      )}
      {!showEmptyState && (
        <div className="w-full flex justify-center">
          <form className="w-full max-w-5xl bg-white px-6 py-3 rounded-xl shadow border border-slate-200 flex items-center gap-3" onSubmit={e => {e.preventDefault(); handleSubmit();}}>
            <input
              type="file"
              ref={fileInputRef}
              className="hidden"
              onChange={handleFileChange}
              accept=".pdf,.doc,.docx,.txt,.jpg,.png"
            />
            <button
              type="button"
              onClick={handleFileUploadClick}
              className="flex items-center justify-center w-7 h-7 bg-transparent text-[#a3a8c5] hover:text-[#1e3a8a] rounded-md focus:outline-none"
              title="Allega File"
            >
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-5 h-5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-3A2.25 2.25 0 008.25 5.25V9m7.5 0v9A2.25 2.25 0 0113.5 20.25h-3A2.25 2.25 0 018.25 18V9m7.5 0H8.25" />
              </svg>
            </button>
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleSubmit())}
              placeholder="Fai una domanda o chiedi di analizzare i file allegati..."
              className="flex-1 bg-transparent outline-none text-base text-slate-700 placeholder:text-slate-400 px-1"
              style={{ minWidth: 0 }}
              autoComplete="off"
            />
            <button
              type="submit"
              disabled={(!input.trim() && files.length === 0) || isLoading}
              className="flex items-center justify-center px-5 py-2 bg-[#a3a8c5] text-white font-semibold rounded-lg hover:bg-[#1e3a8a] transition-colors disabled:opacity-50 disabled:cursor-not-allowed gap-2"
            >
              {isLoading ? (
                <span className="inline-block w-4 h-4 bg-slate-300 rounded-full animate-spin" />
              ) : (
                <>
                  Invia
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-5 h-5 ml-1">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14M12 5l7 7-7 7" />
                  </svg>
                </>
              )}
            </button>
          </form>
        </div>
      )}
    </div>
  );
};

export default ChatInputArea;