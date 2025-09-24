import { useState, useRef } from 'react'
import {
  Box,
  Button,
  Typography,
  CircularProgress,
  IconButton,
  TextField
} from '@mui/material'
import { toast } from 'react-toastify'
import SendIcon from '@mui/icons-material/Send'
import CloudUploadIcon from '@mui/icons-material/CloudUpload'
import UploadableTextArea from '../upload-components/UploadableTextArea'
import { fetchWithAuth } from '../../api/fetchWithAuth'
import ChatMessageList from '../ChatPage/ChatMessageList'

interface Message {
  sender: 'user' | 'ai';
  content: string;
  citations?: string[];
}

const DocCheck = () => {
  const [isLoading, setIsLoading] = useState(false)
  const [isOverview, setIsOverview] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [isChatOpen, setIsChatOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [conversationId, setConversationId] = useState<string | null>(null)
  const eventSourceRef = useRef<EventSource | null>(null)

  const [isTyping, setIsTyping] = useState(false)

  const handleFileUpload = (f: File | File[]) => {
    const first = Array.isArray(f) ? f[0] : f
    setFile(first)
  }

  const handleClearFileUpload = () => {
    setFile(null)
  }

  const handleAnalyze = async () => {
    if (!file) return
    setIsLoading(true)

    try {
      const convRes = await fetchWithAuth("/openai/chat/create-conversation/", { method: "POST" })
      const convData = await convRes.json()
      const newConversationId = convData.conversation_id
      setConversationId(newConversationId)

      setIsChatOpen(true)
      setMessages([])
      setIsTyping(true)
      
      const formData = new FormData()
      formData.append("file", file)
      formData.append("conversation_id", newConversationId)

      const res = await fetchWithAuth("/check-compliance", { method: "POST", body: formData })
      const reader = res.body?.getReader()
      const decoder = new TextDecoder()
      let fullMessage = ""
      
      setIsOverview(true) 
      while (true) {
        const { done, value } = await reader!.read()
        if (done) break
        const chunk = decoder.decode(value)
        fullMessage += chunk

        setMessages(prev => {
          if (prev.length > 0 && prev[prev.length - 1].sender === "ai") {
            return [...prev.slice(0, -1), { sender: "ai", content: fullMessage }]
          }
          return [...prev, { sender: "ai", content: fullMessage }]
        })
      }

      setIsTyping(false)
    } catch (err) {
      console.log(err)
      toast.error("Errore durante l'invio del documento o la lettura del flusso")
    } finally {
      setIsLoading(false)
      setIsOverview(false)
    }
  }

  const handleSend = async () => {
    if (!input.trim() || !conversationId) return

    const userMsg = { sender: "user" as const, content: input }
    setMessages(prev => [...prev, userMsg])
    setInput("")
    setIsTyping(true)

    try {
      const formData = new FormData()
      formData.append("conversation_id", conversationId)
      formData.append("input_text", input)
      const res = await fetchWithAuth("/check-compliance", { method: "POST", body: formData })
      const reader = res.body?.getReader()
      const decoder = new TextDecoder()
      let fullMessage = ""

      setIsOverview(true)
      while (true) {
        const { done, value } = await reader!.read()
        if (done) break
        const chunk = decoder.decode(value)
        fullMessage += chunk

        setMessages(prev => {
          if (prev.length > 0 && prev[prev.length - 1].sender === "ai") {
            return [...prev.slice(0, -1), { sender: "ai", content: fullMessage }]
          }
          return [...prev, { sender: "ai", content: fullMessage }]
        })
      }

      setIsTyping(false)
      setIsOverview(false)
    } catch (err) {
      console.log(err)
      toast.error("Errore durante l'invio del messaggio")
      setIsTyping(false)
    }
  }


  const handleNewDocument = () => {
    setFile(null)
    setMessages([])
    setIsChatOpen(false)
    setConversationId(null)
    eventSourceRef.current?.close()
    eventSourceRef.current = null
  }

  return (
    <Box sx={{
      height: "100%",
      width: "100%",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center"
    }}>
      {!isChatOpen ? (
        <>
          <Box sx={{ mb: 4, textAlign: "center" }}>
            <Typography variant="body1" color="text.secondary" maxWidth={420} fontSize={19}>
              Carica un documento per l'analisi di conformità.
              Il sistema verificherà la conformità in base alle regole interne.
            </Typography>
          </Box>

          <Box sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 3,
            p: 5,
            width: 460,
            borderRadius: 4,
            textAlign: 'center',
            bgcolor: "#fff",
            boxShadow: "0px 4px 12px rgba(0,0,0,0.08)"
          }}>
            <CloudUploadIcon sx={{ fontSize: 70, color: 'primary.main' }} />
            <UploadableTextArea
              onFileUpload={handleFileUpload}
              onClearFile={handleClearFileUpload}
              documentPlaceHolder='Carica o trascina il tuo file qui' />
            <Button
              variant="contained"
              color="primary"
              disabled={!file || isLoading}
              onClick={handleAnalyze}
              sx={{
                width: '70%',
                borderRadius: 3,
                fontWeight: 600
              }}>
              {isLoading ? <CircularProgress size={24} color="inherit" /> : "Invia per l'analisi"}
            </Button>
          </Box>

          <Typography variant="caption" color="text.secondary" sx={{ mt: 4 }}>
            Supporta il formato .pdf
          </Typography>
        </>
      ) : (
        <Box sx={{
          display: "flex",
          flexDirection: "column",
          height: "74vh",
          width: "100%",
          bgcolor: "#fff",
          borderRadius: 3,
          overflow: "hidden",
          borderLeft: 'solid 1px #e9e9e9ff',
          borderBottom: 'solid 1px #e9e9e9ff',
        }}>
          {/* Header */}
          <Box sx={{
            p: 2,
            borderBottom: "1px solid #eee",
            bgcolor: "#fafafaff",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            boxShadow: "0px 1px 3px rgba(0,0,0,0.08)"
          }}>
            <Box>
              <Typography variant="subtitle1" fontWeight={600} fontSize={15}>
                Chat di analisi dei documenti
              </Typography>
              {file && (
                <Typography variant="caption" color="text.secondary">
                  Documenti: {file.name}
                </Typography>
              )}
            </Box>
            <Button
              variant="outlined"
              color="primary"
              size="small"
              onClick={handleNewDocument}
              sx={{ borderRadius: 2, textTransform: "none", fontSize: 12 }}
            >
              Carica un nuovo documenti
            </Button>
          </Box>

          {/* Messages */}
          <Box sx={{ flex: 1, p: 2, overflowY: "auto", display: "flex", flexDirection: "column" }}>
            <ChatMessageList
              messages={messages}
              isTyping={isTyping}
              isOverview={isOverview}
              page='check-compliance'
            />
          </Box>

          {/* Input fixo */}
          <Box sx={{
            display: "flex",
            alignItems: "center",
            borderTop: "1px solid #eee",
            p: 1.5,
            bgcolor: "#fff",
            boxShadow: "0px -1px 3px rgba(0,0,0,0.06)"
          }}>
            <TextField
              fullWidth
              size="small"
              placeholder="Inserisci la tua domanda..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
            />
            <IconButton color="primary" onClick={handleSend} sx={{ ml: 1 }}>
              <SendIcon />
            </IconButton>
          </Box>
        </Box>
      )}
    </Box>
  )
}

export default DocCheck