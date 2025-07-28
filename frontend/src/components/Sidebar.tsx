import React, { useState, useEffect } from 'react'
import { Box, List, ListItem, ListItemIcon, Divider, Typography, Collapse } from '@mui/material'
import { useGlobal } from '../context/GlobalContext';
import { useNavigate, useLocation } from 'react-router-dom'
import { useTheme } from '@mui/material/styles'

// Importação dos ícones
import HomeIcon from '../assets/icons/sidebar/home-icon.svg'
import HomeIconActive from '../assets/icons/sidebar/home-icon-active.svg'
// import TranslatorIcon from '../assets/icons/sidebar/translator-icon.svg'
// import TranslatorIconActive from '../assets/icons/sidebar/translator-icon-active.svg'
import ComplianceIcon from '../assets/icons/sidebar/compliance-icon.svg'
import ComplianceIconActive from '../assets/icons/sidebar/compliance-icon-active.svg'
// import DraftIcon from '../assets/icons/sidebar/draft-icon.svg'
// import DraftIconActive from '../assets/icons/sidebar/draft-icon-active.svg'
import SearchIcon from '../assets/icons/sidebar/search-icon.svg'
import SearchIconActive from '../assets/icons/sidebar/search-icon-active.svg'
import ConsultantIcon from '../assets/icons/sidebar/consultant-icon.svg'
import ConsultantIconActive from '../assets/icons/sidebar/consultant-icon-active.svg'
import UsageIcon from '../assets/icons/sidebar/usage-icon.svg'
import UsageIconActive from '../assets/icons/sidebar/usage-icon-active.svg'
import AccessIcon from '../assets/icons/sidebar/access-icon.svg'
import AccessIconActive from '../assets/icons/sidebar/access-icon-active.svg'

// Logos
import Logo from '../assets/logo.png'

// Menu links
const lawOptions = [
  { title: 'Law References', path: 'Law References' },
  // { title: 'Answer Generation', path: 'Answer Generation' },
  // { title: 'Evaluator', path: 'Evaluator' },
  // { title: 'Rerank', path: 'Rerank' },
  // { title: 'Filter Prompt', path: 'Filter Prompt' },
]

const menuItems = [
  { title: 'Home', path: '/', icon: HomeIcon, activeIcon: HomeIconActive },
  // {
  //   title: 'Draft documenti',
  //   path: '/doc-draft',
  //   icon: DraftIcon,
  //   activeIcon: DraftIconActive,
  // },
  {
    title: 'Ricerca documentale',
    path: '/doc-search',
    icon: SearchIcon,
    activeIcon: SearchIconActive,
  },
  {
    title: 'Check compliance',
    path: '/check-compliance',
    icon: ComplianceIcon,
    activeIcon: ComplianceIconActive,
    disabled: true,
  },
  // {
  //   title: 'Traduttore documenti',
  //   path: '/doc-translator',
  //   icon: TranslatorIcon,
  //   activeIcon: TranslatorIconActive,
  // },
  {
    title: 'Law consultant',
    path: '/law-consultant',
    icon: ConsultantIcon,
    activeIcon: ConsultantIconActive,
    options: lawOptions,
  },
]



const admItems = [
  { title: 'Consumo AI', path: '/usage', icon: UsageIcon, activeIcon: UsageIconActive },
  { title: 'Accessi', path: '/access', icon: AccessIcon, activeIcon: AccessIconActive },
]

const Sidebar: React.FC = () => {
  const { setSelectedLawTab, selectedLawTab } = useGlobal();
  const theme = useTheme()
  const navigate = useNavigate()
  const location = useLocation()
  const [activePath, setActivePath] = useState(location.pathname)
  const [openMenu, setOpenMenu] = useState<string | null>(null)

  useEffect(() => {
    if (selectedLawTab && selectedLawTab.trim() !== '') {
      const option = lawOptions.find(opt => opt.title === selectedLawTab)
      if (option) {
        setActivePath(option.path)
        navigate('/law-consultant')
      } else {
        setActivePath('/law-consultant');
      }
    }
    if (selectedLawTab == '') {
      setActivePath('/law-consultant');
      setSelectedLawTab(null)
      setOpenMenu(null);
    }
  }, [selectedLawTab])
  

  const handleMenuClick = (item: typeof menuItems[0]) => {
    if (item.disabled) return;
    
    if (item.options) {
      setActivePath(item.path)
      navigate(item.path)
      setSelectedLawTab('Law References')
      // setSelectedLawTab(null)
    } else {
      setActivePath(item.path)
      navigate(item.path)
      setOpenMenu(null)
      setSelectedLawTab(null)
    }
  }


  useEffect(() => {
    const withOptions = menuItems.find(i => i.options)
    if (
      withOptions &&
      (
        activePath === withOptions.path || 
        (withOptions.options && withOptions.options.some(opt => activePath.startsWith(opt.path)))
      )
    ) {
      if (openMenu !== withOptions.title) {
        setOpenMenu(withOptions.title)
      }
    }
  }, [activePath, openMenu])

  return (
    <Box
      sx={{
        zIndex: 1000,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        height: '100vh',
        width: 'calc(12vw)',
        minWidth: '20px',
        maxWidth: '410px',
        color: theme.palette.text.primary,
      }}
    >
      {/* Logo */}
      <Box
        sx={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: 'calc(6vw)',
          minWidth: '20px',
          maxWidth: '400px',
          textAlign: 'center',
          height: 'calc(8.5vh)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {/* Logo Icon */}
        <Box
          component="img"
          src={Logo}
          alt="Investor Logo"
          sx={{
            // width: "10vh",
            height: "7.5vh",
            marginLeft: 'calc(6.5vw)',
            marginTop: 'calc(2.5vh)',
          }}
        />
      </Box>

      {/* Menu Functions */}
      <Box
        sx={{
          marginTop: 'calc(12vh)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <List
          sx={{
            padding: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 'calc(0.7vw)',
          }}
        >
          {menuItems.map((item) => {
            const isActive = activePath === item.path ||
              (item.options && item.options.some(opt => activePath === opt.path))

            return (
              <Box key={item.title} sx={{ width: '100%' }}>
                <ListItem
                  onClick={() => handleMenuClick(item)}
                  sx={{
                    padding: 0,
                    justifyContent: 'center',
                    alignItems: 'center',
                    width: 'calc(9vw)',
                    height: 'calc(3vw)',
                    cursor: item.disabled ? 'not-allowed' : 'pointer',
                    backgroundColor: isActive
                      ? theme.palette.primary.main
                      : 'transparent',
                    borderRadius: 'calc(0.5vw)',
                    pointerEvents: item.disabled ? 'none' : 'auto',
                    '&:hover': {
                      backgroundColor: item.disabled
                        ? 'transparent'
                        : isActive
                          ? theme.palette.primary.main
                          : 'rgba(0, 0, 0, 0.1)',
                      borderRadius: 'calc(0.5vw)',
                    },
                  }}
                >
                  <ListItemIcon
                    sx={{
                      display: 'flex',
                      justifyContent: 'left',
                      alignItems: 'center',
                      width: '100%',
                      minWidth: '10px',
                      maxWidth: '400px',
                      px: 1.5,
                    }}
                  >
                    <img
                      src={isActive ? item.activeIcon : item.icon}
                      alt={`${item.title} Icon`}
                      style={{
                        width: 'calc(1.7vw)',
                        height: 'calc(1.7vw)',
                      }}
                    />
                    <Typography
                      sx={{
                        fontSize: 'calc(0.9vw)',
                        color: isActive
                          ? theme.palette.primary.contrastText
                          : theme.palette.primary.main,
                        fontWeight: isActive ? 700 : 400,
                        lineHeight: '1',
                        marginLeft: 'calc(0.5vw)',
                      }}
                    >{item.title}</Typography>
                  </ListItemIcon>
                </ListItem>
                {/* Submenu expandido */}
                {/* {item.options && (
                  <Collapse in={openMenu === item.title} timeout="auto" unmountOnExit>
                    <Box sx={{ width: '100%', mt: 1 }}>
                      {item.options.map(opt => (
                        <ListItem
                          key={opt.title}
                          onClick={e => {
                            e.stopPropagation()
                            setActivePath(opt.path)
                            setSelectedLawTab(opt.title)
                            navigate(item.path)
                          }}
                          sx={{
                            py: 0.5,
                            cursor: "pointer",
                            backgroundColor: activePath === opt.path
                              ? theme.palette.secondary.light
                              : "transparent",
                            borderRadius: 1,
                            mb: 0.2,
                            "&:hover": {
                              backgroundColor: theme.palette.action.hover
                            }
                          }}
                        >
                          <Typography
                            sx={{
                              fontSize: '0.5em',
                              color: activePath === opt.path
                                ? theme.palette.primary.contrastText
                                : theme.palette.text.secondary,
                              fontWeight: activePath === opt.path ? 700 : 400
                            }}
                          >
                            {opt.title}
                          </Typography>
                        </ListItem>
                      ))}
                    </Box>
                  </Collapse>
                )} */}
              </Box>
            )
          })}
        </List>
      </Box>

      {/* Adm */}
      <Box
        sx={{
          marginBottom: 'calc(4vh)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <Divider sx={{ width: 'calc(70%)' }} />
        <List
          sx={{
            marginTop: 'calc(0.5vw)',
            padding: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 'calc(0.6vw)',
          }}
        >
          {admItems.map((item) => {
            const isActive = activePath === item.path
            return (
              <ListItem
                key={item.title}
                onClick={() => handleMenuClick(item)}
                sx={{
                  padding: 0,
                  justifyContent: 'center',
                  alignItems: 'center',
                  width: 'calc(9vw)',
                  height: 'calc(3vw)',
                  cursor: 'pointer',
                  backgroundColor: isActive
                    ? theme.palette.primary.main
                    : 'transparent',
                  borderRadius: 'calc(0.5vw)',
                  '&:hover': {
                    backgroundColor: isActive ? theme.palette.primary.main : 'rgba(0, 0, 0, 0.1)',
                    borderRadius: 'calc(0.5vw)',
                  },
                }}
              >
                <Box>

                </Box>
                <ListItemIcon
                  sx={{
                    display: 'flex',
                    justifyContent: 'left',
                    alignItems: 'center',
                    width: '100%',
                    minWidth: '10px',
                    maxWidth: '400px',
                    px:1.5,
                  }}
                >
                  <img
                    src={isActive ? item.activeIcon : item.icon}
                    alt={`${item.title} Icon`}
                    style={{
                      width: 'calc(1.7vw)',
                      height: 'calc(1.7vw)',
                    }}
                  />
                  <Typography
                    sx={{
                      fontSize: 'calc(0.9vw)',
                      color: isActive
                        ? theme.palette.primary.contrastText
                        : theme.palette.primary.main,
                      fontWeight: isActive ? 700 : 400,
                      lineHeight: '1',
                      marginLeft: 'calc(0.5vw)',
                    }}
                  >{item.title}</Typography>
                </ListItemIcon>
              </ListItem>
            )
          })}
        </List>
      </Box>
    </Box>
  )
}

export default Sidebar
