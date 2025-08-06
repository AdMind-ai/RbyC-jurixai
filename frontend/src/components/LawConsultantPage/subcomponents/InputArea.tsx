import React, { useState, useEffect, useRef } from 'react';
import { Box, Button, TextField, Typography } from '@mui/material';
// import { modelMapping } from './Header';
import { useTheme } from '@mui/material/styles';
import { fetchWithAuth } from '../../../api/fetchWithAuth';
import { fetchWithoutAuth } from '../../../api/fetchWithoutAuth';

interface ChatInputAreaProps {
  onSend: (content: string, sender: 'user' | 'ai', isStream?: boolean) => void;
  selectedModel: string;
  selectedChat: { id: number | string; name: string } | null;
  setSelectedChat: React.Dispatch<React.SetStateAction<{ id: number | string; name: string } | null>>;
  searchWebEnabled: boolean;
  setSearchWebEnabled: (enabled: boolean) => void;
  isEmptyMessages: boolean;
  setCitations?: React.Dispatch<React.SetStateAction<string[]>>;
  setIsOverview: React.Dispatch<React.SetStateAction<boolean>>;
  setIsTyping: React.Dispatch<React.SetStateAction<boolean>>;
}

const ChatInputArea: React.FC<ChatInputAreaProps> = ({
  onSend,
  // selectedModel,
  selectedChat,
  // searchWebEnabled,
  isEmptyMessages,
  setCitations,
  setIsOverview,
  setIsTyping
}) => {
  const theme = useTheme();
  const [text, setText] = useState('');
  // const [file, setFile] = useState<File | null>(null);
  const [isFileAttached, setIsFileAttached] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const [threadId, setThreadId] = useState("");


  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  function handleDeepResearchReady(e: CustomEvent<{
    conversationId: string | number,
    messageId: string | number,
    chatName: string,
    content: string,
    citations: string[]
  }>) {
    if (selectedChat && e.detail.conversationId === selectedChat.id) {
      onSend(e.detail.content, "ai", true);
      if (setCitations && e.detail.citations) {
        setCitations(e.detail.citations);
      }
    }
  }

  useEffect(() => {
    const handler = handleDeepResearchReady as EventListener;
    window.addEventListener("deepResearchReady", handler as EventListener);
    return () => window.removeEventListener("deepResearchReady", handler as EventListener);
  }, [selectedChat, onSend]);


  useEffect(() => {
    const createThread = async () => {
      const res = await fetchWithoutAuth("/openai/chat/assistant/thread", {
        method: "POST",
      });
      if (!res.ok) return;
      const data = await res.json();
      setThreadId(data.threadId);
    };
    createThread();
  }, []);

  const handleSubmit = async () => {
    setIsOverview(false);
    setIsTyping(true);
    setIsFileAttached(false);
    if (!text.trim()) return;

    onSend(text, 'user');

    setText('');
    // setFile(null);

    try {
      const formData = new FormData();
      formData.append('content', text);
      formData.append('thread_id', threadId);

      // const modelToUse = searchWebEnabled ? 'gpt-4o-search-preview' : modelMapping[selectedModel];
      // formData.append('model', modelToUse);

      // if (file) {
      //   formData.append('file', file);
      // }

      // if (selectedChat) {
      //   formData.append('conversation_id', selectedChat.id.toString());
      // } 

      const response = await fetchWithAuth('/openai/chat/assistant/law-consultant', {
        method: 'POST',
        body: formData,
      });

      setIsTyping(false);

      if (!response.ok || !response.body) {
        onSend('Erro ao conectar.', 'ai');
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let done = false;

      while (!done) {
        const { value, done: doneReading } = await reader.read();
        done = doneReading;

        if (value) {
          const chunkValue = decoder.decode(value, { stream: true });
          // O terceiro parâmetro indica "modo streaming" para concatenar no chat
          onSend(chunkValue, 'ai', true);
        }
      }

      // Flush final para garantir que nenhum caractere UTF-8 fique incompleto
      const lastChunk = decoder.decode();
      if (lastChunk) {
        onSend(lastChunk, 'ai', true);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      setIsTyping(false);
      onSend('Erro ao enviar mensagem.', 'ai');
    } finally {
      setIsTyping(false);
    }
  };


  const ChatTextInputBox = () => (
    <Box
      sx={{
        width: '100%',
        display: 'flex',
        justifyContent: 'center',
      }}
    >
      {isEmptyMessages && (
        <Box
          sx={{
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            flexDirection: 'column',
            gap: 3,
          }}
        >
          <Box
            sx={{
              width: '100%',
              minHeight: '60px',
              maxHeight: '300px',
              borderRadius: '12px',
              border: `1px solid #CBCBCB`,
              padding: '16px',
            }}
          >
            <TextField
              inputRef={inputRef}
              variant="standard"
              multiline
              fullWidth
              minRows={2}
              value={text}
              placeholder="Inserisci qui il testo…"
              onChange={e => setText(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit();
                }
              }}
              sx={{
                mb: '50px',
                '& .MuiInputBase-root': {
                  padding: 0,
                  fontSize: '17px',
                  maxHeight: isFileAttached ? '160px' : '200px',
                  overflowY: 'auto',
                  '&:before, &:after, &:hover:not(.Mui-disabled):before': {
                    borderBottom: 'none !important'
                  },
                }
              }}
            />

          </Box>
          <Button
            variant="contained"
            disabled={!text.trim()}
            onClick={handleSubmit}
            sx={{
              borderRadius: '6px', padding: '6px 16px',
              textTransform: 'none', width: '9.5vw', fontSize: '17px'
            }}
          >
            Invia
          </Button>
        </Box>
      )}
    </Box>
  );


  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
      {isEmptyMessages ? (
        <>
          <Typography variant="body1" sx={{ mb: 3, color: theme.palette.text.primary, textAlign: 'center' }}>
            Incolla qui il pezzo di legge da cui vuoi estrarre i riferimenti di legge
          </Typography>

          <Box sx={{ width: '100%', maxWidth: '75vw', marginBottom: '3vh', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            {ChatTextInputBox()}
          </Box>
        </>
      ) : (
        <Box sx={{ display: 'flex', justifyContent: 'center', pointerEvents: 'none', mt: 20 }}>
          <Box sx={{ width: '100%', maxWidth: '84vw', backgroundColor: 'white', borderRadius: '12px', pointerEvents: 'auto' }}>
            {ChatTextInputBox()}
          </Box>
        </Box>
      )}
    </Box>
  );
};

export default ChatInputArea;