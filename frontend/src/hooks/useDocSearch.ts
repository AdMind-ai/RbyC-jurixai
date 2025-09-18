import { useState, useEffect } from "react";
import { toast } from "react-toastify";
import { api } from "../api/api";
import {
  Message,
  Chat,
  ApiMessage,
  ApiChatResponse,
} from "../interfaces/docSearch";

import { fetchWithAuth } from '../api/fetchWithAuth'

export function useDocSearch() {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [selectedChat, setSelectedChat] = useState<Chat | null>(null);
  const [chats, setChats] = useState<Chat[]>([]);
  const [openSaveModal, setOpenSaveModal] = useState(false);
  const [openDeleteModal, setOpenDeleteModal] = useState(false);

  // Thread creation: StrictMode-proof
  // const threadCreatedRef = useRef(false);

  useEffect(() => {
    // if (!threadCreatedRef.current) {
    //   threadCreatedRef.current = true;
    //   createThread();
    // }
    fetchChatConversations();
  }, []);

  // 1. CRIAR NOVA THREAD
  // const createThread = async () => {
  //   try {
  //     const res = await api.post<{ threadId: string }>("/openai/chat/assistant/thread");
  //     setThreadId(res.data.threadId);
  //   } catch (err) {
  //     toast.error("Thread non inizializzata!"); 
  //     console.log(err)
  //   }
  // };

  // 2. BUSCAR TODAS AS CONVERSAS
  const fetchChatConversations = async () => {
    try {
      const response = await api.get<ApiChatResponse[]>("/openai/chat/?only_saved=true&is_chat_rag=true");
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

  // 3. SALVAR CHAT (threadId correto sempre!)
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
        name: chatName,
        is_chat_rag: true
      });
      toast.success(`Chat "${chatName}" salvata con successo!`);

      const updatedChats = await fetchChatConversations();

      const updatedChat = updatedChats.find(
        (c) => (c.thread_id ?? undefined) === conversationId
      );
      if (updatedChat) {
        setSelectedChat(updatedChat);
        handleChatSelect(updatedChat.id, updatedChat.name, updatedChat.thread_id ?? undefined);
      }
      setOpenSaveModal(false);
    } catch (e) {
      toast.error("Errore nel salvataggio della chat.");
      console.error(e);
    }
  };

  // 4. DELETAR CHAT
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

  // 5. SELECIONAR CHAT - 🚩 ATUALIZA TAMBÉM O THREAD_ID
  const handleDropdownSelect = (name: string | string[]) => {
    const chat = chats.find((chat) => chat.name === name);
    if (chat) {
      handleChatSelect(chat.id, chat.name, chat.thread_id ?? undefined);
      setSelectedChat({ id: chat.id, name: chat.name, thread_id: chat.thread_id });
    }
  };

  // 6. AO TROCAR DE CHAT, SINCRONIZE O threadId!
  const handleChatSelect = async (
    id: number | string | null,
    name: string | null,
    chatThreadId?: string
  ) => {
    if (id && name) {
      setSelectedChat({ id, name, thread_id: chatThreadId });
      setConversationId(chatThreadId ?? null);
      try {
        const response = await api.get<ApiChatResponse>(`/openai/chat/${id}`);
        const messages: Message[] = response.data.messages.map(
          (message: ApiMessage) => ({
            sender: message.is_user ? "user" : "ai",
            content: message.content,
          })
        );
        setMessages(messages);
      } catch (error) {
        console.error("Error fetching conversations:", error);
      }
    } else {
      setSelectedChat(null);
      setConversationId(null);
      setMessages([]);
    }
  };

  const handleSendMessage = async (message: string) => {

    setIsTyping(true);
    setMessages((msgs) => [...msgs, { sender: "user", content: message }]);

    try {
      const res = await fetchWithAuth("/openai/chat/assistant/send-message", {
        method: "POST",
        body: JSON.stringify({ thread_id: conversationId, content: message }),
        // Content-Type definido auto pra JSON
      });
      if (!res.body) throw new Error("Nessuna risposta dal server!");
      setIsTyping(false);
      const reader = res.body.getReader();
      let done, value;
      while (true) {
        ({ done, value } = await reader.read());
        if (done) break;
        const chunk = new TextDecoder().decode(value);
        setMessages((msgs) => {
          if (msgs.length && msgs[msgs.length - 1].sender === "ai") {
            return [
              ...msgs.slice(0, -1),
              { sender: "ai", content: msgs[msgs.length - 1].content + chunk },
            ];
          } else {
            return [...msgs, { sender: "ai", content: chunk }];
          }
        });
      }
    } catch (e) {
      toast.error("Errore nell'invio del messaggio.");
      console.log(e)
    }

    if (!conversationId) {
      try {
        const res = await api.get("/openai/chat/assistant/thread");
        const threads = res.data;
        if (threads.length > 0) {
          setConversationId(threads[0].thread_id);
        } else {
          toast.error("Nenhuma thread encontrada!");
        }
      } catch (err) {
        toast.error("Thread non inizializzata!");
        console.log(err)
      }
      return;
    }
    setIsTyping(false);
  };

  const handleDeleteClick = (chat: Chat | null) => {
    setSelectedChat(chat);
    setOpenDeleteModal(true);
  };

  return {
    messages,
    setMessages,
    isTyping,
    setIsTyping,
    conversationId,
    setConversationId,
    selectedChat,
    setSelectedChat,
    chats,
    setChats,
    openSaveModal,
    setOpenSaveModal,
    openDeleteModal,
    setOpenDeleteModal,
    handleSaveClick: () => setOpenSaveModal(true),
    handleDeleteClick,
    handleSaveChat,
    handleDeleteChat,
    handleDropdownSelect,
    handleChatSelect,
    handleSendMessage,
    // createThread,
  };
}