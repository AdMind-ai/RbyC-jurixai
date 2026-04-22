
import React, { useState, useEffect, useRef } from 'react';
import { fetchWithAuth } from '../../api/fetchWithAuth';
import { Send, Bot, User, Info } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { Company, Deadline } from '../../types/types';

interface Message {
  id: number;
  sender: 'user' | 'bot';
  text: string;
}

const askOpenAILegalAssistant = async (query: string, contextData: string): Promise<string> => {
  const formData = new FormData();
  formData.append(
    'content',
    [
      'Rispondi come assistente legale per la segreteria societaria di uno studio legale.',
      'Usa solo il contesto fornito quando parli di societa, scadenze, cariche sociali o dati interni.',
      '',
      'CONTESTO DATI:',
      contextData,
      '',
      'DOMANDA UTENTE:',
      query,
    ].join('\n')
  );

  const response = await fetchWithAuth('/openai/chat/send-message/', {
    method: 'POST',
    body: formData,
  });

  if (!response.ok || !response.body) {
    throw new Error(`OpenAI request failed with status ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let done = false;
  let text = '';

  while (!done) {
    const { value, done: doneReading } = await reader.read();
    done = doneReading;
    text += decoder.decode(value, { stream: true });
  }

  return text || 'Non ho trovato una risposta utile.';
};


const AIAssistant: React.FC = () => {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    { id: 1, sender: 'bot', text: 'Ciao! Sono il tuo assistente legale. Posso darti informazioni sulle società gestite, le scadenze imminenti o le cariche sociali. Chiedimi pure!' }
  ]);
  const [isTyping, setIsTyping] = useState(false);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [deadlines, setDeadlines] = useState<Deadline[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };
  // Busca dados do backend ao montar
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Buscar companies
    fetchWithAuth('/companies')
      .then(res => res.json())
      .then(data => setCompanies(data))
      .catch(() => setCompanies([]));
    // Buscar deadlines
    fetchWithAuth('/deadlines')
      .then(res => res.json())
      .then(data => setDeadlines(data))
      .catch(() => setDeadlines([]));
  }, []);


  const handleSend = async () => {
    if (!input.trim()) return;

    const userMsg: Message = { id: Date.now(), sender: 'user', text: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsTyping(true);

    // Prepara dados de contexto para a AI
    const contextData = JSON.stringify({
      companies: companies.map((c: Company) => ({
         name: c.name,
         type: c.type,
         vat: c.vatNumber,
         officers: c.officers,
         shareholders: c.shareholders,
         nextMeeting: c.nextMeetingDate
      })),
      deadlines: deadlines.filter((d: Deadline) => !d.completed)
    });

    try {
      const responseText = await askOpenAILegalAssistant(userMsg.text, contextData);
      const botMsg: Message = { id: Date.now() + 1, sender: 'bot', text: responseText };
      setMessages(prev => [...prev, botMsg]);
    } catch (error) {
      console.error('Erro ao consultar assistente OpenAI:', error);
      setMessages(prev => [
        ...prev,
        {
          id: Date.now() + 1,
          sender: 'bot',
          text: 'Si e verificato un errore durante la comunicazione con l assistente.',
        },
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="w-full h-full p-6 flex flex-col max-w-3xl mx-auto animate-fade-in">
      <div className="mb-3 border-b border-slate-300 pb-3">
        <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
          <Bot className="text-[#1e3a8a]" />
          Assistente Legale
        </h2>
        <p className="text-slate-500 text-sm">Interroga il database dello studio con linguaggio naturale</p>
      </div>

      <div className="flex-1 bg-white rounded-lg shadow-sm border border-slate-300 overflow-hidden flex flex-col">
        {/* Chat Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50/50">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
               <div className={`flex max-w-[80%] gap-3 ${msg.sender === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                    msg.sender === 'user' ? 'bg-slate-200 text-slate-600' : 'bg-[#1e3a8a] text-white'
                  }`}>
                    {msg.sender === 'user' ? <User size={16} /> : <Bot size={16} />}
                  </div>
                  <div className={`p-3 rounded-xl text-sm leading-relaxed shadow-sm ${
                    msg.sender === 'user' 
                      ? 'bg-white text-slate-800 rounded-tr-none border border-slate-300' 
                      : 'bg-[#1e3a8a] text-white rounded-tl-none shadow-md'
                  }`}>
                     <ReactMarkdown
                        components={{
                            p: ({...props}) => <p className="mb-1 last:mb-0" {...props} />,
                            ul: ({...props}) => <ul className="list-disc pl-4 my-1" {...props} />,
                            ol: ({...props}) => <ol className="list-decimal pl-4 my-1" {...props} />,
                            li: ({...props}) => <li className="my-0.5" {...props} />,
                            strong: ({...props}) => <strong className="font-bold" {...props} />
                        }}
                     >
                        {msg.text}
                     </ReactMarkdown>
                  </div>
               </div>
            </div>
          ))}
          {isTyping && (
            <div className="flex justify-start">
               <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-[#1e3a8a] text-white flex items-center justify-center">
                     <Bot size={16} />
                  </div>
                  <div className="bg-blue-50 px-3 py-2 rounded-xl rounded-tl-none border border-blue-200">
                     <div className="flex gap-1">
                        <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"></span>
                        <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce delay-75"></span>
                        <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce delay-150"></span>
                     </div>
                  </div>
               </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-3 bg-white border-t border-slate-200">
            <div className="relative flex items-center gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Chiedi qualcosa sulle scadenze o sulle società..."
                className="flex-1 p-2 pl-3 pr-10 rounded-full border border-slate-300 bg-slate-50 focus:bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all text-sm"
              />
              <button 
                onClick={handleSend}
                disabled={!input.trim() || isTyping}
                className="absolute right-2 p-1.5 bg-[#1e3a8a] text-white rounded-full hover:bg-blue-900 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors shadow-md"
              >
                <Send size={16} />
              </button>
            </div>
            <div className="mt-1 flex items-center gap-2 text-xs text-slate-400 justify-center">
               <Info size={11} />
               <span>L'AI può commettere errori. Verifica sempre le informazioni importanti.</span>
            </div>
        </div>
      </div>
    </div>
  );
};

export default AIAssistant;
