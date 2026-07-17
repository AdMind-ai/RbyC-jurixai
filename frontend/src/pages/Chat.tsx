import React, { useCallback, useEffect, useState } from 'react'
import ChatHeader from '../components/ChatPage/ChatHeader'
import ChatMessageList from '../components/ChatPage/ChatMessageList'
import ChatInputArea from '../components/ChatPage/ChatInputArea'

import { fetchWithoutAuth } from '../api/fetchWithoutAuth'
import { toast } from 'react-toastify'
import { ModelId } from '../types/types'
import { chatSessionService, SaveChatSessionPayload, StoredChatProvider } from '../services/chatSessionService'
import { mapMessagesToStoredPayload } from '../utils/chatStorage'
import { StoredChatSelection } from '../types/chat'

interface Message {
  sender: 'user' | 'ai'
  content: string
  citations?: string[]
}

const providerToModel: Record<StoredChatProvider, ModelId> = {
  gpt: ModelId.GPT_5_4,
  perplexity: ModelId.GPT_5_4,
};

const flattenStoredContent = (content: unknown): string => {
  if (Array.isArray(content)) {
    return content
      .map((part) => {
        if (typeof part === 'string') {
          return part;
        }
        if (part && typeof part === 'object') {
          const maybeText = (part as { text?: string }).text;
          if (typeof maybeText === 'string') {
            return maybeText;
          }
          return JSON.stringify(part);
        }
        return '';
      })
      .filter(Boolean)
      .join('\n\n');
  }

  if (typeof content === 'string') {
    return content;
  }

  if (content && typeof content === 'object') {
    const maybeText = (content as { text?: string }).text;
    if (typeof maybeText === 'string') {
      return maybeText;
    }
    return JSON.stringify(content);
  }

  return '';
};

const Chat: React.FC = () => {
  const [selectedModel, setSelectedModel] = useState<ModelId>(ModelId.GPT_5_4)
  const [messages, setMessages] = useState<Message[]>([])
  const [isTyping, setIsTyping] = useState(false);
  const [isOverview, setIsOverview] = useState(false);
  const [searchWebEnabled, setSearchWebEnabled] = useState(false)
  const [selectedChat, setSelectedChat] = useState<StoredChatSelection | null>(null);
  const [conversationRefs, setConversationRefs] = useState<Record<ModelId, string | null>>({
    [ModelId.GPT_5_4]: null,
  });
  const [shouldPersist, setShouldPersist] = useState(false);

  const updateConversationRef = useCallback(
    (model: ModelId, value: string | null) => {
      setConversationRefs((prev) => ({
        ...prev,
        [model]: value ?? null,
      }));

      setSelectedChat((prev) => {
        if (prev && providerToModel[prev.provider] === model) {
          return {
            ...prev,
            thread_id: value ?? null,
          };
        }
        return prev;
      });
    },
    []
  );

  const requestNewConversation = useCallback(async () => {
    updateConversationRef(ModelId.GPT_5_4, null);
    try {
      const resp = await fetchWithoutAuth('/openai/chat/create-conversation/', {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (!resp.ok) {
        throw new Error(`Failed with status ${resp.status}`);
      }
      const data = await resp.json();
      updateConversationRef(ModelId.GPT_5_4, data.conversation_id);
      return data.conversation_id as string;
    } catch (err) {
      console.error("Erro ao criar nova conversa:", err);
      toast.error("Erro ao criar nova conversa");
      return null;
    }
  }, [updateConversationRef]);

  useEffect(() => {
    requestNewConversation();
  }, [requestNewConversation]);

  useEffect(() => {
    setMessages([]);
    setSelectedChat(null);
  }, [selectedModel]);

  const handleResetConversationContext = useCallback(async () => {
    setMessages([]);
    setSelectedChat(null);
    if (selectedModel === ModelId.GPT_5_4) {
      await requestNewConversation();
    } else {
      updateConversationRef(selectedModel, null);
    }
  }, [selectedModel, requestNewConversation, updateConversationRef]);

  const handleChatSelect = useCallback(
    async (id: number | string | null, name: string | null) => {
      if (id && name) {
        try {
          const session = await chatSessionService.getSession(String(id));

          const normalizedMessages: Message[] = session.messages
            .filter((message) => message.role === 'user' || message.role === 'assistant')
            .map((message): Message => ({
              sender: message.role === 'user' ? 'user' : 'ai',
              content: flattenStoredContent(message.content),
            }));

          setMessages(normalizedMessages);
          const targetModel = providerToModel[session.provider];
          const externalConversationId = session.external_conversation_id ?? null;
          updateConversationRef(targetModel, externalConversationId);

          setSelectedChat({
            id: session.id,
            name: session.title,
            provider: session.provider,
            thread_id: externalConversationId,
          });
        } catch (error) {
          console.error('Error fetching stored conversation:', error);
          toast.error('Erro ao carregar chat salvo.');
        }
      } else {
        setSelectedChat(null);
        setMessages([]);
        updateConversationRef(selectedModel, null);
      }
    },
    [selectedModel, updateConversationRef]
  );

  const handleSendMessage = (message: string, sender: 'user' | 'ai', isStream: boolean = false) => {
    console.log('----------------------------')
    console.log('onsend:', message, '\n', sender, ' - ', isStream);
    if (!isStream) {
      setIsOverview(false);
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

  const persistSelectedChat = useCallback(async () => {
    if (!selectedChat?.id) {
      return;
    }

    const provider = selectedChat.provider;
    const targetModel = providerToModel[provider];
    const conversationId = selectedChat.thread_id ?? conversationRefs[targetModel] ?? null;
    const requiresConversationId = provider === 'gpt';

    if (requiresConversationId && !conversationId) {
      return;
    }

    const payload: SaveChatSessionPayload = {
      provider,
      title: selectedChat.name,
      session_id: selectedChat.id,
      messages: mapMessagesToStoredPayload(messages),
    };

    if (conversationId) {
      payload.conversation_id = conversationId;
    }

    try {
      await chatSessionService.saveSession(payload);
    } catch (error) {
      console.error('Erro ao atualizar chat salvo automaticamente:', error);
    }
  }, [selectedChat, conversationRefs, messages]);

  useEffect(() => {
    if (!shouldPersist) {
      return;
    }
    setShouldPersist(false);
    void persistSelectedChat();
  }, [shouldPersist, persistSelectedChat]);

  const requestAutoPersist = useCallback(() => {
    setShouldPersist(true);
  }, []);

  const activeConversationId = selectedChat?.thread_id ?? conversationRefs[selectedModel] ?? null;

  return (
    <div className="page-root flex flex-col h-full bg-slate-50">
      <ChatHeader
        conversationId={activeConversationId}
        selectedModel={selectedModel}
        setSelectedModel={setSelectedModel}
        searchWebEnabled={searchWebEnabled}
        setSearchWebEnabled={setSearchWebEnabled}
        onChatSelect={handleChatSelect}
        selectedChat={selectedChat}
        setSelectedChat={setSelectedChat}
        saveCleanEnabled={messages.length > 0}
        messages={messages}
        setMessages={setMessages}
        onResetConversation={handleResetConversationContext}
      />
      <div className="flex-1 overflow-hidden relative flex flex-col w-full">
        <ChatMessageList
          messages={messages}
          isTyping={isTyping}
          isOverview={isOverview}
        />
        <ChatInputArea
          conversationId={activeConversationId}
          onSend={handleSendMessage}
          selectedChat={selectedChat}
          setSelectedChat={setSelectedChat}
          searchWebEnabled={searchWebEnabled}
          setSearchWebEnabled={setSearchWebEnabled}
          setIsOverview={setIsOverview}
          setIsTyping={setIsTyping}
          messages={messages}
          selectedModel={selectedModel}
          onConversationIdChange={updateConversationRef}
          onConversationUpdated={requestAutoPersist}
        />
      </div>
    </div>
  );
}

export default Chat
