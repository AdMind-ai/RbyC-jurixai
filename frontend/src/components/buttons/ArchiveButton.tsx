import React from 'react'
import { Button, Box, Typography } from '@mui/material'
import ArchiveIcon from '../assets/icons/archive-icon.svg'
import { useTheme } from '@mui/material/styles'

interface ArchiveButtonProps {
  label: string
}

const ArchiveButton: React.FC<ArchiveButtonProps> = ({ label }) => {
  const theme = useTheme()
  return (
    <Button
      variant="outlined"
      sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        border: `calc(0.1vh) solid ${theme.palette.text.secondary}`,
        borderRadius: 'calc(0.5vw)',
        padding: 0,
        textTransform: 'none',
        width: 'calc(13.6vh)',
        height: 'calc(4.3vh)',
        minWidth: '10px',
        maxWidth: '450px',
        backgroundColor: theme.palette.background.default,
        '&:hover': {
          backgroundColor: 'rgba(0, 0, 0, 0.05)',
          borderColor: theme.palette.text.secondary,
        },
      }}
    >
      {/* Ícone */}
      <Box
        component="img"
        src={ArchiveIcon}
        alt="Archive Icon"
        sx={{
          width: "2vh",
          height: "2vh",
          marginRight: 'calc(0.3vw)',
        }}
      />
      {/* Texto do botão */}
      <Typography
        variant="button"
        sx={{
          fontSize: "1.9vh",
          fontWeight: 400,
          color: theme.palette.text.secondary,
        }}
      >
        {label}
      </Typography>
    </Button>
  )
}

export default ArchiveButton
