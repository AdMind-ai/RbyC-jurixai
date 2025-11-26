import React, { useState, useRef } from 'react';
import { marked } from 'marked';
import jsPDF from 'jspdf';
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

  // Lógica de análise
  const handleAnalyze = async () => {
      if (!file) return
      setIsLoading(true)
  
      try {
        const convRes = await fetchWithAuth("/openai/chat/create-conversation/", { method: "POST" })
        const convData = await convRes.json()
        const newConversationId = convData.conversation_id
        setConversationId(newConversationId)
  
        setMessages([])
        
        const formData = new FormData()
        formData.append("file", file)
        formData.append("conversation_id", newConversationId)
        
        const res = await fetchWithAuth("/check-compliance", { method: "POST", body: formData })
        const reader = res.body?.getReader()
        const decoder = new TextDecoder()
        let fullMessage = ""
        
        setIsOverview(true)
        setIsChatOpen(true)
        setIsTyping(true)
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
    <div className="w-full h-full p-8 overflow-y-auto animate-fade-in max-w-6xl mx-auto">
      <div className="flex flex-col h-full">
        <h2 className="text-1xl font-bold text-slate-800 mb-3 border-b border-slate-300 pb-2 shrink-0">Check compliance</h2>
        {!isChatOpen ? (
          <div className="flex-1 flex flex-col items-center justify-center max-w-2xl mx-auto w-full text-center transition-all">
            {isLoading ? (
              <div className="flex flex-col items-center">
                <div className="w-16 h-16 border-4 border-slate-200 border-t-[#1e3a8a] rounded-full animate-spin mb-6"></div>
                <h3 className="text-xl font-bold text-slate-800">Analisi in corso...</h3>
                <p className="text-slate-500">Sto verificando le clausole contrattuali</p>
              </div>
            ) : (
              <>
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
                    <div className="mb-2">
                      <p className="font-bold text-slate-800 text-sm">{file.name}</p>
                      <p className="text-xs text-slate-500">{(file.size / 1024).toFixed(1)} KB - Pronto para análise</p>
                    </div>
                  ) : (
                    <div className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 text-sm underline decoration-slate-400 underline-offset-2 mb-2">
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
                    className={`w-40 py-3 mt-4 text-sm font-bold rounded-md shadow transition-all animate-bounce-in ${file ? 'bg-[#1e3a8a] text-white hover:bg-blue-900' : 'bg-slate-200 text-slate-500 font-medium cursor-not-allowed'}`}
                    disabled={!file || isLoading}
                  >
                    {"Invia per l'analisi"}
                  </button>
                </div>
                <p className="mt-2 text-xs text-slate-400">Suporta formato .pdf</p>
              </>
            )}
          </div>
        ) : (
          <div className="flex-1 bg-white rounded-lg shadow border border-slate-300 overflow-hidden flex flex-col">
            <div className="p-2 bg-slate-50 border-b border-slate-300 flex justify-between items-center shrink-0">
              <h3 className="font-bold text-slate-800 flex items-center gap-2 text-sm"><FileText size={16} /> Report: {file?.name}</h3>
              <div className="flex gap-2">
                <button onClick={handleNewDocument} className="text-xs text-[#1e3a8a] hover:underline">Nuova Analisi</button>
                <button
                  className="text-xs text-red-500 font-medium flex items-center gap-1"
                  onClick={async () => {
                    const firstAIMessage = messages.find(m => m.sender === 'ai');
                    if (!firstAIMessage) {
                      toast.error('Nenhuma resposta do AI encontrada.');
                      return;
                    }
                    // Adiciona CSS customizado para o PDF
                    const customStyles = `
                      <style>
                        body { font-family: 'Arial', sans-serif; color: #222; margin: 0; padding: 0; }
                        .pdf-content { padding-top: 5mm; padding-bottom: 5mm; }
                        h1 { font-size: 2em; margin-bottom: 0.5em; color: #1e3a8a; }
                        h2 { font-size: 1.5em; margin-bottom: 0.5em; color: #1e3a8a; }
                        h3 { font-size: 1.2em; margin-bottom: 0.5em; color: #1e3a8a; }
                        p, li { font-size: 1em; line-height: 1.6; margin-bottom: 0.5em; }
                        ul, ol { margin-left: 1.5em; }
                        code, pre { background: #f4f4f4; font-size: 0.95em; border-radius: 4px; padding: 2px 6px; }
                        blockquote { border-left: 4px solid #1e3a8a; padding-left: 1em; color: #555; margin: 1em 0; }
                        table { border-collapse: collapse; width: 100%; margin-bottom: 1em; }
                        th, td { border: 1px solid #ccc; padding: 6px 10px; font-size: 0.95em; }
                        th { background: #e5e7eb; }
                      </style>
                    `;
                    const htmlContent = customStyles + `<div class='pdf-content'>` + marked.parse(firstAIMessage.content) + `</div>`;
                    const doc = new jsPDF({ unit: 'mm', format: 'a4', orientation: 'portrait' });
                    // Cria elemento temporário para renderizar HTML
                    const tempDiv = document.createElement('div');
                    tempDiv.innerHTML = htmlContent;
                    document.body.appendChild(tempDiv);
                    await doc.html(tempDiv, {
                      x: 10,
                      y: 0,
                      width: 180,
                      windowWidth: 800,
                      margin: [30, 8, 30, 8], // top, right, bottom, left
                      callback: function () {
                        doc.save(`${file?.name || 'report'}.pdf`);
                        document.body.removeChild(tempDiv);
                      }
                    });
                  }}
                >
                  <AlertTriangle size={12} /> Esporta PDF
                </button>
              </div>
            </div>
            <div className="p-4 overflow-y-auto">
              <div className="markdown-body text-xs leading-relaxed">
                <h3 className="text-base font-bold text-slate-800 mb-1">Chat de análise</h3>
                <p className="text-xs text-slate-400 mb-2">Documento: {file?.name}</p>
                {/* Mensagens do chat - ChatMessageList dentro de box estilizada */}
                <div className="border border-slate-200 rounded-lg p-3 shadow-sm">
                  <ChatMessageList
                    messages={messages}
                    isTyping={isTyping}
                    isOverview={isOverview}
                    page='check-compliance'
                  />
                </div>
              </div>
            </div>
            <div className="p-2 border-t border-slate-300 bg-white shrink-0">
              <div className="relative flex items-center gap-1">
                <input
                  type="text"
                  placeholder="Digite sua pergunta..."
                  className="w-full pl-3 pr-10 py-2 rounded-md border border-slate-300 outline-none focus:border-[#1e3a8a] text-xs"
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleSend()}
                  disabled={isTyping}
                />
                <button
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-[#1e3a8a]"
                  onClick={handleSend}
                  disabled={isTyping || !input.trim()}
                >
                  <Send size={16} />
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
