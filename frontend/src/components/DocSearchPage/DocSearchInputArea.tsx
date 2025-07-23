import React, { useState, useEffect, useRef } from 'react';
import { Box, Button, TextField, Typography  } from '@mui/material';
import { modelMapping } from '../LawConsultantPage/subcomponents/Header';
import { useTheme } from '@mui/material/styles';
import { fetchWithAuth } from '../../api/fetchWithAuth';

interface DocSearchInputAreaProps {
  onSend: (content: string, sender: 'user' | 'ai', isStream?: boolean) => void;
  selectedModel: string;
  selectedChat: { id: number | string; name: string } | null;
  searchWebEnabled: boolean;
  isEmptyMessages: boolean;
  setIsOverview: React.Dispatch<React.SetStateAction<boolean>>;
  setIsTyping:React.Dispatch<React.SetStateAction<boolean>>;
}

const DocSearchInputArea: React.FC<DocSearchInputAreaProps> = ({
  onSend,
  selectedModel,
  selectedChat,
  searchWebEnabled,
  isEmptyMessages,
  setIsOverview,
  setIsTyping
}) => {
  const theme = useTheme();
  const [text, setText] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);


  useEffect(() => {
    inputRef.current?.focus();
  }, []);


  const handleSubmit = async () => {
    setIsOverview(false);
    setIsTyping(true);
    if (!text.trim()) return;
  
    onSend(text, 'user');
  
    setText('');
    setFile(null);
  
    try {
      const formData = new FormData();
      formData.append('content', text);
  
      const modelToUse = searchWebEnabled ? 'gpt-4o-search-preview' : modelMapping[selectedModel];
      formData.append('model', modelToUse);
  
      if (file) {
        formData.append('file', file);
      }
  
      if (selectedChat) {
        formData.append('conversation_id', selectedChat.id.toString());
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
        padding: '16px',
      }}
    >
      <TextField
        inputRef={inputRef}
        variant="standard"
        multiline
        fullWidth
        minRows={4}
        value={text}
        placeholder="Descrivi il documento o l’informazione che ti serve"
        onChange={e => setText(e.target.value)}
        onKeyDown={e => {
          if (e.key === 'Enter' && !e.shiftKey && text.trim()) {
            e.preventDefault();
            handleSubmit();
          }
        }}
        sx={{
          mb: '0px',
          '& .MuiInputBase-root': {
            padding: 0,
            fontSize: '17px',
            overflowY: 'auto',
            '&:before, &:after, &:hover:not(.Mui-disabled):before': {
              borderBottom: 'none !important'
            },
          }
        }}
      />
      <Button
        variant="contained"
        disabled={!text.trim()}
        onClick={handleSubmit}
        sx={{
          position: 'absolute', bottom:16, right:16,
          borderRadius:'6px', 
          textTransform:'none', width:'9.5vw', fontSize:'17px'
        }}
      >
        Invia
      </Button>
    </Box>
  );

  return (
    <Box sx={{ display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', height:'100%' }}>
      {isEmptyMessages ? (
        <>
          <Typography variant="body1" sx={{ mb:3, color: theme.palette.text.primary, textAlign: 'center' }}>
            Seleziona una categoria e poi effettua una ricerca tra i documenti
          </Typography>

          <Box sx={{ width: '100%', maxWidth :'75vw', marginBottom:'10vh', display:'flex', flexDirection: 'column', alignItems:'center' }}>
            {ChatTextInputBox()}
          </Box>
        </>
      ) : (
        <Box sx={{ position:'absolute', bottom:0, left:0, right:0, display:'flex', justifyContent:'center', pointerEvents:'none' }}>
          <Box sx={{ width:'100%', maxWidth:'84vw', backgroundColor:'white', borderRadius: '12px', pointerEvents:'auto' }}>
            {ChatTextInputBox()}
          </Box>
        </Box>
      )}
    </Box>
  );
};

export default DocSearchInputArea;