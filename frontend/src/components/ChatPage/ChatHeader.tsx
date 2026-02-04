import React, { useState, useEffect, useCallback } from 'react'
import SimpleDropdown from '../dropdowns/SimpleDropdown'
import SaveCleanButtons from '../buttons/SaveCleanButtons'
import { toast } from 'react-toastify'
import { Globe, X } from 'lucide-react';
import ModelSelector from './ModelSelector'
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
  [ModelId.GPT_5_2]: {
    name: 'GPT-5.2 Pro',
    desc: 'GPT-5.2 Pro è la scelta principale per ragionamento avanzato, tool usage e automazioni multi-step.',
    subtitle: 'Accesso internet attivo - Ragionamento complesso'
  },
  [ModelId.GEMINI_3_PRO]: {
    name: 'Gemini 3 Pro Preview',
    desc: 'Gemini 3 Pro offre contesto esteso, multimodalità avanzata e gestione affidabile di documenti lunghi.',
    subtitle: 'Analisi multimodale - Contesto esteso'
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

  // ...existing code...
  const [chats, setChats] = useState<Chat[]>([]);
  const [openSaveModal, setOpenSaveModal] = useState(false);
  const [openDeleteModal, setOpenDeleteModal] = useState(false);
  const [newChatName, setNewChatName] = useState('');
  const [chatPendingDeletion, setChatPendingDeletion] = useState<Chat | null>(null);

  const currentModelInfo = modelDescriptions[selectedModel] ?? modelDescriptions[ModelId.GPT_5_2];
  const modelToProvider: Record<ModelId, StoredChatProvider> = {
    [ModelId.GPT_5_2]: 'gpt',
    [ModelId.GEMINI_3_PRO]: 'gemini',
    [ModelId.PERPLEXITY]: 'perplexity',
  };

  const handleSaveClick = () => {
    setNewChatName(selectedChat?.name ?? '');
    setOpenSaveModal(true);
  };

  const handleDeleteClick = (chat: Chat | null) => {
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
    <div className="w-full h-full p-8 flex flex-col animate-fade-in relative max-w-6xl mx-auto">
      <div className="flex justify-between items-center border-b border-slate-300 pb-3 z-10 bg-[#f8fafc] shrink-0 mt-16">
        <div>
          <h2 className="text-1xl font-bold text-slate-800 flex items-center gap-2">
            Chat Assistant
            
          </h2>
          <p className="text-xs text-slate-500 mt-1 flex items-center gap-1">
            <Globe size={10} /> Accesso internet attivo &bull; Ragionamento complesso
          </p>
        </div>
      <ModelSelector currentModel={selectedModel} onSelectModel={setSelectedModel} />

        <div className="flex items-center gap-2">
          {saveCleanEnabled ? (
            <SaveCleanButtons
              showSave={!selectedChat || !selectedChat.id}
              onSave={handleSaveClick}
              onClean={handleCleanConversation}
            />
          ) : null}
          <SimpleDropdown
            title="Chat salvate"
            options={chats.slice().reverse().map(chat => chat.name)}
            onSelect={handleDropdownSelect}
            selectedValue={selectedChat ? selectedChat.name : ''}
            isDeleteItems
            onDeleteItem={(name) => {
              const chat = chats.find(c => c.name === name);
              if (chat) handleDeleteClick(chat);
            }}
          />
        </div>
      </div>

      {/* Modal para salvar chat - Tailwind */}
      {openSaveModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 animate-fade-in">
          <div className="bg-white rounded-xl shadow-2xl p-8 w-full max-w-md border border-slate-200 relative">
            <button onClick={() => { setOpenSaveModal(false); setNewChatName(''); }} className="absolute top-4 right-4 text-slate-500 hover:text-slate-800">
              <X size={22} />
            </button>
            <h3 className="text-2xl font-bold text-center text-slate-800 mb-6">Salva Chat</h3>
            <div className="text-center text-slate-700 mb-4 text-base">Scegli un nome per il chat:</div>
            <div className="flex justify-center mt-2">
              <input
                type="text"
                value={newChatName}
                onChange={(e) => setNewChatName(e.target.value)}
                className="w-4/5 p-2 rounded border border-slate-300 text-slate-700 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none"
              />
            </div>
            <div className="flex justify-center gap-2 mt-8">
              <button
                onClick={() => handleSaveChat(newChatName)}
                className="py-2 px-8 bg-blue-600 text-white font-bold rounded-lg hover:bg-blue-700 transition-colors"
              >
                Salva
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal para deletar chat - Tailwind */}
      {openDeleteModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 animate-fade-in">
          <div className="bg-white rounded-xl shadow-2xl p-8 w-full max-w-md border border-slate-200 relative">
            <button onClick={() => { setOpenDeleteModal(false); setChatPendingDeletion(null); }} className="absolute top-4 right-4 text-slate-500 hover:text-slate-800">
              <X size={22} />
            </button>
            <h3 className="text-2xl font-bold text-center text-slate-800 mb-6">Conferma Eliminazione</h3>
            <div className="text-center text-slate-700 mb-4 text-base">
              Vuoi davvero eliminare il chat <strong>{chatPendingDeletion?.name}</strong>?<br />
              Una volta eliminato, non sarà possibile recuperarlo.
            </div>
            <div className="flex justify-center gap-2 mt-8">
              <button
                onClick={handleDeleteChat}
                className="py-2 px-8 bg-red-600 text-white font-bold rounded-lg hover:bg-red-700 transition-colors"
              >
                Elimina
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ChatHeader