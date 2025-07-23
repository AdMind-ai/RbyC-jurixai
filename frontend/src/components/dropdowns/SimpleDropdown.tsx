import React, { useState } from 'react'
import { Button, Menu, MenuItem, Box, Typography, ListItemIcon } from '@mui/material';
import ArrowDropDownIcon from '@mui/icons-material/ArrowDropDown'
import CheckIcon from '@mui/icons-material/Check';
import CloseIcon  from '@mui/icons-material/CloseRounded';
import IconButton from '@mui/material/IconButton';

interface SimpleDropdownProps {
  title: string
  options: string[]
  selectedValue: string;
  onSelect?: (selectedOption: string) => void
  isDeleteItems?: boolean 
  onDeleteItem?: (itemName: string) => void 
}

const SimpleDropdown: React.FC<SimpleDropdownProps> = ({ title, options, selectedValue, onSelect, isDeleteItems = false, onDeleteItem  }) => {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  // const [selectedIndex, setSelectedIndex] = useState<null | number>(null);
  const open = Boolean(anchorEl);

  const handleClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    setAnchorEl(event.currentTarget)
  }

  const handleClose = () => {
    setAnchorEl(null)
  }

  const handleSelect = (index: number) => {
    // setSelectedIndex(index);
    onSelect?.(options[index])
    handleClose();
  };

  return (
    <Box sx={{ padding: 0 }}>
      <Button
        onClick={handleClick}
        endIcon={<ArrowDropDownIcon />}
        sx={{
          textTransform: 'none',
          fontWeight: 'regular',
          color: 'black',
          fontSize: '16px',
          padding: '0px 12px',
          width: 'auto',
        }}
      >
        {selectedValue || title}
      </Button>
      <Menu
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
        PaperProps={{
          style: {
            borderRadius: 10,  
            backgroundColor: '#f9f9f9', 
            maxHeight: 300, 
            overflowY: 'auto',
          },
        }}
      >
        {options.map((option, index) => (
          <MenuItem
            key={index}
            onClick={() => handleSelect(index)}
            selected={option === selectedValue}
            sx={{
              '&:hover': {
                backgroundColor: 'rgba(0, 0, 0, 0.05)',
              },
              display:'flex',
              justifyContent: 'space-between',
              fontWeight: option === selectedValue ? 'bold' : 'normal',
              fontSize: '14px', 
              borderRadius: 10,  
            }}
          >
            {option === selectedValue && (
              <ListItemIcon>
                <CheckIcon fontSize="small" />
              </ListItemIcon>
            )}
            <Typography variant="inherit">{option}</Typography>
            {isDeleteItems && (
              <IconButton
                size="small"
                edge="end"
                onClick={e => {
                  e.stopPropagation(); 
                  onDeleteItem?.(option);
                  handleClose(); 
                }}
                sx={{ml:2}}
              >
                <CloseIcon fontSize="small" />
              </IconButton>
            )}
          </MenuItem>
        ))}
      </Menu>
    </Box>
  )
}

export default SimpleDropdown
