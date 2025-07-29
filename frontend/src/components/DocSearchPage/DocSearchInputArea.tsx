import React, { useState, useEffect, useRef } from 'react';
import { Box, Button, TextField, Typography } from '@mui/material';
import { useTheme } from '@mui/material/styles';

interface DocSearchInputAreaProps {
  onSendMessage: (message: string) => Promise<void>;
  isEmptyMessages: boolean;
  isTyping: boolean;
  setIsTyping: React.Dispatch<React.SetStateAction<boolean>>;
}

const DocSearchInputArea: React.FC<DocSearchInputAreaProps> = ({
  onSendMessage,
  isEmptyMessages,
  isTyping,
  setIsTyping
}) => {
  const theme = useTheme();
  const [text, setText] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = async () => {
    if (!text.trim() || isTyping) return;
    setIsTyping(true);
    setText('');
    await onSendMessage(text);
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
        disabled={!text.trim() || isTyping}
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