import React, { useState, useEffect } from 'react'
import SimpleDropdown from '../dropdowns/SimpleDropdown'
import SaveCleanButtons from '../buttons/SaveCleanButtons'
import { api } from '../../api/api';
import { toast } from 'react-toastify'
import { Globe, X } from 'lucide-react';

interface Message {
  sender: 'user' | 'ai'
  content: string
}

interface Chat {
  id: number | string;
  name: string;
  thread_id: string;
}

interface ApiMessage {
  id: number;
  conversation: string;
  content: string;
  file: string | null;
  created_at: string;
  is_user: boolean;
}

interface ApiChatResponse {
  id: string;
  thread_id: string;
  name: string;
  user: number;
  created_at: string;
  messages: ApiMessage[];
}

interface ChatHeaderProps {
  selectedModel: string;
  setSelectedModel: (model: string) => void;
  searchWebEnabled: boolean;
  onChatSelect: (id: number | string | null, name: string | null, thread_id: string | null) => void;
  selectedChat: { id: number | string; name: string } | null;
  setSelectedChat: React.Dispatch<React.SetStateAction<{ id: number | string; name: string; thread_id: string | null } | null>>;
  saveCleanEnabled: boolean;
  messages: Message[];
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  conversationId: string;
}

const modelDescriptions: Record<string, { name: string, desc: string }> = {
  "GPT-5.2 pro": {
    name: "GPT-5.2 pro:",
    desc: "GPT-5.2 pro is the leading model for encoding, reasoning, and agency tasks across all domains."
  }
}

const ChatHeader: React.FC<ChatHeaderProps> = ({
  onChatSelect,
  selectedChat,
  setSelectedChat,
  saveCleanEnabled,
  setMessages,
  conversationId,
}) => {
  // ...existing code...
  const [chats, setChats] = useState<{ id: number | string; name: string; thread_id: string }[]>([]);
  // const [selectedChat, setSelectedChat] = useState<Chat | null>(null);
  const [openSaveModal, setOpenSaveModal] = useState(false);
  const [openDeleteModal, setOpenDeleteModal] = useState(false);
  const [newChatName, setNewChatName] = useState('');

  const modelOfChat = "GPT-5.2 pro";

  const handleSaveClick = () => {
    setOpenSaveModal(true);
  };

  const handleDeleteClick = (chat: { id: string | number; name: string; thread_id: string } | null) => {
    setSelectedChat(chat);
    setOpenDeleteModal(true);
  };

  const fetchChatConversations = async () => {
    try {
      const response = await api.get<ApiChatResponse[]>("/openai/chat/?only_saved=true");
      console.log(response)
      const chatList: Chat[] = response.data.map((conversation) => ({
        id: conversation.id,
        name: conversation.name,
        thread_id: conversation.thread_id
      }));
      setChats(chatList);
      return chatList;
    } catch (error) {
      console.error("Error fetching conversations:", error);
      return [];
    }
  };

  const handleSaveChat = async (chatName: string) => {
    if (!conversationId) {
      toast.error("Thread non inizializzata!");
      return;
    }
    if (!chatName.trim() || chats.some((chat) => chat.name === chatName)) {
      alert("Nome non valido o già esistente. Scegli un altro nome.");
      return;
    }
    try {
      // Salva conversa/renomeia
      await api.post("/openai/chat/assistant/save-conversation", {
        thread_id: conversationId,
        name: chatName
      });
      toast.success(`Chat "${chatName}" salvata con successo!`);

      const updatedChats = await fetchChatConversations();

      const updatedChat = updatedChats.find(
        (c) => (c.thread_id ?? undefined) === conversationId
      );
      if (updatedChat) {
        setSelectedChat(updatedChat);
        onChatSelect(updatedChat.id, updatedChat.name, updatedChat.thread_id ?? undefined);
      }
      setOpenSaveModal(false);
    } catch (e) {
      toast.error("Errore nel salvataggio della chat.");
      console.error(e);
    }
  };

  const handleDeleteChat = async () => {
    if (selectedChat) {
      try {
        await api.delete(`/openai/chat/${selectedChat.id}/`);
        toast.success(`Chat "${selectedChat.name}" eliminato con successo.`);
        setChats(chats.filter(chat => chat.id !== selectedChat.id));
        setOpenDeleteModal(false);
        setSelectedChat(null);
        onChatSelect(null, null, null);
      } catch (error) {
        console.error('Erro ao deletar o chat:', error);
      }
    } else {
      console.warn('Nenhum chat selecionado para excluir.');
    }
  };

  const handleDropdownSelect = (name: string) => {
    const chat = chats.find(chat => chat.name === name);
    if (chat && onChatSelect) {
      onChatSelect(chat.id, chat.name, chat.thread_id);
      setSelectedChat({ id: chat.id, name: chat.name, thread_id: chat.thread_id });
    }
  };

  useEffect(() => {
    const handleFetchChatConversations = async () => {
      try {
        const chatList = await fetchChatConversations();

        if (chatList) {
          const chatsToRemove = chatList.filter((chat) => chat.name.trim().toLowerCase() === "new chat");

          // Remover esses chats do backend
          for (const chat of chatsToRemove) {
            await removeChat(chat.id);
          }
        }
        // Filtrar chats com o nome 'New Chat'

      } catch (error) {
        console.error('Error fetching conversations:', error);
      }
    };

    const removeChat = async (chatId: string | number) => {
      const response = await api.delete(`/openai/chat/${chatId}/`);

      if (response.status === 204 || response.status === 200) {
        console.log(`Chat ${chatId} excluído.`);
        setChats(prevChats => prevChats.filter(chat => chat.id !== chatId));
        setSelectedChat(null);
        onChatSelect(null, null, null);
      } else {
        console.error(`Erro ao excluir chat ${chatId}:`, response.statusText);
      }

    };

    handleFetchChatConversations();
  }, []);

  return (
    <div className="w-full h-full p-8 flex flex-col animate-fade-in relative max-w-6xl mx-auto">
      <div className="flex justify-between items-center border-b border-slate-300 pb-3 z-10 bg-[#f8fafc] shrink-0">
        <div>
          <h2 className="text-1xl font-bold text-slate-800 flex items-center gap-2">
            Chat Assistant
            <span className="ml-2 text-xs bg-gradient-to-r from-blue-600 to-purple-600 text-white px-2 py-1 rounded font-mono shadow-sm relative group cursor-pointer">
              GPT-5.2 pro
              <span
                className="absolute left-1/2 -translate-x-1/2 mt-2 z-20 hidden group-hover:flex px-3 py-2 bg-white text-slate-800 text-xs rounded-lg shadow-xl border border-slate-200 w-56 text-center break-words font-normal"
                style={{ wordBreak: 'break-word', whiteSpace: 'pre-line', lineHeight: '1.5' }}
              >
                {modelDescriptions[modelOfChat]?.desc || ""}
              </span>
            </span>
          </h2>
          <p className="text-xs text-slate-500 mt-1 flex items-center gap-1">
          <Globe size={10} /> Accesso internet attivo &bull; Ragionamento complesso
          </p>
        </div>

        <div className="flex items-center gap-2">
          {saveCleanEnabled ? (
            <SaveCleanButtons
              showSave={!selectedChat || !selectedChat.id}
              onSave={handleSaveClick}
              onClean={() => {
                setSelectedChat(null);
                onChatSelect(null, null, null);
                setMessages([]);
                // Removido navigate para home, agora só reseta o estado
              }}
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
            <button onClick={() => setOpenSaveModal(false)} className="absolute top-4 right-4 text-slate-500 hover:text-slate-800">
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
            <button onClick={() => setOpenDeleteModal(false)} className="absolute top-4 right-4 text-slate-500 hover:text-slate-800">
              <X size={22} />
            </button>
            <h3 className="text-2xl font-bold text-center text-slate-800 mb-6">Conferma Eliminazione</h3>
            <div className="text-center text-slate-700 mb-4 text-base">
              Vuoi davvero eliminare il chat <strong>{selectedChat?.name}</strong>?<br />
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