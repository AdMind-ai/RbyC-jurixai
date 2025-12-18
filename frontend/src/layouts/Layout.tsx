// layouts/Layout.tsx
import React, { useState, useContext } from "react";
import { Box, Typography, Menu, MenuItem, Avatar } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import Sidebar from "../components/Sidebar";
// import ArchiveButton from "../components/ArchiveButton";
import { AuthContext } from "../context/AuthContext";
import { useNavigate } from "react-router-dom";
import ExpandMoreRoundedIcon from '@mui/icons-material/ExpandMoreRounded';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const theme = useTheme();
  const auth = useContext(AuthContext);
  const navigate = useNavigate();

  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const open = Boolean(anchorEl);

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = () => {
    auth?.logout();
    navigate("/login");
  };

  const userName = auth?.user?.username || "User";
  const userInitial = userName.charAt(0).toUpperCase();

  return (
    <Box
      sx={{
        display: "flex",
        height: "100vh",
        width: "100vw",
        backgroundColor: theme.palette.background.paper,
      }}
    >
      {/* Sidebar */}
      <Sidebar />

      <Box sx={{ display: "flex", flexDirection: "column", width: "100%", height: "100%" }}>
        {/* Header */}
        <Box
          component="header"
          sx={{
            height: "calc(9.1vh)",
            width: "calc(90vw)",
            paddingRight: "calc(3vh)",
            paddingTop: "calc(1.5vh)",  
            display: "flex",
            alignItems: "center",
            justifyContent: "flex-end",
            gap: "calc(1.3vh)"
          }}
        >
          {/* <ArchiveButton label={"Archivio"} /> */}

          {/* User Dropdown */}
          <Box
            sx={{ 
              display: "flex", 
              alignItems: "center", 
              cursor: "pointer", 
              padding: '0.7vh 0.6vw',
              '&:hover': {
                backgroundColor: 'rgba(0, 0, 0, 0.05)',
                borderRadius: 'calc(4vh)',
              },
            }}
            onClick={handleMenuOpen}
          >
            <Avatar
              sx={{
                bgcolor: theme.palette.secondary.main,
                color: theme.palette.primary.contrastText,
                width: "4vh",
                height: "4vh",
                fontSize: "2.5vh",
              }}
            >
              {userInitial}
            </Avatar>
            <Typography
              variant="subtitle1"
              sx={{
                marginLeft: "0.5vw",
                fontSize: "2.5vh",
                color: theme.palette.text.primary,
              }}
            >
              {userName}
            </Typography>
            <ExpandMoreRoundedIcon
              sx={{
                fontSize: "2.5vh",
                color: theme.palette.text.secondary,
              }}
            />
          </Box>

          {/* Dropdown Menu  */}
          <Menu
            anchorEl={anchorEl}
            open={open}
            onClose={handleMenuClose}
            anchorOrigin={{
              vertical: "bottom",
              horizontal: "right",
            }}
            transformOrigin={{
              vertical: "top",
              horizontal: "right",
            }}
            PaperProps={{
              sx: {
                mt: 1,
                borderRadius: "12px",
                backgroundColor: theme.palette.background.default,
                boxShadow: "0px 4px 10px rgba(0,0,0,0.2)",
              },
            }}
          >
            <MenuItem
              sx={{
                fontSize: "2vh",
                backgroundColor: "white",
                "&:hover": {
                  backgroundColor: theme.palette.action.hover,
                },
              }}
              onClick={handleLogout}
            >
              Logout
            </MenuItem>
          </Menu>
        </Box>

        {/* Content */}
        <Box
          component="main"
          sx={{
            padding: '1vh calc(1vw) calc(2vw) 0vh',
            height: 'calc(88vh)',
            width: 'calc(90vw)',
          }}
        >
          <Box
            sx={{
              height: 'calc(87vh)',
              backgroundColor: theme.palette.background.default,
              borderRadius: 'calc(1.7vw)',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
            }}
          >
            {children}
          </Box>
        </Box>
      </Box>
    </Box>
  );
};

export default Layout;