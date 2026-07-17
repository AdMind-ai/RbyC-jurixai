import React, { useEffect, useRef } from 'react'
import { Paperclip, Bot } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import { toast } from 'react-toastify'

interface Message {
  sender: 'user' | 'ai'
  content: string
  citations?: string[]
}

interface ChatMessageListProps {
  messages: Message[]
  isTyping: boolean
  isOverview: boolean;
  page?: string;
  chatColor?: string;
}

const TypingIndicator = () => (
  <div className="flex space-x-1.5 items-center px-1">
    <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
    <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
    <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
  </div>
)

const ChatMessageList: React.FC<ChatMessageListProps> = ({ messages, isTyping, isOverview, page, chatColor }) => {
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  const parseThinkTag = (content: string) => {
    const thinkTagOpen = content.lastIndexOf('<think>');
    const thinkTagClose = content.lastIndexOf('</think>');
    
    if (thinkTagOpen !== -1 && thinkTagClose > thinkTagOpen) {
      const beforeThink = content.slice(0, thinkTagOpen);
      const afterThink = content.slice(thinkTagClose + '</think>'.length);
      content = beforeThink + afterThink;
    }
    
    if (thinkTagOpen !== -1 && thinkTagClose <= thinkTagOpen) {
      content = content.slice(0, thinkTagOpen);
    }
  
    return content.trim(); 
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    toast.success('Codice copiato!')
  }

  const citeLinks = (text: string, citations: string[] = []) => {
    return text.replace(/\[(\d+)\]/g, (match, num) => {
      const citationLink = citations[parseInt(num) - 1];
      if (citationLink) {
        return `[ [${num}] ](${citationLink})`
      }
      return match;
    });
  };
  
  const handleThink = (content: string): boolean => {
    const thinkTagOpen = content.lastIndexOf('<think>');
    const thinkTagClose = content.lastIndexOf('</think>');
    return thinkTagOpen !== -1 && (thinkTagClose === -1 || thinkTagClose < thinkTagOpen);
  };

  if (messages.length === 0 && !isTyping) {
    return (
      <div className="flex-1 overflow-y-auto px-6 py-4 bg-[#f8fafc] flex flex-col items-center justify-center">
        <Bot size={40} className="text-slate-300 mb-4" />
        <p className="text-slate-400 text-sm">Inizia una conversazione</p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-6 py-4 bg-[#f8fafc] space-y-6">
      {messages.map((msg, idx) => {
        const isThinking = handleThink(msg.content);
        const parsedContent = parseThinkTag(msg.content);
        const contentWithCitations = msg.sender === 'ai' 
          ? citeLinks(parsedContent, msg.citations) 
          : parsedContent;
        
        const isUser = msg.sender === 'user';

        return (
          <div key={idx} className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'}`}>
            {!isUser && (
              <div className="w-7 h-7 shrink-0 bg-[#1e3a8a] text-white rounded-full flex items-center justify-center mr-3 mt-1 shadow-sm">
                <Bot size={16} />
              </div>
            )}
            <div className={`flex flex-col ${isUser ? 'items-end max-w-[70%]' : 'items-start max-w-[80%]'}`}>
              <div className={`${isUser ? 'chat-bubble-user' : 'chat-bubble-ai'} ${!isUser && isThinking ? 'py-4 px-5' : ''}`}>
                
                {isUser && Array.isArray(msg.citations) && msg.citations.length > 0 && (
                  <div className="mb-3 flex flex-wrap gap-2 justify-end">
                    {msg.citations.map((fileName, fileIdx) => (
                      <div key={fileIdx} className="bg-white/20 text-xs flex items-center gap-1 px-2 py-1 rounded border border-white/30 text-white">
                        <Paperclip size={10} /> {fileName}
                      </div>
                    ))}
                  </div>
                )}

                {isThinking ? (
                  <TypingIndicator />
                ) : (
                  <div className="prose prose-sm max-w-none break-words">
                    <ReactMarkdown 
                      remarkPlugins={[remarkGfm]} 
                      rehypePlugins={[rehypeHighlight]}
                      components={{
                        code({ className, children, ...props }) {
                          const match = /language-(\w+)/.exec(className || '');
                          const language = match ? match[1] : '';
                          return match ? (
                            <div className="relative mt-2 mb-2 bg-slate-800 rounded-lg group shadow-sm">
                              <button
                                onClick={() => copyToClipboard(String(children).replace(/\n$/, ''))}
                                className="absolute top-2 right-2 text-slate-400 hover:text-white text-xs opacity-0 group-hover:opacity-100 transition-opacity"
                              >
                                Copia
                              </button>
                              <pre className="p-4 overflow-x-auto text-sm text-slate-50 m-0 rounded-lg">
                                <code className={className} {...props}>
                                  {children}
                                </code>
                              </pre>
                            </div>
                          ) : (
                            <code className="bg-black/10 px-1 py-0.5 rounded text-sm font-mono" {...props}>
                              {children}
                            </code>
                          );
                        },
                        p: ({ children }) => <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>,
                        a: ({ href, children }) => <a href={href} target="_blank" rel="noopener noreferrer" className="text-[#15803d] hover:underline font-medium">{children}</a>,
                        ul: ({ children }) => <ul className="list-disc pl-4 mb-2 space-y-1">{children}</ul>,
                        ol: ({ children }) => <ol className="list-decimal pl-4 mb-2 space-y-1">{children}</ol>,
                        li: ({ children }) => <li className="leading-relaxed">{children}</li>,
                        table: ({ children }) => <div className="overflow-x-auto mb-2"><table className="min-w-full text-left border-collapse">{children}</table></div>,
                        th: ({ children }) => <th className="border-b border-slate-200 px-3 py-2 font-semibold bg-slate-50 text-slate-600">{children}</th>,
                        td: ({ children }) => <td className="border-b border-slate-100 px-3 py-2">{children}</td>,
                      }}
                    >
                      {contentWithCitations}
                    </ReactMarkdown>
                  </div>
                )}
              </div>
            </div>
          </div>
        );
      })}
      
      {isTyping && ( 
        <div className="flex w-full justify-start">
          <div className="w-7 h-7 shrink-0 bg-[#1e3a8a] text-white rounded-full flex items-center justify-center mr-3 mt-1 shadow-sm">
            <Bot size={16} />
          </div>
          <div className="chat-bubble-ai py-4 px-5">
            <TypingIndicator />
          </div>
        </div>
      )}

      <div ref={messagesEndRef} className="h-4"></div>
    </div>
  )
}

export default ChatMessageList
