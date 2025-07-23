import { useState, useEffect } from "react";
import { toast } from "react-toastify";
import { api } from "../api/api";
import {
  Message,
  Chat,
  ApiMessage,
  ApiChatResponse,
} from "../interfaces/docSearch";

export function useDocSearch() {
  const [selectedModel, setSelectedModel] = useState("GPT-4.1");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [isOverview, setIsOverview] = useState(false);
  const [citations, setCitations] = useState<string[]>([]);
  const [searchWebEnabled, setSearchWebEnabled] = useState(false);
  const [selectedChat, setSelectedChat] = useState<Chat | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string[] | string>([]);

  const [chats, setChats] = useState<Chat[]>([]);
  const [openSaveModal, setOpenSaveModal] = useState(false);
  const [openDeleteModal, setOpenDeleteModal] = useState(false);
  const [newChatName, setNewChatName] = useState("");

  // fetch chats on mount
  useEffect(() => {
    fetchChatConversations();
    // eslint-disable-next-line
  }, []);

  useEffect(() => {
    if (searchWebEnabled) setSelectedModel("GPT-4o");
  }, [searchWebEnabled]);

  const fetchChatConversations = async () => {
    try {
      const response = await api.get("/openai/chat/");
      const chatList: Chat[] = response.data.map((conversation: ApiChatResponse) => ({
        id: conversation.id,
        name: conversation.name,
      }));

      setChats(chatList);

      // remove chats "New Chat"
      const chatsToRemove = chatList.filter((chat) => chat.name === "New Chat");
      for (const chat of chatsToRemove) {
        await removeChat(chat.id);
      }
    } catch (error) {
      console.error("Error fetching conversations:", error);
    }
  };

  const removeChat = async (chatId: string | number) => {
    const response = await api.delete(`/openai/chat/${chatId}/`);
    if (response.status === 204 || response.status === 200) {
      setChats((prevChats) => prevChats.filter((chat) => chat.id !== chatId));
      setSelectedChat(null);
      handleChatSelect(null, null);
    } else {
      console.error(`Erro ao excluir chat ${chatId}:`, response.statusText);
    }
  };

  const handleSaveClick = () => setOpenSaveModal(true);

  const handleDeleteClick = (chat: Chat | null) => {
    setSelectedChat(chat);
    setOpenDeleteModal(true);
  };

  const handleSaveChat = async () => {
    if (!newChatName.trim() || chats.some((chat) => chat.name === newChatName)) {
      alert("Nome inválido ou já existe. Escolha outro.");
      return;
    }

    if (selectedChat) {
      const oldChat = selectedChat;
      const newChat = { id: selectedChat.id, name: newChatName };

      try {
        await api.put(`/openai/chat/${selectedChat.id}/`, {
          name: newChatName,
        });

        setChats(chats.map((chat) => (chat.id === selectedChat.id ? newChat : chat)));
        setSelectedChat(newChat);
        handleChatSelect(newChat.id, newChat.name);
        toast.success(`Chat ${oldChat.name} aggiornato al nome "${newChat.name}"`);
      } catch (error) {
        console.error("Erro ao salvar o chat:", error);
      }
    } else {
      try {
        const response = await api.post("/openai/chat/", {
          name: newChatName,
          messages: messages.map((msg) => ({
            content: msg.content,
            is_user: msg.sender === "user",
            file: null,
          })),
        });
        const newChat: Chat = { id: response.data.id, name: response.data.name };

        setChats([...chats, newChat]);
        setSelectedChat(newChat);
        handleChatSelect(newChat.id, newChat.name);

        toast.success(`Nuova chat "${newChatName}" creata con successo.`);
      } catch (error) {
        console.error("Erro ao criar nova chat:", error);
      }
    }

    setOpenSaveModal(false);
    setNewChatName("");
  };

  const handleDeleteChat = async () => {
    if (selectedChat) {
      try {
        await api.delete(`/openai/chat/${selectedChat.id}/`);
        toast.success(`Chat "${selectedChat.name}" eliminato con successo.`);
        setChats(chats.filter((chat) => chat.id !== selectedChat.id));
        setOpenDeleteModal(false);
        setSelectedChat(null);
        handleChatSelect(null, null);
      } catch (error) {
        console.error("Erro ao deletar o chat:", error);
      }
    } else {
      console.warn("Nenhum chat selecionado para excluir.");
    }
  };

  const handleDropdownSelect = (name: string | string[]) => {
    const chat = chats.find((chat) => chat.name === name);
    if (chat && handleChatSelect) {
      handleChatSelect(chat.id, chat.name);
      setSelectedChat({ id: chat.id, name: chat.name });
    }
  };

  const handleChatSelect = async (id: number | string | null, name: string | null) => {
    if (id && name) {
      setSelectedChat({ id, name });
      try {
        const response = await api.get(`/openai/chat/${id}`);
        const messages = response.data.messages.map(
          (message: ApiMessage & { citations?: string[] }) => ({
            sender: message.is_user ? "user" : "ai",
            content: message.content,
            citations: message.citations || [],
          })
        );
        setMessages(messages);
      } catch (error) {
        console.error("Error fetching conversations:", error);
      }
    } else {
      setSelectedChat(null);
      setMessages([]);
    }
  };

  const handleSendMessage = (
    message: string,
    sender: "user" | "ai",
    isStream: boolean = false
  ) => {
    if (!isStream) {
      setIsOverview(false);
      if (sender === "user")
        setMessages((messages) => [...messages, { sender, content: message }]);
    } else {
      setMessages((messages) => {
        const lastMessage = messages[messages.length - 1];
        if (sender === "ai" && lastMessage?.sender === "ai") {
          return [
            ...messages.slice(0, -1),
            { sender: "ai", content: lastMessage.content + message },
          ];
        } else {
          return [...messages, { sender, content: message }];
        }
      });
    }
  };


  return {
    selectedModel,
    setSelectedModel,
    messages,
    setMessages,
    isTyping,
    setIsTyping,
    isOverview,
    setIsOverview,
    citations,
    setCitations,
    searchWebEnabled,
    setSearchWebEnabled,
    selectedChat,
    setSelectedChat,
    selectedCategory,
    setSelectedCategory,
    chats,
    setChats,
    openSaveModal,
    setOpenSaveModal,
    openDeleteModal,
    setOpenDeleteModal,
    newChatName,
    setNewChatName,
    handleSaveClick,
    handleDeleteClick,
    handleSaveChat,
    handleDeleteChat,
    handleDropdownSelect,
    handleChatSelect,
    handleSendMessage,
  };
}