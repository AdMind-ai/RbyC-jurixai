import React, { useState, useEffect, useCallback } from 'react'
import { toast } from 'react-toastify'
import { Globe, X } from 'lucide-react';
import { ModelId } from '../../types/types'
import {
  chatSessionService,
  SaveChatSessionPayload,
  StoredChatProvider,
} from '../../services/chatSessionService'
import { mapMessagesToStoredPayload } from '../../utils/chatStorage'
import { StoredChatSelection } from '../../types/chat'

interface Message {
  sender: 'user' | 'ai'
  content: string
}

interface Chat {
  id: number | string;
  name: string;
  thread_id: string | null;
  provider: StoredChatProvider;
}

interface ChatHeaderProps {
  selectedModel: ModelId;
  setSelectedModel: (model: ModelId) => void;
  searchWebEnabled: boolean;
  setSearchWebEnabled?: (enabled: boolean) => void;
  onChatSelect: (id: number | string | null, name: string | null) => void;
  selectedChat: StoredChatSelection | null;
  setSelectedChat: React.Dispatch<React.SetStateAction<StoredChatSelection | null>>;
  saveCleanEnabled: boolean;
  messages: Message[];
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  conversationId: string | null;
  onResetConversation?: () => void | Promise<void>;
}

const modelDescriptions: Record<ModelId, { name: string, desc: string, subtitle: string }> = {
  [ModelId.GPT_5_4]: {
    name: 'GPT-5.4',
    desc: 'GPT-5.4 e la scelta principale per ragionamento avanzato, tool usage e automazioni multi-step.',
    subtitle: 'Accesso internet attivo - Ragionamento complesso'
  },
  [ModelId.PERPLEXITY]: {
    name: 'Perplexity',
    desc: 'Perplexity combina ricerca web live e risposte sintetiche con citazioni verificabili in tempo reale.',
    subtitle: 'Ricerca web live - Sintesi con fonti'
  }
}

const ChatHeader: React.FC<ChatHeaderProps> = ({
  selectedModel,
  setSelectedModel,
  searchWebEnabled,
  setSearchWebEnabled,
  onChatSelect,
  selectedChat,
  setSelectedChat,
  saveCleanEnabled,
  messages,
  setMessages,
  conversationId,
  onResetConversation,
}) => {
  const handleCleanConversation = async () => {
    setSelectedChat(null);
    onChatSelect(null, null);
    setMessages([]);
    try {
      await onResetConversation?.();
    } catch (error) {
      console.error('Erro ao reiniciar a conversa:', error);
    }
  };

  const [chats, setChats] = useState<Chat[]>([]);
  const [openSaveModal, setOpenSaveModal] = useState(false);
  const [openDeleteModal, setOpenDeleteModal] = useState(false);
  const [newChatName, setNewChatName] = useState('');
  const [chatPendingDeletion, setChatPendingDeletion] = useState<Chat | null>(null);

  const currentModelInfo = modelDescriptions[selectedModel] ?? modelDescriptions[ModelId.GPT_5_4];
  const modelToProvider: Record<ModelId, StoredChatProvider> = {
    [ModelId.GPT_5_4]: 'gpt',
    [ModelId.PERPLEXITY]: 'perplexity',
  };

  const handleSaveClick = () => {
    setNewChatName(selectedChat?.name ?? '');
    setOpenSaveModal(true);
  };

  const handleDeleteClick = (chat: Chat) => {
    setChatPendingDeletion(chat);
    setOpenDeleteModal(true);
  };

  const fetchChatConversations = useCallback(async () => {
    const provider = modelToProvider[selectedModel];
    try {
      const sessions = await chatSessionService.listSessions(provider);
      const chatList: Chat[] = sessions.map((session) => ({
        id: session.id,
        name: session.title,
        thread_id: session.external_conversation_id ?? null,
        provider: session.provider,
      }));
      setChats(chatList);
      return chatList;
    } catch (error) {
      console.error('Error fetching conversations:', error);
      return [];
    }
  }, [selectedModel]);

  const handleSaveChat = async (chatName: string) => {
    const provider = modelToProvider[selectedModel];
    const activeConversationId = selectedChat?.thread_id ?? conversationId ?? null;
    const requiresConversationId = provider === 'gpt' || provider === 'perplexity';

    if (requiresConversationId && !activeConversationId) {
      toast.error('Thread non inizializzata!');
      return;
    }

    if (!chatName.trim() || chats.some((chat) => chat.name === chatName)) {
      alert("Nome non valido o già esistente. Scegli un altro nome.");
      return;
    }
    try {
      const payload: SaveChatSessionPayload = {
        provider,
        title: chatName,
        display_model: currentModelInfo.name,
        messages: mapMessagesToStoredPayload(messages),
      };

      if (activeConversationId) {
        payload.conversation_id = activeConversationId;
      }

      const savedSession = await chatSessionService.saveSession(payload);
      toast.success(`Chat "${chatName}" salvata con successo!`);

      await fetchChatConversations();

      const normalizedChat = {
        id: savedSession.id,
        name: savedSession.title,
        provider,
        thread_id: savedSession.external_conversation_id ?? null,
      };

      setSelectedChat(normalizedChat);
      onChatSelect(savedSession.id, savedSession.title);
      setOpenSaveModal(false);
      setNewChatName('');
    } catch (e) {
      toast.error("Errore nel salvataggio della chat.");
      console.error(e);
    }
  };

  const handleDeleteChat = async () => {
    if (!chatPendingDeletion) {
      console.warn('Nenhum chat selecionado para excluir.');
      return;
    }

    try {
      await chatSessionService.deleteSession(String(chatPendingDeletion.id));
      toast.success(`Chat "${chatPendingDeletion.name}" eliminata con successo.`);

      setChats((prev) => prev.filter((chat) => chat.id !== chatPendingDeletion.id));

      if (selectedChat && selectedChat.id === chatPendingDeletion.id) {
        setSelectedChat(null);
        onChatSelect(null, null);
      }

      await fetchChatConversations();
    } catch (error) {
      console.error('Erro ao deletar o chat:', error);
      toast.error('Erro ao deletar o chat.');
    } finally {
      setOpenDeleteModal(false);
      setChatPendingDeletion(null);
    }
  };

  const handleDropdownSelect = (name: string) => {
    const chat = chats.find(chat => chat.name === name);
    if (chat && onChatSelect) {
      onChatSelect(chat.id, chat.name);
      setSelectedChat({ id: String(chat.id), name: chat.name, provider: chat.provider, thread_id: chat.thread_id });
    }
  };

  useEffect(() => {
    fetchChatConversations();
  }, [fetchChatConversations]);

  return (
    <div className="bg-white border-b border-slate-100 px-6 py-4 flex items-center justify-between shrink-0">
      <div className="flex items-center">
        <h2 className="text-base font-semibold text-slate-800">Chat Assistant</h2>
      </div>

      <div className="flex bg-slate-100 rounded-xl p-1">
        <button
          onClick={() => setSelectedModel(ModelId.GPT_5_4)}
          className={`px-4 py-1.5 rounded-lg text-sm transition-all duration-200 ${
            selectedModel === ModelId.GPT_5_4
              ? 'bg-white shadow-sm text-[#1e3a8a] font-medium'
              : 'text-slate-400 hover:text-slate-600'
          }`}
        >
          GPT-5.4
        </button>
        <button
          onClick={() => setSelectedModel(ModelId.PERPLEXITY)}
          className={`px-4 py-1.5 rounded-lg text-sm transition-all duration-200 ${
            selectedModel === ModelId.PERPLEXITY
              ? 'bg-white shadow-sm text-[#1e3a8a] font-medium'
              : 'text-slate-400 hover:text-slate-600'
          }`}
        >
          Perplexity
        </button>
      </div>

      <div className="flex items-center gap-4">
        {setSearchWebEnabled && (
          <label className="flex items-center gap-2 cursor-pointer">
            <span className="text-sm text-slate-500">Cerca nel web</span>
            <div className="relative inline-block w-10 h-6">
              <input 
                type="checkbox" 
                className="peer sr-only" 
                checked={searchWebEnabled}
                onChange={(e) => setSearchWebEnabled(e.target.checked)} 
              />
              <div className="w-10 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[#15803d]"></div>
            </div>
          </label>
        )}

        <div className="flex items-center gap-2">
          <select
            className="apple-select text-sm py-1.5 px-3 h-auto min-w-[140px]"
            value={selectedChat ? selectedChat.name : ''}
            onChange={(e) => {
              const name = e.target.value;
              if (name) handleDropdownSelect(name);
            }}
          >
            <option value="" disabled>Seleziona chat...</option>
            {chats.slice().reverse().map(chat => (
              <option key={chat.id} value={chat.name}>{chat.name}</option>
            ))}
          </select>
          {selectedChat && (
            <button 
              onClick={() => handleDeleteClick(selectedChat as Chat)} 
              className="text-slate-400 hover:text-red-500 transition-colors p-1"
              title="Elimina chat selezionata"
            >
              <X size={16} />
            </button>
          )}
        </div>

        {saveCleanEnabled && (
          <div className="flex items-center gap-2">
            {!selectedChat?.id && (
              <button onClick={handleSaveClick} className="btn-secondary py-1.5 px-3 text-sm h-auto">
                Salva
              </button>
            )}
            <button onClick={handleCleanConversation} className="btn-secondary py-1.5 px-3 text-sm h-auto">
              Nuova
            </button>
          </div>
        )}
      </div>

      {openSaveModal && (
        <div className="modal-overlay">
          <div className="modal-box">
            <button onClick={() => { setOpenSaveModal(false); setNewChatName(''); }} className="absolute top-4 right-4 text-slate-400 hover:text-slate-600">
              <X size={20} />
            </button>
            <h3 className="text-xl font-semibold text-slate-800 mb-4 text-center">Salva Chat</h3>
            <p className="text-sm text-slate-500 text-center mb-6">Scegli un nome per la chat:</p>
            <div className="flex justify-center mb-6">
              <input
                type="text"
                value={newChatName}
                onChange={(e) => setNewChatName(e.target.value)}
                className="apple-input w-full"
                placeholder="Nome chat..."
                autoFocus
              />
            </div>
            <div className="flex justify-center">
              <button
                className="btn-primary"
                onClick={() => handleSaveChat(newChatName)}
              >
                Salva
              </button>
            </div>
          </div>
        </div>
      )}

      {openDeleteModal && (
        <div className="modal-overlay">
          <div className="modal-box">
            <button onClick={() => { setOpenDeleteModal(false); setChatPendingDeletion(null); }} className="absolute top-4 right-4 text-slate-400 hover:text-slate-600">
              <X size={20} />
            </button>
            <h3 className="text-xl font-semibold text-slate-800 mb-4 text-center">Conferma Eliminazione</h3>
            <p className="text-sm text-slate-500 text-center mb-6">
              Vuoi davvero eliminare la chat <strong>{chatPendingDeletion?.name}</strong>?<br />
              Una volta eliminata, non sarà possibile recuperarla.
            </p>
            <div className="flex justify-center gap-3">
              <button className="btn-secondary" onClick={() => { setOpenDeleteModal(false); setChatPendingDeletion(null); }}>Annulla</button>
              <button className="btn-danger" onClick={handleDeleteChat}>Elimina</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ChatHeader
