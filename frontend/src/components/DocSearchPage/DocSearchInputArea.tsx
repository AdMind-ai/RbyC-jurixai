import React, { useState, useEffect, useRef } from 'react';
import { Send } from 'lucide-react';

interface DocSearchInputAreaProps {
  onSendMessage: (message: string) => Promise<void>;
  isEmptyMessages: boolean;
  isTyping: boolean;
  setIsTyping: React.Dispatch<React.SetStateAction<boolean>>;
}

const DocSearchInputArea: React.FC<DocSearchInputAreaProps> = ({
  onSendMessage,
  isEmptyMessages,
  isTyping,
  setIsTyping
}) => {
  const [text, setText] = useState('');
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = async () => {
    if (!text.trim() || isTyping) return;
    setIsTyping(true);
    const content = text;
    setText('');
    await onSendMessage(content);
  };

  const adjustTextareaHeight = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
  };

  return (
    <div className="bg-white border-t border-slate-100 px-6 py-4 w-full shrink-0">
      <div className="max-w-4xl mx-auto relative flex items-end">
        <textarea
          ref={inputRef}
          value={text}
          onChange={adjustTextareaHeight}
          onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey && text.trim()) {
              e.preventDefault();
              handleSubmit();
            }
          }}
          placeholder="Descrivi il documento o l'informazione che ti serve..."
          className="apple-input w-full pr-14 resize-none overflow-y-auto"
          style={{ minHeight: '44px', maxHeight: '120px' }}
          rows={1}
        />
        <button
          onClick={handleSubmit}
          disabled={!text.trim() || isTyping}
          className="absolute right-1.5 bottom-1.5 p-1.5 btn-primary rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
          title="Invia"
        >
          <Send size={18} />
        </button>
      </div>
    </div>
  );
};

export default DocSearchInputArea;
