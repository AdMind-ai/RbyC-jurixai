import React from 'react';
import { Box, keyframes } from '@mui/material';

export const DotTyping: React.FC = () => {
  const dotTyping = keyframes`
    0%, 20% { content: '.'; }
    40% { content: '..'; }
    60% { content: '...'; }
    80%, 100% { content: ''; }
  `;

  return (
    <Box sx={{ 
      '&::after': {
        content: '""',
        display: 'inline-block',
        animation: `${dotTyping} 1s steps(4, end) infinite`,
        fontSize: '1.2rem'
      }
    }} />
  );
};