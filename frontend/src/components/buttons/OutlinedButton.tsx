import React, { useState, useEffect } from 'react'
import { Button } from '@mui/material'
import { useTheme } from '@mui/material/styles'
import { SvgIconProps } from '@mui/material/SvgIcon'

interface OutlinedButtonProps {
  icon?: React.ReactElement<SvgIconProps>
  title: string
  color: number
  onClick: () => void
  isSelected?: boolean
  disabled?: boolean
  toggleSelection?: boolean
}

const iconColors = ['#5072CC', '#EAB400', '#FF1A72']

const OutlinedButton: React.FC<OutlinedButtonProps> = ({
  icon,
  title,
  color,
  onClick,
  isSelected = false,
  disabled = false,
  toggleSelection = true
}) => {
  const theme = useTheme()
  const [selected, setSelected] = useState(false)

  useEffect(() => {
    setSelected(isSelected)
  }, [isSelected]) 

  const handleButtonClick = () => {
    if (toggleSelection) {
      setSelected(prev => !prev)
    }
    onClick()
  }

  const colorIndex = color
  const iconColor = iconColors[colorIndex - 1]

  const styledIcon = icon
    ? React.cloneElement(icon, { sx: { color: selected ? 'white' : disabled? theme.palette.grey[400] : iconColor, fontSize: '1.5rem' } }) 
    : null

  return (
    <Button
      variant="outlined"
      startIcon={styledIcon}
      disabled={disabled}
      sx={{
        color: selected ? 'white' : 'black',
        fontSize: '17px',
        fontWeight: selected ? '700' : '400',
        borderRadius: '8px',
        border: `2px solid ${selected ? '#5072CC' : theme.palette.grey[300]}`,
        textTransform: 'none',
        display: 'flex',
        alignItems: 'center',
        paddingX: '12px', 
        paddingY: '8px',  
        gap: 0, 
        whiteSpace: 'nowrap',
        width: 'auto',
        backgroundColor: selected ? '#5072CC' : 'white',
        '&:hover': {
          backgroundColor: selected ? '#5066CC' : '#f3f4f6',
          borderColor: selected ? '#5066CC' : '#9ca3af',
        },
        '&.Mui-disabled': { 
          backgroundColor: theme.palette.grey[100],
          borderColor: theme.palette.grey[200],
          color: theme.palette.grey[400],
        },
      }}
      onClick={handleButtonClick}
    >
      {title}
    </Button>
  )
}

export default OutlinedButton
