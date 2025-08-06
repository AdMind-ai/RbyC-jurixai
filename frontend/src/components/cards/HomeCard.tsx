import React from 'react'
import { useTheme } from '@mui/material/styles'
import { Box, Button, Typography, Card } from '@mui/material'
import { useNavigate } from 'react-router-dom'

interface CardProps {
  title: string
  description: string
  icon: string
  path: string
}

const HomeCard: React.FC<CardProps> = ({ title, description, icon, path }) => {
  const theme = useTheme()
  const navigate = useNavigate()

  const handleNavigation = (path: string) => {
    navigate(path)
  }

  return (
    <Card
      sx={{
        flexDirection: 'column',
        justifyContent: 'space-between',
        aspectRatio: '1.2 / 1',
      }}
    >
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
        {/* Ícone */}
        <Box
          component="img"
          src={icon}
          alt={`${title} Icon`}
          sx={{
            width: '35px',
            height: '40px',
            objectFit: 'contain',
            color: theme.palette.secondary.main,
          }}
        />

        {/* Título */}
        <Typography variant="h4">{title}</Typography>

        {/* Botão */}
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 5 }}>
          <Button variant="contained" sx={{ fontSize: '12px', width: '165px', height: '32px', backgroundColor: '#21148E' }} onClick={() => handleNavigation(path)}>
            VAI ALLA FUNZIONE
          </Button>
        </Box>
      </Box>

      {/* Descrição */}
      <Typography variant="subtitle1">{description}</Typography>

    </Card>
  )
}

export default HomeCard
