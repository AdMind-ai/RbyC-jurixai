import React, { useEffect, useState } from 'react'
import ChatHeader from '../components/ChatPage/ChatHeader'
import ChatMessageList from '../components/ChatPage/ChatMessageList'
import ChatInputArea from '../components/ChatPage/ChatInputArea'

import { api } from '../api/api'
import { fetchWithoutAuth } from '../api/fetchWithoutAuth'
import { toast } from 'react-toastify'

interface Message {
  sender: 'user' | 'ai'
  content: string
  citations?: string[]
}

interface ApiMessage {
  id: number;
  conversation: string;
  content: string;
  file: string | null;
  created_at: string;
  is_user: boolean;
}

// interface ApiChatResponse {
//   id: string;
//   name: string;
//   user: number;
//   created_at: string;
//   messages: ApiMessage[];
// }

const Chat: React.FC = () => {
  const [selectedModel, setSelectedModel] = useState('GPT-5')
  const [messages, setMessages] = useState<Message[]>([])
  const [isTyping, setIsTyping] = useState(false);
  const [isOverview, setIsOverview] = useState(false);
  const [citations, setCitations] = useState<string[]>([])
  const [searchWebEnabled, setSearchWebEnabled] = useState(false)
  const [selectedChat, setSelectedChat] = useState<{ id: number | string; name: string; thread_id: string | null} | null>(null);
  const [conversationId, setConversationId] = useState<string>('');

  useEffect(() => {
    const createConversation = async () => {
      try {
        const resp = await fetchWithoutAuth('/openai/chat/create-conversation/', {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        });
        if (resp.ok) {
          const data = await resp.json();
          setConversationId(data.conversation_id);
        }
      } catch (err) {
        console.error("Erro ao criar nova conversa:", err);
        toast.error("Erro ao criar nova conversa:");
      }
    }
    createConversation();
  }, []);

  const handleChatSelect = async (id: number | string | null, name: string | null, thread_id: string | null ) => {
    if (id && name && thread_id) {
      console.log(`Selected Chat ID: ${id}, Name: ${name}`);
      setSelectedChat({ id, name, thread_id });

      try {
        const response = await api.get(`/openai/chat/${id}`);
        console.log(response.data, citations);

        const messages = response.data.messages.map((message: ApiMessage & { citations?: string[] }) => ({
          sender: message.is_user ? 'user' : 'ai',
          content: message.content,
          citations: message.citations || []
        }));

        setMessages(messages);

      } catch (error) {
        console.error("Error fetching conversations:", error);
      }
    } else {
      setSelectedChat(null);
      setMessages([])
    }

  };

  const handleSendMessage = (message: string, sender: 'user' | 'ai', isStream: boolean = false) => {
    console.log('----------------------------')
    console.log('onsend:', message, '\n', sender, ' - ', isStream);
    if (!isStream) {
      setIsOverview(false);
      if (sender === 'user')
        setMessages(messages => [...messages, { sender, content: message }]);
    } else {
      console.log('isOverview: ', isOverview, 'isTyping: ', isTyping)
      setMessages(messages => {
        const lastMessage = messages[messages.length - 1];
        if (sender === 'ai' && lastMessage?.sender === 'ai') {
          return [...messages.slice(0, -1), { sender: 'ai', content: lastMessage.content + message }];
        } else {
          return [...messages, { sender, content: message }];
        }
      });
    }
    console.log('----------------------------')
  };


  return (
    <div className="flex flex-col items-center justify-center min-h-screen w-full bg-[#f8fafc]">
      {/* Header */}
      <ChatHeader
        conversationId={conversationId}
        selectedModel={selectedModel}
        setSelectedModel={setSelectedModel}
        searchWebEnabled={searchWebEnabled}
        onChatSelect={handleChatSelect}
        selectedChat={selectedChat}
        setSelectedChat={setSelectedChat}
        saveCleanEnabled={messages.length > 0}
        messages={messages}
        setMessages={setMessages}
      />
      <div className="flex-1 relative flex flex-col items-center justify-center h-full w-full relative">
        <div className="w-full max-w-6xl mx-auto px-8 flex flex-col h-full">
          <ChatMessageList
            messages={messages}
            isTyping={isTyping}
            isOverview={isOverview}
            chatColor='#F9F9FB'
          />
          {/* Messages Container */}
          <div className="w-full">
            <ChatInputArea
              conversationId={conversationId}
              onSend={handleSendMessage}
              selectedChat={selectedChat}
              setSelectedChat={setSelectedChat}
              searchWebEnabled={searchWebEnabled}
              setSearchWebEnabled={setSearchWebEnabled}
              setCitations={setCitations}
              setIsOverview={setIsOverview}
              setIsTyping={setIsTyping}
              messages={messages}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default Chat