import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom';
import SimpleDropdown from '../dropdowns/SimpleDropdown'
import SaveCleanButtons from '../buttons/SaveCleanButtons'
import { useTheme } from '@mui/material/styles'
import { api } from '../../api/api';
import { toast } from 'react-toastify'
import {
  Box,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
  IconButton,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Grow
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';

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
  "GPT-5": {
    name: "GPT-5:",
    desc: "GPT-5 is the leading model for encoding, reasoning, and agency tasks across all domains."
  }
}

export const modelMapping: Record<string, string> = {
  "GPT-5": "gpt-5"
};

const ChatHeader: React.FC<ChatHeaderProps> = ({
  selectedModel,
  setSelectedModel,
  searchWebEnabled,
  onChatSelect,
  selectedChat,
  setSelectedChat,
  saveCleanEnabled,
  setMessages,
  conversationId
}) => {
  const navigate = useNavigate();
  const theme = useTheme()
  const [chats, setChats] = useState<{ id: number | string; name: string; thread_id: string }[]>([]);
  // const [selectedChat, setSelectedChat] = useState<Chat | null>(null);
  const [openSaveModal, setOpenSaveModal] = useState(false);
  const [openDeleteModal, setOpenDeleteModal] = useState(false);
  const [newChatName, setNewChatName] = useState('');
  const [hoverModel, setHoverModel] = useState<string | null>(null);

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
      setSelectedChat({ id: chat.id, name: chat.name, thread_id: chat.thread_id});
    }
  };

  useEffect(() => {
    const handleFetchChatConversations = async () => {
      try {
        const chatList = await fetchChatConversations();

        if(chatList){
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
    <Box
      sx={{
        display: 'flex',
        justifyContent: 'space-between',
        marginBottom: '0.2vw',
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 3 }}>
        <Typography variant="h2" sx={{ marginLeft: '1vw' }}>
          ChatGPT
        </Typography>

        <Box
          sx={{
            backgroundColor: theme.palette.primary.light,
            padding: '4px',
            borderRadius: '8px !important',
            display: 'inline-flex',
          }}
        >

          <ToggleButtonGroup
            value={selectedModel}
            exclusive
            onChange={(_, value) => {
              if (!searchWebEnabled && value) setSelectedModel(value);
            }}
            aria-label="model selection"
            sx={{ gap: '4px', maxHeight: '4.1vh' }}
          >
            {Object.keys(modelMapping).map(model => (
              <Box key={model} sx={{ position: 'relative', display: 'inline-block' }}>
                <ToggleButton
                  key={model}
                  value={model}
                  onMouseEnter={() => setHoverModel(model)}
                  onMouseLeave={() => setHoverModel(null)}
                  sx={{
                    mb: 1,
                    textTransform: 'none',
                    fontSize: '14px',
                    maxHeight: '4.1vh',
                    fontWeight: 'regular',
                    color: theme.palette.text.primary,
                    backgroundColor: 'transparent',
                    borderRadius: '8px !important',
                    borderColor: 'transparent !important',
                    padding: '6px 12px',
                    '&.Mui-selected': {
                      backgroundColor: theme.palette.primary.main,
                      color: theme.palette.primary.contrastText,
                      '&:hover': {
                        backgroundColor: theme.palette.primary.main,
                        color: theme.palette.primary.contrastText,
                      },
                    },
                    '&:hover': {
                      backgroundColor: theme.palette.primary.main,
                      color: theme.palette.primary.contrastText,
                    },
                  }}
                >
                  {model}
                </ToggleButton>

                <Grow in={hoverModel === model} timeout={'auto'} unmountOnExit >
                  <Box
                    sx={{
                      position: 'absolute',
                      top: '65%',
                      left: '95%',
                      width: '300px',
                      bgcolor: 'white',
                      border: '1px solid #ccc',
                      borderRadius: 2,
                      boxShadow: '0 2px 10px rgba(0,0,0,0.12)',
                      p: 1,
                      zIndex: 10,
                      mt: 1,
                      pointerEvents: 'none',
                      transformOrigin: 'left top'
                    }}
                  >
                    <Typography variant="body2" sx={{ fontSize: '0.8rem', color: '#333', lineHeight: '1.3' }}>
                      <b>{modelDescriptions[model].name}</b> {modelDescriptions[model].desc}
                    </Typography>
                  </Box>
                </Grow>
              </Box>
            ))}
          </ToggleButtonGroup>
        </Box>
      </Box>

      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        {saveCleanEnabled ? (
          <SaveCleanButtons
            onSave={handleSaveClick}
            onClean={() => {
              setSelectedChat(null);
              onChatSelect(null, null, null);
              setMessages([]);
              navigate('/chat-assistant');
            }}
          />
        ) : null}
        <SimpleDropdown
          // onClick={() => handleDeleteClick(selectedChat)}
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
      </Box>

      {/* Modal para salvar chat */}
      <Dialog open={openSaveModal} onClose={() => setOpenSaveModal(false)}>
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', fontWeight: 'bold', justifyContent: 'center', mt: 2, fontSize: '26px', borderRadius: '16px' }}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            Salva Chat
          </Box>
          <IconButton
            onClick={() => setOpenSaveModal(false)}
            sx={{ position: 'absolute', top: 10, right: 10 }}
          >
            <CloseIcon sx={{ color: '#000' }} />
          </IconButton>
        </DialogTitle>
        <DialogContent sx={{ borderRadius: '16px' }}>
          <DialogContentText sx={{ color: 'black', textAlign: 'center', fontSize: '20px', my: 0.5, mx: 1 }}>
            Scegli un nome per il chat:
          </DialogContentText>
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
            <input
              type="text"
              value={newChatName}
              onChange={(e) => setNewChatName(e.target.value)}
              style={{ width: '80%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
            />
          </Box>
        </DialogContent>
        <DialogActions sx={{ justifyContent: 'center', pb: 2.5, mb: 2, borderRadius: '16px' }}>
          <Button
            variant="contained"
            onClick={() => handleSaveChat(newChatName)}
            sx={{ py: 2.6, borderRadius: '10px' }}
          >
            Salva
          </Button>
        </DialogActions>
      </Dialog>

      {/* Modal para deletar chat */}
      <Dialog open={openDeleteModal} onClose={() => setOpenDeleteModal(false)}>
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', fontWeight: 'bold', justifyContent: 'center', mt: 2, fontSize: '26px', borderRadius: '16px' }}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            Conferma Eliminazione
          </Box>
          <IconButton
            onClick={() => setOpenDeleteModal(false)}
            sx={{ position: 'absolute', top: 10, right: 10 }}
          >
            <CloseIcon sx={{ color: '#000' }} />
          </IconButton>
        </DialogTitle>
        <DialogContent sx={{ borderRadius: '16px' }}>
          <DialogContentText sx={{ color: 'black', textAlign: 'center', fontSize: '20px', my: 0.5, mx: 1 }}>
            Vuoi davvero eliminare il chat {selectedChat?.name}?<br />
            Una volta eliminato, non sarà possibile recuperarlo.
          </DialogContentText>
        </DialogContent>
        <DialogActions sx={{ justifyContent: 'center', pb: 2.5, mb: 2, borderRadius: '16px' }}>
          <Button
            variant="contained"
            onClick={handleDeleteChat}
            sx={{ bgcolor: '#d32f2f', color: '#fff', py: 2.6, borderRadius: '10px', '&:hover': { bgcolor: '#c62828' } }}
          >
            Elimina
          </Button>
        </DialogActions>
      </Dialog>

    </Box>
  )
}

export default ChatHeader