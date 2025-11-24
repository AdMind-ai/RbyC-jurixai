import React, { useState, useRef } from 'react';
import { Upload, CheckCircle2, X, FileText, AlertTriangle, Send } from 'lucide-react';
// Lógica migrada de DocCheck
import { toast } from 'react-toastify';
import { fetchWithAuth } from '../../api/fetchWithAuth';
import ChatMessageList from '../ChatPage/ChatMessageList';

const ComplianceView: React.FC = () => {
  // Estados migrados de DocCheck
  const [file, setFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [messages, setMessages] = useState<Array<{ sender: 'user' | 'ai'; content: string; citations?: string[] }>>([]);
  const [input, setInput] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isTyping, setIsTyping] = useState(false);
  const [isOverview, setIsOverview] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  // Drag & Drop real
  const handleFileDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleClearFileUpload = () => {
    setFile(null);
  };

  // Lógica de análise
  const handleAnalyze = async () => {
      if (!file) return
      setIsLoading(true)
  
      try {
        const convRes = await fetchWithAuth("/openai/chat/create-conversation/", { method: "POST" })
        const convData = await convRes.json()
        const newConversationId = convData.conversation_id
        setConversationId(newConversationId)
  
        setIsChatOpen(true)
        setMessages([])
        setIsTyping(true)
        
        const formData = new FormData()
        formData.append("file", file)
        formData.append("conversation_id", newConversationId)
  
        const res = await fetchWithAuth("/check-compliance", { method: "POST", body: formData })
        const reader = res.body?.getReader()
        const decoder = new TextDecoder()
        let fullMessage = ""
        
        setIsOverview(true) 
        while (true) {
          const { done, value } = await reader!.read()
          if (done) break
          const chunk = decoder.decode(value)
          fullMessage += chunk
  
          setMessages(prev => {
            if (prev.length > 0 && prev[prev.length - 1].sender === "ai") {
              return [...prev.slice(0, -1), { sender: "ai", content: fullMessage }]
            }
            return [...prev, { sender: "ai", content: fullMessage }]
          })
        }
  
        setIsTyping(false)
      } catch (err) {
        console.log(err)
        toast.error("Errore durante l'invio del documento o la lettura del flusso")
      } finally {
        setIsLoading(false)
        setIsOverview(false)
      }
    }

  // Lógica de envio de mensagem
  const handleSend = async () => {
    if (!input.trim() || !conversationId) return

    const userMsg = { sender: "user" as const, content: input }
    setMessages(prev => [...prev, userMsg])
    setInput("")
    setIsTyping(true)

    try {
      const formData = new FormData()
      formData.append("conversation_id", conversationId)
      formData.append("input_text", input)
      const res = await fetchWithAuth("/check-compliance", { method: "POST", body: formData })
      const reader = res.body?.getReader()
      const decoder = new TextDecoder()
      let fullMessage = ""

      setIsOverview(true)
      while (true) {
        const { done, value } = await reader!.read()
        if (done) break
        const chunk = decoder.decode(value)
        fullMessage += chunk

        setMessages(prev => {
          if (prev.length > 0 && prev[prev.length - 1].sender === "ai") {
            return [...prev.slice(0, -1), { sender: "ai", content: fullMessage }]
          }
          return [...prev, { sender: "ai", content: fullMessage }]
        })
      }

      setIsTyping(false)
      setIsOverview(false)
    } catch (err) {
      console.log(err)
      toast.error("Errore durante l'invio del messaggio")
      setIsTyping(false)
    }
  }

  const handleNewDocument = () => {
    setFile(null);
    setMessages([]);
    setIsChatOpen(false);
    setConversationId(null);
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
  };

  return (
    <div className="w-full h-full p-8 overflow-y-auto animate-fade-in max-w-7xl mx-auto">
      <div className="flex flex-col h-full">
        <h2 className="text-2xl font-bold text-slate-800 mb-6 border-b border-slate-300 pb-4 shrink-0">Check compliance</h2>
        {!isChatOpen ? (
          <div className="flex-1 flex flex-col items-center justify-center max-w-2xl mx-auto w-full text-center transition-all">
            <h3 className="text-xl text-slate-500 mb-8 leading-relaxed">
              Carica un documento per l'analisi di conformità. Il sistema verificherà la conformità in base alle regole interne.
            </h3>
            <div
              onDrop={handleFileDrop}
              onDragOver={handleDragOver}
              className={`bg-white p-12 rounded-3xl shadow-sm border-2 border-dashed w-full flex flex-col items-center justify-center transition-all cursor-pointer group relative
              ${file ? 'border-[#1e3a8a] bg-blue-50/30' : 'border-slate-300 hover:border-[#1e3a8a] hover:bg-slate-50'}`}
            >
              {file && (
                <div className="absolute top-4 right-4" onClick={e => { e.stopPropagation(); setFile(null); }}>
                  <div className="p-1 bg-white rounded-full shadow border hover:bg-red-50 text-red-500"><X size={16} /></div>
                </div>
              )}
              <div className={`w-20 h-20 rounded-full flex items-center justify-center mb-6 shadow-lg transition-transform
                ${file ? 'bg-green-600 text-white scale-110' : 'bg-[#1e3a8a] text-white group-hover:scale-110'}`}>
                {file ? <CheckCircle2 size={40} /> : <Upload size={40} />}
              </div>
              {file ? (
                <div className="mb-4">
                  <p className="font-bold text-slate-800 text-lg">{file.name}</p>
                  <p className="text-sm text-slate-500">{(file.size / 1024).toFixed(1)} KB - Pronto per l'analisi</p>
                </div>
              ) : (
                <div className="px-6 py-3 border border-slate-300 rounded-lg text-slate-700 font-small underline decoration-slate-400 underline-offset-4 mb-4">
                  Carica o trascina il tuo file qui
                  <input
                    type="file"
                    accept=".pdf"
                    className="absolute inset-0 opacity-0 cursor-pointer"
                    style={{ width: '100%', height: '100%' }}
                    onChange={handleFileInput}
                  />
                </div>
              )}
              <button
                onClick={file && !isLoading ? handleAnalyze : undefined}
                className={`w-64 py-3 font-bold rounded-lg shadow-lg transition-all animate-bounce-in ${file ? 'bg-[#1e3a8a] text-white hover:bg-blue-900' : 'bg-slate-200 text-slate-500 font-medium cursor-not-allowed'}`}
                disabled={!file || isLoading}
              >
                {isLoading ? 'Analisando...' : 'Invia per l\'analisi'}
              </button>
            </div>
            <p className="mt-6 text-xs text-slate-400">Supporta il formato .pdf</p>
          </div>
        ) : (
          <div className="flex-1 bg-white rounded-xl shadow border border-slate-300 overflow-hidden flex flex-col">
            <div className="p-4 bg-slate-50 border-b border-slate-300 flex justify-between items-center shrink-0">
              <h3 className="font-bold text-slate-800 flex items-center gap-2"><FileText size={18} /> Report Analisi: {file?.name}</h3>
              <div className="flex gap-3">
                <button onClick={handleNewDocument} className="text-sm text-[#1e3a8a] hover:underline">Nuova Analisi</button>
                <button className="text-sm text-red-500 font-medium flex items-center gap-1"><AlertTriangle size={14} /> Esporta PDF</button>
              </div>
            </div>
            <div className="p-8 overflow-y-auto">
              <div className="markdown-body text-sm leading-relaxed">
                <h3 className="text-lg font-bold text-slate-800 mb-2">Chat di analisi dei documenti</h3>
                <p className="text-xs text-slate-400 mb-6">Documenti: {file?.name}</p>
                {/* Mensagens do chat - ChatMessageList dentro de box estilizada */}
                <div className="border border-slate-200 rounded-xl p-6 shadow-sm">
                  <ChatMessageList
                    messages={messages}
                    isTyping={isTyping}
                    isOverview={isOverview}
                    page='check-compliance'
                  />
                </div>
              </div>
            </div>
            <div className="p-4 border-t border-slate-300 bg-white shrink-0">
              <div className="relative flex items-center gap-2">
                <input
                  type="text"
                  placeholder="Inserisci la tua domanda..."
                  className="w-full pl-4 pr-12 py-3 rounded-lg border border-slate-300 outline-none focus:border-[#1e3a8a]"
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleSend()}
                  disabled={isTyping}
                />
                <button
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[#1e3a8a]"
                  onClick={handleSend}
                  disabled={isTyping || !input.trim()}
                >
                  <Send size={20} />
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ComplianceView;
