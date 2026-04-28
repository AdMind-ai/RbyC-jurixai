import { useState, useEffect, useRef } from 'react'
import { toast } from 'react-toastify'
import { api } from '../api/api'
import {
  Message,
  Chat,
  ApiMessage,
  ApiChatResponse,
} from '../interfaces/docSearch'

import { fetchWithAuth } from '../api/fetchWithAuth'

export function useDocSearch() {
  // Local source/message types for this hook (adds optional sources to messages)
  type Source = {
    id: string
    title: string
    url: string
    type?: string
  }

  type LocalMessage = Message & { sources?: Source[]; isStreaming?: boolean }

  type StreamEventPayload = {
    type?: string
    request_id?: string
    phase?: string
    status?: string
    message?: string
    text?: string
    delta?: string
    response_text?: string
    documents_urls?: Record<string, string>
  }

  // Citation type inferred from ApiMessage.citations
  type Citation = ApiMessage['citations'] extends Array<infer T>
    ? T
    : { id?: string; title?: string; url?: string; type?: string }

  const [conversationId, setConversationId] = useState<string | null>(null)
  const [messages, setMessages] = useState<LocalMessage[]>([])
  const [isTyping, setIsTyping] = useState(false)
  const [selectedChat, setSelectedChat] = useState<Chat | null>(null)
  const [chats, setChats] = useState<Chat[]>([])
  const [openSaveModal, setOpenSaveModal] = useState(false)
  const [openDeleteModal, setOpenDeleteModal] = useState(false)
  const streamTimerRef = useRef<number | null>(null)
  const streamSequenceRef = useRef(0)
  const progressEntriesRef = useRef<string[]>([])

  // Thread creation: StrictMode-proof
  // const threadCreatedRef = useRef(false);

  useEffect(() => {
    // if (!threadCreatedRef.current) {
    //   threadCreatedRef.current = true;
    //   createThread();
    // }
    fetchChatConversations()

    return () => {
      if (streamTimerRef.current) {
        window.clearTimeout(streamTimerRef.current)
      }
    }
  }, [])

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
      const response = await api.get<ApiChatResponse[]>(
        '/openai/chat/?only_saved=true&is_chat_rag=true'
      )
      const chatList: Chat[] = response.data.map((conversation) => ({
        id: conversation.id,
        name: conversation.name,
        thread_id: conversation.thread_id,
      }))
      setChats(chatList)
      return chatList
    } catch (error) {
      console.error('Error fetching conversations:', error)
      return []
    }
  }

  // 3. SALVAR CHAT (threadId correto sempre!)
  const handleSaveChat = async (chatName: string) => {
    if (!conversationId) {
      toast.error('Thread non inizializzata!')
      return
    }
    if (!chatName.trim() || chats.some((chat) => chat.name === chatName)) {
      alert('Nome non valido o già esistente. Scegli un altro nome.')
      return
    }
    try {
      // Salva conversa/renomeia
      await api.post('/openai/chat/assistant/save-conversation', {
        thread_id: conversationId,
        name: chatName,
        is_chat_rag: true,
      })
      toast.success(`Chat "${chatName}" salvata con successo!`)

      const updatedChats = await fetchChatConversations()

      const updatedChat = updatedChats.find(
        (c) => (c.thread_id ?? undefined) === conversationId
      )
      if (updatedChat) {
        setSelectedChat(updatedChat)
        handleChatSelect(
          updatedChat.id,
          updatedChat.name,
          updatedChat.thread_id ?? undefined
        )
      }
      setOpenSaveModal(false)
    } catch (e) {
      toast.error('Errore nel salvataggio della chat.')
      console.error(e)
    }
  }

  // 4. DELETAR CHAT
  const handleDeleteChat = async () => {
    if (selectedChat) {
      try {
        await api.delete(`/openai/chat/${selectedChat.id}/`)
        toast.success(`Chat "${selectedChat.name}" eliminato con successo.`)
        setChats(chats.filter((chat) => chat.id !== selectedChat.id))
        setOpenDeleteModal(false)
        setSelectedChat(null)
        handleChatSelect(null, null)
      } catch (error) {
        console.error('Erro ao deletar o chat:', error)
      }
    } else {
      console.warn('Nenhum chat selecionado para excluir.')
    }
  }

  // 5. SELECIONAR CHAT - 🚩 ATUALIZA TAMBÉM O THREAD_ID
  const handleDropdownSelect = (name: string | string[]) => {
    const chat = chats.find((chat) => chat.name === name)
    if (chat) {
      handleChatSelect(chat.id, chat.name, chat.thread_id ?? undefined)
      setSelectedChat({
        id: chat.id,
        name: chat.name,
        thread_id: chat.thread_id,
      })
    }
  }

  // 6. AO TROCAR DE CHAT, SINCRONIZE O threadId!
  const handleChatSelect = async (
    id: number | string | null,
    name: string | null,
    chatThreadId?: string
  ) => {
    if (streamTimerRef.current) {
      window.clearTimeout(streamTimerRef.current)
    }
    progressEntriesRef.current = []
    if (id && name) {
      setSelectedChat({ id, name, thread_id: chatThreadId })
      setConversationId(chatThreadId ?? null)
      try {
        const response = await api.get<ApiChatResponse>(`/openai/chat/${id}`)
        const messages: LocalMessage[] = response.data.messages.map(
          (message: ApiMessage) => ({
            sender: message.is_user ? 'user' : 'ai',
            content: message.content,
            isStreaming: false,
            // Load saved citations/sources if present
            sources: Array.isArray(message.citations)
                ? message.citations.map((c: Citation) => ({
                    id: c.id || `${message.id || 0}-${c.title || 'file'}`,
                    title: c.title || 'file',
                    url: c.url || '',
                    type: c.type || '',
                  }))
                : [],
          })
        )
        setMessages(messages)
      } catch (error) {
        console.error('Error fetching conversations:', error)
      }
    } else {
      setSelectedChat(null)
      setConversationId(null)
      setMessages([])
    }
  }

  const normalizeDocumentsToSources = (
    documents: Record<string, string>
  ): Source[] =>
    Object.entries(documents).map(([key, url], idx): Source => {
      const parts = String(key).split('/')
      const filename = parts[parts.length - 1] || key
      const extMatch = filename.match(/\.([0-9a-zA-Z]+)(?:\?|$)/)
      const ext = extMatch ? extMatch[1].toLowerCase() : ''
      return {
        id: `${idx}-${filename}`,
        title: filename,
        url: String(url || ''),
        type: ext,
      }
    })

  const upsertAssistantMessage = (content: string, sources: Source[] = []) => {
    setMessages((currentMessages) => {
      if (
        currentMessages.length > 0 &&
        currentMessages[currentMessages.length - 1].sender === 'ai'
      ) {
        return [
          ...currentMessages.slice(0, -1),
          {
            ...currentMessages[currentMessages.length - 1],
            content,
            sources,
            isStreaming: false,
          },
        ]
      }
      return [...currentMessages, { sender: 'ai', content, sources, isStreaming: false }]
    })
  }

  const setAssistantMessageState = (
    content: string,
    sources: Source[] = [],
    isStreaming = false
  ) => {
    setMessages((currentMessages) => {
      if (
        currentMessages.length > 0 &&
        currentMessages[currentMessages.length - 1].sender === 'ai'
      ) {
        return [
          ...currentMessages.slice(0, -1),
          {
            ...currentMessages[currentMessages.length - 1],
            content,
            sources,
            isStreaming,
          },
        ]
      }

      return [
        ...currentMessages,
        { sender: 'ai', content, sources, isStreaming },
      ]
    })
  }

  const animateAssistantMessage = (
    targetContent: string,
    options?: {
      sources?: Source[]
      preservePrefix?: boolean
      initialContent?: string
      keepStreaming?: boolean
      charsPerStep?: number
      intervalMs?: number
    }
  ) => {
    const {
      sources = [],
      preservePrefix = true,
      initialContent = '',
      keepStreaming = true,
      charsPerStep = 3,
      intervalMs = 18,
    } = options || {}

    if (streamTimerRef.current) {
      window.clearTimeout(streamTimerRef.current)
    }

    streamSequenceRef.current += 1
    const sequence = streamSequenceRef.current

    let baseContent = initialContent
    setMessages((currentMessages) => {
      const lastMessage =
        currentMessages.length > 0
          ? currentMessages[currentMessages.length - 1]
          : null

      if (!baseContent && lastMessage?.sender === 'ai' && preservePrefix) {
        const existing = lastMessage.content || ''
        if (targetContent.startsWith(existing)) {
          baseContent = existing
        }
      }

      if (lastMessage?.sender === 'ai') {
        return [
          ...currentMessages.slice(0, -1),
          {
            ...lastMessage,
            content: baseContent,
            sources,
            isStreaming: true,
          },
        ]
      }

      return [
        ...currentMessages,
        { sender: 'ai', content: baseContent, sources, isStreaming: true },
      ]
    })

    let currentLength = baseContent.length

    const tick = () => {
      if (sequence !== streamSequenceRef.current) {
        return
      }

      if (currentLength >= targetContent.length) {
        setAssistantMessageState(targetContent, sources, keepStreaming)
        return
      }

      currentLength = Math.min(currentLength + charsPerStep, targetContent.length)
      setAssistantMessageState(
        targetContent.slice(0, currentLength),
        sources,
        true
      )
      streamTimerRef.current = window.setTimeout(tick, intervalMs)
    }

    tick()
  }

  const parseSseBlock = (
    block: string
  ): { eventName: string; payload: StreamEventPayload } | null => {
    const lines = block
      .split('\n')
      .map((line) => line.trimEnd())
      .filter(Boolean)

    if (lines.length === 0) return null

    let eventName = 'message'
    const dataLines: string[] = []

    for (const line of lines) {
      if (line.startsWith('event:')) {
        eventName = line.slice('event:'.length).trim()
      } else if (line.startsWith('data:')) {
        dataLines.push(line.slice('data:'.length).trim())
      }
    }

    if (dataLines.length === 0) return null

    try {
      return {
        eventName,
        payload: JSON.parse(dataLines.join('\n')) as StreamEventPayload,
      }
    } catch (error) {
      console.error('Error parsing SSE block:', error, block)
      return null
    }
  }

  const handleSendMessage = async (message: string) => {
    setIsTyping(true)
    progressEntriesRef.current = []
    setMessages((msgs) => [...msgs, { sender: 'user', content: message }])

    try {
      let streamedAnswer = ''

      const res = await fetchWithAuth('/openai/chat/assistant/send-message-stream', {
        method: 'POST',
        body: JSON.stringify({ thread_id: conversationId, content: message }),
        headers: { 'Content-Type': 'application/json' },
      })

      if (!res.ok) {
        const txt = await res.text().catch(() => '')
        throw new Error(`Server error: ${res.status} ${txt}`)
      }

      if (!res.body) {
        throw new Error('Streaming response body is not available')
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      const appendProgressEntry = (entry: string) => {
        const normalizedEntry = entry.trim()
        if (!normalizedEntry) return

        const currentEntries = progressEntriesRef.current
        if (currentEntries[currentEntries.length - 1] === normalizedEntry) {
          return
        }

        const nextEntries = [...currentEntries, normalizedEntry]
        const nextContent = nextEntries.join('\n\n')
        const previousContent = currentEntries.join('\n\n')
        progressEntriesRef.current = nextEntries

        animateAssistantMessage(nextContent, {
          preservePrefix:
            Boolean(previousContent) && nextContent.startsWith(previousContent),
          initialContent: previousContent,
          keepStreaming: true,
          charsPerStep: 4,
          intervalMs: 20,
        })
      }

      while (true) {
        const { value, done } = await reader.read()
        if (done) {
          const trailingChunk = parseSseBlock(buffer)
          if (trailingChunk?.eventName === 'answer_completed') {
            const responseText = trailingChunk.payload.response_text || ''
            const documents = trailingChunk.payload.documents_urls || {}
            const sources = normalizeDocumentsToSources(documents)
            upsertAssistantMessage(responseText, sources)
          }
          break
        }

        buffer += decoder.decode(value, { stream: true })
        const chunks = buffer.split('\n\n')
        buffer = chunks.pop() || ''

        for (const chunk of chunks) {
          const parsed = parseSseBlock(chunk)
          if (!parsed) continue

          const { eventName, payload } = parsed

          if (payload.request_id && !conversationId) {
            setConversationId(payload.request_id)
          }

          if (eventName === 'execution_event') {
            setIsTyping(false)
            continue
          }

          if (eventName === 'narration_event') {
            if (payload.text && streamedAnswer.length === 0) {
              setIsTyping(false)
              appendProgressEntry(payload.text)
            }
            continue
          }

          if (eventName === 'answer_started') {
            streamedAnswer = ''
            progressEntriesRef.current = []
            setIsTyping(false)
            if (streamTimerRef.current) {
              window.clearTimeout(streamTimerRef.current)
            }
            setAssistantMessageState('', [], true)
            continue
          }

          if (eventName === 'answer_delta') {
            streamedAnswer += payload.delta || ''
            setIsTyping(false)
            setAssistantMessageState(streamedAnswer, [], true)
            continue
          }

          if (eventName === 'answer_completed') {
            const responseText = payload.response_text || ''
            const documents = payload.documents_urls || {}
            const sources = normalizeDocumentsToSources(documents)
            setIsTyping(false)
            if (streamTimerRef.current) {
              window.clearTimeout(streamTimerRef.current)
            }
            setAssistantMessageState(responseText, sources, false)
            continue
          }

          if (eventName === 'error') {
            throw new Error(
              payload.message ||
                payload.text ||
                payload.response_text ||
                'Streaming error'
            )
          }
        }
      }
    } catch (e) {
      if (streamTimerRef.current) {
        window.clearTimeout(streamTimerRef.current)
      }
      progressEntriesRef.current = []
      toast.error("Errore nell'invio del messaggio.")
      console.log(e)
    } finally {
      setIsTyping(false)
    }
  }

  const handleDeleteClick = (chat: Chat | null) => {
    setSelectedChat(chat)
    setOpenDeleteModal(true)
  }

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
  }
}
