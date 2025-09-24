import { useState } from 'react'
import {
  Box,
  Button,
  Typography,
  CircularProgress,
  Paper,
  IconButton,
  TextField
} from '@mui/material'
// import { api } from '../../api/api'
import { toast } from 'react-toastify'

// Icons
import SendIcon from '@mui/icons-material/Send'
import CloudUploadIcon from '@mui/icons-material/CloudUpload'
import UploadableTextArea from '../upload-components/UploadableTextArea'

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

const DocCheck = () => {
  const [isLoading, setIsLoading] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [isChatOpen, setIsChatOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")

  const handleFileUpload = (f: File | File[]) => {
    const first = Array.isArray(f) ? f[0] : f
    setFile(first)
  }

  const handleAnalyze = async () => {
    if (!file) return
    setIsLoading(true)
    try {
      const formData = new FormData()
      formData.append("file", file)

      // await api.post("/analyze/document/", formData, {
      //   headers: { "Content-Type": "multipart/form-data" },
      // })

      setIsChatOpen(true)
      setMessages([
        { role: "assistant", content: "O documento foi processado. Em que posso ajudar com a análise?" }
      ])
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error)
      toast.error(`Erro ao enviar documento: ${msg}`)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSend = () => {
    if (!input.trim()) return
    const userMsg = { role: "user" as const, content: input }
    setMessages(prev => [...prev, userMsg])
    setInput("")

    // Simulação de resposta da OpenAI
    setTimeout(() => {
      setMessages(prev => [
        ...prev,
        { role: "assistant", content: "Esta é uma resposta simulada baseada no documento enviado." }
      ])
    }, 800)
  }

  return (
    <Box
      sx={{
        height: "100%",
        width: "100%",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        p: 2
      }}
    >
      {!isChatOpen ? (
        <>
          {/* Header / Intro */}
          <Box sx={{ mb: 4, textAlign: "center" }}>
            <Typography variant="body1" color="text.secondary" maxWidth={420} fontSize={19}>
              Carica un documento per l'analisi di conformità.
              Il sistema verificherà la conformità in base alle regole interne.
            </Typography>
          </Box>

          {/* Upload Card */}
          <Paper
            elevation={4}
            sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 3,
              p: 5,
              width: 460,
              borderRadius: 4,
              textAlign: 'center',
              background: "#fff"
            }}
          >
            <CloudUploadIcon sx={{ fontSize: 70, color: 'primary.main' }} />

            <UploadableTextArea
              onFileUpload={handleFileUpload}
              documentPlaceHolder='Carica o trascina il tuo file qui'
            />

            <Button
              variant="contained"
              color="primary"
              disabled={!file || isLoading}
              onClick={handleAnalyze}
              sx={{ width: '70%', borderRadius: 3, fontWeight: 600 }}
            >
              {isLoading ? <CircularProgress size={24} color="inherit" /> : "Invia per l'analisi"}
            </Button>
          </Paper>

          {/* Footer */}
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ mt: 4 }}
          >
            Supporta il formato .pdf
          </Typography>
        </>
      ) : (
        <Paper
          elevation={2}
          sx={{
            display: "flex",
            flexDirection: "column",
            height: "72vh",
            width: "100%",
            borderRadius: 3,
            overflow: "hidden"
          }}
        >
          {/* Header */}
          <Box
            sx={{
              p: 2,
              borderBottom: "1px solid #eee",
              bgcolor: "#f9fafb",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between"
            }}
          >
            <Box>
              <Typography variant="subtitle1" fontWeight={600} fontSize={14}>
                Chat di analisi dei documenti
              </Typography>
              {file && (
                <Typography variant="caption" color="text.secondary">
                  Documento: {file.name}
                </Typography>
              )}
            </Box>

            <Button
              variant="outlined"
              color="primary"
              size="small"
              onClick={() => {
                setIsChatOpen(false)
                setMessages([])
                setFile(null)
              }}
              sx={{ borderRadius: 2, textTransform: "none", fontSize: 12, fontWeight: 500 }}
            >
              Carica un nuovo documento
            </Button>
          </Box>

          {/* Chat body */}
          <Box
            sx={{
              flex: 1,
              p: 2,
              overflowY: "auto",
              display: "flex",
              flexDirection: "column",
              gap: 1,
              bgcolor: "#fff"
            }}
          >
            {messages.map((msg, idx) => (
              <Box
                key={idx}
                sx={{
                  alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
                  maxWidth: "70%",
                  bgcolor: msg.role === "user" ? "#1976d2" : "#f1f3f5",
                  color: msg.role === "user" ? "#fff" : "#222",
                  px: 2,
                  py: 1,
                  borderRadius: 3,
                  boxShadow: 1,
                  fontSize: 14
                }}
              >
                {msg.content}
              </Box>
            ))}
          </Box>

          {/* Input */}
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              borderTop: "1px solid #eee",
              p: 1.2,
              bgcolor: "#fafafa"
            }}
          >
            <TextField
              fullWidth
              size="small"
              placeholder="Inserisci la tua domanda..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
            />
            <IconButton
              color="primary"
              onClick={handleSend}
              sx={{ ml: 1 }}
            >
              <SendIcon />
            </IconButton>
          </Box>
        </Paper>
      )}
    </Box>
  )
}

export default DocCheck