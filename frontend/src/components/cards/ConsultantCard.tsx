import React from 'react'
import { Typography, Card } from '@mui/material'

interface CardProps {
  title: string
  description: string
  onClick?: () => void
}

const ConsultantCard: React.FC<CardProps> = ({ title, description, onClick }) => {

  return (
    <Card
      onClick={onClick}  
      sx={{
        height: '160px',
        padding: 2,
        flexDirection: 'column',
        aspectRatio: '1.5 / 1',
        gap:2,
        cursor: 'pointer',    
        transition: 'box-shadow 0.2s',
        '&:hover': {
          boxShadow: 6,     
        },
        display: 'flex',     
      }}
      role="button"         
      tabIndex={0}          
    >
      <Typography variant="h4" color='primary'>{title}</Typography>
      <Typography variant="subtitle1">{description}</Typography>
    </Card>
  )
}

export default ConsultantCard