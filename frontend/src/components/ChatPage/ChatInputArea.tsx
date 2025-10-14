import React, { useState, useEffect, useRef } from 'react';
import { useGlobal } from "../../context/GlobalContext";
import { Box, Button, TextField, Typography, IconButton } from '@mui/material';
import OutlinedButton from '../buttons/OutlinedButton';
import FilePresentRoundedIcon from '@mui/icons-material/FilePresentRounded';
import CloseIcon from '@mui/icons-material/DisabledByDefaultRounded';
import AttachFileIcon from '@mui/icons-material/AttachFile';
// import SearchWebIcon from '@mui/icons-material/TravelExploreOutlined';
import OverviewIcon from '@mui/icons-material/AnalyticsOutlined';
import { useTheme } from '@mui/material/styles';
import { fetchWithAuth } from '../../api/fetchWithAuth';
import CircularProgress from '@mui/material/CircularProgress';
import { toast } from "react-toastify";

interface ChatInputAreaProps {
  onSend: (content: string, sender: 'user' | 'ai', isStream?: boolean) => void;
  selectedModel: string;
  selectedChat: { id: number | string; name: string; thread_id: string | null} | null;
  setSelectedChat: React.Dispatch<React.SetStateAction<{ id: number | string; name: string; thread_id: string | null} | null>>;
  searchWebEnabled: boolean;
  setSearchWebEnabled: (enabled: boolean) => void;
  isEmptyMessages: boolean;
  setCitations?: React.Dispatch<React.SetStateAction<string[]>>;
  setIsOverview: React.Dispatch<React.SetStateAction<boolean>>;
  setIsTyping: React.Dispatch<React.SetStateAction<boolean>>;
  conversationId: string
}

const ChatInputArea: React.FC<ChatInputAreaProps> = ({
  onSend,
  selectedChat,
  setSelectedChat,
  // searchWebEnabled,
  setSearchWebEnabled,
  isEmptyMessages,
  setCitations,
  setIsOverview,
  setIsTyping,
  conversationId
}) => {
  const theme = useTheme();
  const { setAwaitingDeepResponse } = useGlobal();
  const [text, setText] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [isFileAttached, setIsFileAttached] = useState(false);
  // const [searchWebEnabled, setSearchWebEnabled] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const [loading, setLoading] = useState(false);


  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files ? e.target.files[0] : null;
    if (selectedFile) {
      setFile(selectedFile);
      setIsFileAttached(true);
    }
  };

  const handleFileUploadClick = () => {
    setSearchWebEnabled(false);
    document.getElementById('file-input')?.click();
  };

  // const handleWebSearchClick = () => {
  //   setSearchWebEnabled(!searchWebEnabled);
  // };

  // const handleOverviewClick = async () => {
  //   setIsOverview(true);
  //   setLoading(true);

  //   try {
  //     const response = await fetchWithAuth('/perplexity/deep-search/', {
  //       method: 'POST'
  //     });

  //     if (!response.ok || !response.body) {
  //       onSend('Erro ao conectar.', 'ai');
  //       setLoading(false);
  //       return;
  //     }
  //     setLoading(false);

  //     const reader = response.body.getReader();
  //     const decoder = new TextDecoder("utf-8");
  //     let citationsReceived = false;

  //     while (true) {
  //       const { done, value } = await reader.read();
  //       if (done) break;

  //       const chunk = decoder.decode(value, { stream: true });

  //       if (!citationsReceived && chunk.includes('_CITATIONS_START_')) {
  //         const citationsJson = chunk.substring(
  //           chunk.indexOf('_CITATIONS_START_') + '_CITATIONS_START_'.length,
  //           chunk.indexOf('_CITATIONS_END_')
  //         );
  //         const citations = JSON.parse(citationsJson).citations;
  //         setCitations?.(citations);
  //         citationsReceived = true;

  //         const cleanedChunk = chunk.substring(chunk.indexOf('_CITATIONS_END_') + '_CITATIONS_END_'.length);
  //         onSend(cleanedChunk, 'ai', true);
  //         // console.log(cleanedChunk)
  //       } else {
  //         onSend(chunk, 'ai', true); 
  //         // console.log(chunk)
  //       }
  //     }

  //   } catch (error) {
  //     console.error('Erro ao conectar:', error);
  //     onSend('Erro ao conectar.', 'ai');
  //   } finally {
  //     console.log('ACABOU')
  //     setLoading(false);
  //     setIsOverview(false);
  //   }
  // };

  const handleOverviewClick = async () => {
    setIsOverview(true);
    try {
      const response = await fetchWithAuth('/perplexity/deep-search/', {
        method: 'POST'
      });
      const resData = await response.json();
      if (response.ok && resData.conversation_id && resData.waiting_message_id) {
        setSelectedChat({ id: resData.conversation_id, name: resData.conversation_name, thread_id: null });
        onSend("Starting Deep Research...", 'ai', true);
        setLoading(true);
        setAwaitingDeepResponse({
          conversationId: resData.conversation_id,
          messageId: resData.waiting_message_id,
          placeholderText: "processing",
          chatName: resData.conversation_name
        });
        toast.info("Ricerca approfondita in corso, verrai notificato quando sarà pronta.");
      } else {
        toast.error("An error occurred while starting the deep search.");
      }
    } catch (err) {
      toast.error("An error occurred while starting the deep search. error: " + err);
    } finally {
      setIsOverview(false);
    }
  };

  function handleDeepResearchReady(e: CustomEvent<{
    conversationId: string | number,
    messageId: string | number,
    chatName: string,
    content: string,
    citations: string[]
  }>) {
    if (selectedChat && e.detail.conversationId === selectedChat.id) {
      setLoading(false);
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


  const handleSubmit = async () => {
    setIsOverview(false);
    setIsTyping(true);
    setIsFileAttached(false);
    if (!text.trim()) return;

    onSend(text, 'user');

    setText('');
    setFile(null);

    try {
      const formData = new FormData();
      formData.append('content', text);

      if (file) {
        formData.append('file', file);
      }

      if (selectedChat) {
        formData.append('conversation_id', selectedChat.thread_id as string);
      }
      else if (conversationId) {
        console.log(conversationId)
        formData.append('conversation_id', conversationId);
      }

    
      const response = await fetchWithAuth('/openai/chat/send-message/', {
        method: 'POST',
        body: formData
      });
      setIsTyping(false);

      if (!response.ok || !response.body) {
        onSend('Erro ao conectar.', 'ai');
        return;
      }

      if (response.ok) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');

        let done = false;
        while (!done) {
          const { value, done: doneReading } = await reader.read();
          done = doneReading;
          const chunkValue = decoder.decode(value, { stream: true });
          onSend(chunkValue, 'ai', true);
        }
      } else {
        console.error('Erro ao conectar:', response.statusText);
        onSend('Erro ao gerar resposta.', 'ai');
      }

    } catch (error) {
      console.error('Error sending message:', error);
      setIsTyping(false);
      onSend('Erro ao enviar mensagem.', 'ai');
    }
  };


  const ChatTextInputBox = () => (
    <Box
      sx={{
        position: 'relative',
        width: '100%',
        minHeight: '60px',
        maxHeight: '300px',
        borderRadius: '12px',
        border: `1px solid #CBCBCB`,
        display: 'flex',
        flexDirection: 'column',
        padding: '16px',
      }}
    >
      {AttachedFilePreview()}
      <TextField
        inputRef={inputRef}
        variant="standard"
        multiline
        fullWidth
        minRows={2}
        value={text}
        placeholder="Scrivi qui la tua richiesta o usa uno degli strumenti."
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

      <Box sx={{ position: 'absolute', bottom: 16, left: 16, display: 'flex', gap: 2 }}>
        <input id="file-input" type="file" accept="image/*,application/pdf" hidden onChange={handleFileChange} />
        <OutlinedButton icon={<AttachFileIcon />} title="Immagine/documento" color={1} onClick={handleFileUploadClick} disabled={isFileAttached} toggleSelection={false} />
        {/* <OutlinedButton icon={<SearchWebIcon />} title="SearchWeb" color={1} onClick={handleWebSearchClick} isSelected={searchWebEnabled} disabled={isFileAttached} /> */}
      </Box>

      <Button
        variant="contained"
        disabled={!text.trim()}
        onClick={handleSubmit}
        sx={{
          position: 'absolute', bottom: 16, right: 16,
          borderRadius: '6px', padding: '6px 16px',
          textTransform: 'none', width: '9.5vw', fontSize: '17px'
        }}
      >
        Invia
      </Button>
    </Box>
  );

  const AttachedFilePreview = () => file && (
    <Box sx={{ display: 'flex', gap: 0.2, alignItems: 'end', mb: 1.5 }}>
      <FilePresentRoundedIcon color="action" sx={{ height: 20 }} />
      <Typography variant="subtitle1" >
        {file.name.length > 100 ? file.name.substring(0, 100) + '...' : file.name}
      </Typography>
      <IconButton
        size="small"
        onClick={() => {
          setFile(null);
          setIsFileAttached(false);
          setSearchWebEnabled(false);

          const fileInput = document.getElementById('file-input') as HTMLInputElement;
          if (fileInput) fileInput.value = '';
        }}
        sx={{
          color: '#FF1744',
          width: 15,
          height: 15,
          ml: 3,
          pb: '8px'
        }}
      >
        <CloseIcon sx={{ fontSize: '15px', fontWeight: '700' }} />
      </IconButton>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
      {isEmptyMessages ? (
        <>
          <Typography variant="h1" sx={{ mb: 3, color: theme.palette.text.primary, textAlign: 'center' }}>
            Come posso esserti utile?
          </Typography>

          <Box sx={{ width: '100%', maxWidth: '75vw', marginBottom: '3vh', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            {ChatTextInputBox()}

            <Box sx={{ mt: 2, display: 'none', gap: 2, flexDirection: 'column', alignItems: 'center' }}>
              <OutlinedButton icon={<OverviewIcon />} title="Overview del titolo" color={1} onClick={handleOverviewClick} />
              {loading && <CircularProgress />}
            </Box>
          </Box>
        </>
      ) : (
        <Box sx={{ position: 'absolute', bottom: 0, left: 0, right: 0, display: 'flex', justifyContent: 'center', pointerEvents: 'none' }}>
          <Box sx={{ width: '100%', maxWidth: '84vw', backgroundColor: 'white', borderRadius: '12px', pointerEvents: 'auto' }}>
            {ChatTextInputBox()}
          </Box>
        </Box>
      )}
    </Box>
  );
};

export default ChatInputArea;