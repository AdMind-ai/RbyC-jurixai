import React from "react";
import { Select, MenuItem, FormControl, InputLabel, IconButton, Typography } from "@mui/material";
import CloseIcon from '@mui/icons-material/CloseRounded';
import ExpandMoreRoundedIcon from '@mui/icons-material/ExpandMoreRounded';
import CheckIcon from '@mui/icons-material/Check';

export interface LinedDropdownProps {
  title: string;
  options: string[];
  value: string | string[] | undefined;
  onChange: (value: string | string[]) => void;
  width?: number;
  isMultipleOptions?: boolean;
  isDeleteItems?: boolean;
  onDeleteItem?: (itemName: string) => void;
}

const LinedDropdown: React.FC<LinedDropdownProps> = ({
  title,
  options,
  value,
  onChange,
  width,
  isMultipleOptions = false,
  isDeleteItems = false,
  onDeleteItem,
}) => {

  const isSelected = (option: string) => 
    isMultipleOptions 
      ? Array.isArray(value) && value.includes(option) 
      : value === option;

  return (
    <FormControl size="small" sx={{ minWidth: width ?? 180 }}>
      <InputLabel>{title}</InputLabel>
      <Select
        multiple={isMultipleOptions}
        label={title}
        value={value ?? (isMultipleOptions ? [] : "")}
        onChange={(e) => {onChange(e.target.value as string)}}
        renderValue={(selected) =>
          isMultipleOptions
            ? (
                <Typography sx={{
                  whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", fontSize: "1rem",
                }}>
                  {Array.isArray(selected) ? selected.join(", ") : selected}
                </Typography>
              )
            : (
                <Typography sx={{
                  whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", fontSize: "1rem",
                }}>
                  {selected}
                </Typography>
              )
        }
        sx={{
          fontSize: '1rem',
          borderRadius: '8px',
          bgcolor: '#fff',
          borderColor: '#E1E8F0',
        }}
        IconComponent={ExpandMoreRoundedIcon} 
        MenuProps={{
          PaperProps: {
            sx: {
              boxShadow: "0px 2px 8px 0px #1A1A1A1A",
              borderRadius: "10px",
              minWidth: 180,
              mt: 0,
              bgcolor: "#fff",
            },
          },
          MenuListProps: {
            sx: {
              "& .MuiMenuItem-root": {
                fontSize: "0.8rem",
                borderRadius: "8px",
                p: 0.8,
                mx: 0.5,
                "&.Mui-selected, &.Mui-focusVisible": {
                  bgcolor: "#F5F6FA",
                  mx: 0.5,
                  borderRadius: "8px",
                },
              },
            },
          },
        }}
      >
        {options.map((option) => (
          <MenuItem
            key={option}
            value={option}
            sx={{
              fontSize: "1rem",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <Typography
              variant="inherit"
              sx={{
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
                ml: 1,
              }}
            >
              {option}
            </Typography>
            {isMultipleOptions && isSelected(option) && (
              <CheckIcon fontSize="small" sx={{ ml: 1, color: "#1976d2" }} />
            )}
            {isDeleteItems && (
              <IconButton
                size="small"
                edge="end"
                onClick={e => {
                  e.stopPropagation();
                  onDeleteItem?.(option);
                }}
                sx={{ ml: 1.5 }}
              >
                <CloseIcon fontSize="small" />
              </IconButton>
            )}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
};

export default LinedDropdown;