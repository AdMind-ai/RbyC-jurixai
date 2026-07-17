import React, { useEffect, useRef } from 'react'
import { Search } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import SourcesPanel, { SourceItem } from './SourcesPanel'

interface Message {
  sender: 'user' | 'ai'
  content: string
  sources?: SourceItem[]
  isStreaming?: boolean
}

interface DocSearchMessageListProps {
  messages: Message[]
  isTyping: boolean
}

function removeCitations(text: string): string {
  return text.replace(/【[^【†】]*†[^【†】]*】/g, '')
}

const TypingIndicator = () => (
  <div className="flex space-x-1.5 items-center px-1">
    <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
    <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
    <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
  </div>
)

const DocSearchMessageList: React.FC<DocSearchMessageListProps> = ({
  messages,
  isTyping,
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  if (messages.length === 0 && !isTyping) {
    return (
      <div className="flex-1 overflow-y-auto px-6 py-4 bg-[#f8fafc] flex flex-col items-center justify-center">
        <Search size={40} className="text-slate-300 mb-4" />
        <p className="text-slate-400 text-sm">Seleziona una categoria ed effettua una ricerca</p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-6 py-4 bg-[#f8fafc] space-y-6">
      {messages.map((msg, idx) => {
        const content = removeCitations(msg.content)
        const isUser = msg.sender === 'user';

        return (
          <div key={idx} className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'}`}>
            {!isUser && (
              <div className="w-7 h-7 shrink-0 bg-[#1e3a8a] text-white rounded-full flex items-center justify-center mr-3 mt-1 shadow-sm">
                <Search size={14} />
              </div>
            )}
            <div className={`flex flex-col ${isUser ? 'items-end max-w-[70%]' : 'items-start max-w-[80%]'}`}>
              <div className={isUser ? 'chat-bubble-user' : 'chat-bubble-ai'}>
                <div className="prose prose-sm max-w-none break-words">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    rehypePlugins={[rehypeHighlight]}
                    components={{
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
                    {content}
                  </ReactMarkdown>
                </div>

                {msg.sources && msg.sources.length > 0 && (
                  <div className="mt-4 border-t border-slate-100 pt-3">
                    <SourcesPanel sources={msg.sources} />
                  </div>
                )}

                {msg.sender === 'ai' && msg.isStreaming && (
                  <div className="flex items-center gap-2 mt-3 pt-3 border-t border-slate-100">
                    <span className="text-xs text-slate-500 font-medium">Scrivendo</span>
                    <TypingIndicator />
                  </div>
                )}
              </div>
            </div>
          </div>
        )
      })}

      {isTyping && (
        <div className="flex w-full justify-start">
          <div className="w-7 h-7 shrink-0 bg-[#1e3a8a] text-white rounded-full flex items-center justify-center mr-3 mt-1 shadow-sm">
            <Search size={14} />
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

export default DocSearchMessageList
