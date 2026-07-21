import React, { useState, useEffect, useContext } from 'react';
import {
  Search,
  FileText,
  ShieldCheck,
  MessageSquareText,
  FolderOpen,
  Home,
  ChevronDown,
  ChevronRight,
  Bot,
  UserPlus,
  LogOut,
  BarChart3,
  Newspaper,
  ClipboardList,
  WalletCards,
  Bell,
} from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import { notificationService } from '../services/notificationService';

const routeMap = {
  home: '/',
  search: '/search',
  draft: '/draft-document',
  compliance: '/compliance/chat',
  'compliance-chat': '/compliance/chat',
  'compliance-documents': '/compliance/documents',
  'compliance-logs': '/compliance/logs',
  'chat-general': '/chat-general',
  newsletter: '/newsletter',
  notifications: '/notifications',
  accessi: '/accessi',
  usage: '/usage/utilizzo',
  'usage-utilizzo': '/usage/utilizzo',
  'usage-wallet': '/usage/wallet',
} as const;

type RouteKey = keyof typeof routeMap;

type SvgIconComponent = React.ComponentType<React.SVGProps<SVGSVGElement> & { size?: number | string }>;

const complianceTabs: { key: RouteKey; label: string; Icon: SvgIconComponent }[] = [
  { key: 'compliance-chat', label: 'Agente Vera', Icon: MessageSquareText },
  { key: 'compliance-documents', label: 'Documenti', Icon: FolderOpen },
  { key: 'compliance-logs', label: 'Log', Icon: ClipboardList },
];

const usageTabs: { key: RouteKey; label: string; Icon: SvgIconComponent }[] = [
  { key: 'usage-utilizzo', label: 'Utilizzo', Icon: BarChart3 },
  { key: 'usage-wallet', label: 'Wallet', Icon: WalletCards },
];

type SidebarProps = {
  onCollapseChange?: (collapsed: boolean) => void;
};

const Sidebar: React.FC<SidebarProps> = ({ onCollapseChange }) => {
  const auth = useContext(AuthContext);
  const userFirst = auth?.user?.first_name || '';
  const userLast = auth?.user?.last_name || '';
  const userName = (userFirst || userLast)
    ? `${userFirst} ${userLast}`.trim()
    : auth?.user?.username || 'Utente';
  const usernameOrFirst = userFirst || auth?.user?.username || '';
  const userInitial = usernameOrFirst ? usernameOrFirst.charAt(0).toUpperCase() : 'U';

  const navigate = useNavigate();
  const location = useLocation();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isComplianceOpen, setIsComplianceOpen] = useState(false);
  const [isUsageOpen, setIsUsageOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    if (location.pathname.startsWith('/compliance')) setIsComplianceOpen(true);
    if (location.pathname.startsWith('/usage')) setIsUsageOpen(true);
  }, [location.pathname]);

  useEffect(() => {
    if (onCollapseChange) onCollapseChange(isCollapsed);
  }, [isCollapsed, onCollapseChange]);

  // Poll unread notifications count every 30 seconds
  useEffect(() => {
    const fetchCount = () => {
      notificationService.getUnreadCount().then(setUnreadCount).catch(() => {});
    };
    fetchCount();
    const interval = setInterval(fetchCount, 30_000);
    const onFocus = () => fetchCount();
    window.addEventListener('focus', onFocus);
    return () => {
      clearInterval(interval);
      window.removeEventListener('focus', onFocus);
    };
  }, []);

  // Reset count when visiting notifications page
  useEffect(() => {
    if (location.pathname === '/notifications') {
      setTimeout(() => {
        notificationService.getUnreadCount().then(setUnreadCount).catch(() => {});
      }, 800);
    }
  }, [location.pathname]);

  const handleNav = (tab: RouteKey) => {
    const route = routeMap[tab];
    if (route) navigate(route);
  };

  const isActive = (tab: RouteKey) => location.pathname === routeMap[tab];
  const isComplianceActive = location.pathname.startsWith('/compliance');
  const isUsageActive = location.pathname.startsWith('/usage');

  const handleLogout = () => {
    auth?.logout();
    navigate('/login');
  };

  const navItem = (active: boolean, collapsed: boolean) =>
    `w-full flex items-center gap-3 transition-all duration-200 rounded-xl
     ${collapsed ? 'justify-center py-3 px-2 mx-0' : 'px-3 py-2.5 mx-2'}
     ${active
       ? 'bg-white/10 text-white'
       : 'text-blue-200/70 hover:bg-white/5 hover:text-blue-100'}`;

  const subNavItem = (active: boolean) =>
    `w-full flex items-center gap-2.5 px-3 py-2 rounded-xl transition-all duration-200
     ml-6 mr-2 text-[12px] font-medium
     ${active
       ? 'bg-white/10 text-white'
       : 'text-blue-200/60 hover:bg-white/5 hover:text-blue-100'}`;

  const iconSize = isCollapsed ? 20 : 17;
  const subIconSize = 14;

  return (
    <div
      className={`${isCollapsed ? 'w-20' : 'w-64'} bg-[#1e3a8a] text-white h-screen flex flex-col fixed left-0 top-0 z-20 transition-[width] duration-200`}
    >
      {/* Logo */}
      <div
        className="bg-[#172554] flex items-center cursor-pointer select-none px-5"
        style={{ height: 72 }}
        onClick={() => setIsCollapsed(!isCollapsed)}
        title={isCollapsed ? 'Espandi sidebar' : 'Comprimi sidebar'}
      >
        {isCollapsed ? (
          <div className="flex items-center justify-center w-full">
            <span className="block rounded-full" style={{ width: 10, height: 10, background: '#1b9162' }} />
          </div>
        ) : (
          <img src="/logo-dark.svg" alt="Refink" style={{ height: 38, width: 'auto', display: 'block' }} />
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-5 flex flex-col gap-0.5 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">

        {/* Home */}
        <button onClick={() => handleNav('home')} title={isCollapsed ? 'Home' : undefined} className={navItem(isActive('home'), isCollapsed)}>
          <Home size={iconSize} />
          {!isCollapsed && <span className="text-[13px] font-medium">Home</span>}
        </button>

        {!isCollapsed && <div className="h-px bg-blue-800/40 mx-5 my-2" />}

        {/* Ricerca documentale */}
        <button onClick={() => handleNav('search')} title={isCollapsed ? 'Ricerca documentale' : undefined} className={navItem(isActive('search'), isCollapsed)}>
          <Search size={iconSize} />
          {!isCollapsed && <span className="text-[13px] font-medium">Ricerca documentale</span>}
        </button>

        {/* Draft Document */}
        <button onClick={() => handleNav('draft')} title={isCollapsed ? 'Draft Document' : undefined} className={navItem(isActive('draft'), isCollapsed)}>
          <FileText size={iconSize} />
          {!isCollapsed && <span className="text-[13px] font-medium">Draft Document</span>}
        </button>

        {/* Check compliance (dropdown) */}
        <div>
          <button
            onClick={() => {
              setIsComplianceOpen(!isComplianceOpen);
              if (!isComplianceOpen && !isComplianceActive) navigate(routeMap['compliance-chat']);
            }}
            title={isCollapsed ? 'Check compliance' : undefined}
            className={`w-full flex items-center transition-all duration-200 rounded-xl
              ${isCollapsed ? 'justify-center py-3 px-2 mx-0' : 'px-3 py-2.5 mx-2 justify-between'}
              ${isComplianceActive ? 'bg-white/10 text-white' : 'text-blue-200/70 hover:bg-white/5 hover:text-blue-100'}`}
          >
            <div className="flex items-center gap-3">
              <ShieldCheck size={iconSize} />
              {!isCollapsed && <span className="text-[13px] font-medium">Check compliance</span>}
            </div>
            {!isCollapsed && (isComplianceOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />)}
          </button>
          {isComplianceOpen && (
            <div className="mt-0.5 flex flex-col gap-0.5">
              {complianceTabs.map(tab => (
                <button
                  key={tab.key}
                  title={isCollapsed ? tab.label : undefined}
                  onClick={() => handleNav(tab.key)}
                  className={isCollapsed ? navItem(isActive(tab.key), true) : subNavItem(isActive(tab.key))}
                >
                  <tab.Icon size={subIconSize} />
                  {!isCollapsed && tab.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Chat Assistant */}
        <button onClick={() => handleNav('chat-general')} title={isCollapsed ? 'Chat Assistant' : undefined} className={navItem(isActive('chat-general'), isCollapsed)}>
          <Bot size={iconSize} />
          {!isCollapsed && <span className="text-[13px] font-medium">Chat Assistant</span>}
        </button>

        {/* Newsletter */}
        <button onClick={() => handleNav('newsletter')} title={isCollapsed ? 'Newsletter' : undefined} className={navItem(isActive('newsletter'), isCollapsed)}>
          <Newspaper size={iconSize} />
          {!isCollapsed && <span className="text-[13px] font-medium">Newsletter</span>}
        </button>

        {/* Notifiche */}
        <button
          onClick={() => handleNav('notifications')}
          title={isCollapsed ? 'Notifiche' : undefined}
          className={`${navItem(isActive('notifications'), isCollapsed)} relative`}
        >
          <div className="relative">
            <Bell size={iconSize} />
            {unreadCount > 0 && (
              <span className={`absolute flex items-center justify-center rounded-full bg-red-500 text-white font-bold leading-none
                ${isCollapsed ? '-top-1.5 -right-1.5 w-4 h-4 text-[9px]' : '-top-1 -right-1.5 w-4 h-4 text-[9px]'}`}>
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </div>
          {!isCollapsed && (
            <span className="text-[13px] font-medium flex-1 text-left">Notifiche</span>
          )}
        </button>

      </nav>

      {/* Bottom section */}
      <div className="pb-2">
        {!isCollapsed && <div className="h-px bg-blue-800/40 mx-5 mb-2" />}

        <div className="flex flex-col gap-0.5">
          <div>
            <button
              onClick={() => {
                setIsUsageOpen(!isUsageOpen);
                if (!isUsageOpen && !isUsageActive) navigate(routeMap['usage-utilizzo']);
              }}
              title={isCollapsed ? 'Consumo AI' : undefined}
              className={`w-full flex items-center transition-all duration-200 rounded-xl
                ${isCollapsed ? 'justify-center py-3 px-2 mx-0' : 'px-3 py-2.5 mx-2 justify-between'}
                ${isUsageActive ? 'bg-white/10 text-white' : 'text-blue-200/70 hover:bg-white/5 hover:text-blue-100'}`}
            >
              <div className="flex items-center gap-3">
                <BarChart3 size={iconSize} />
                {!isCollapsed && <span className="text-[13px] font-medium">Consumo AI</span>}
              </div>
              {!isCollapsed && (isUsageOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />)}
            </button>
            {isUsageOpen && (
              <div className="mt-0.5 flex flex-col gap-0.5">
                {usageTabs.map(tab => (
                  <button
                    key={tab.key}
                    title={isCollapsed ? tab.label : undefined}
                    onClick={() => handleNav(tab.key)}
                    className={isCollapsed ? navItem(isActive(tab.key), true) : subNavItem(isActive(tab.key))}
                  >
                    <tab.Icon size={subIconSize} />
                    {!isCollapsed && tab.label}
                  </button>
                ))}
              </div>
            )}
          </div>

          <button onClick={() => handleNav('accessi')} title={isCollapsed ? 'Accessi' : undefined} className={navItem(isActive('accessi'), isCollapsed)}>
            <UserPlus size={iconSize} />
            {!isCollapsed && <span className="text-[13px] font-medium">Accessi</span>}
          </button>
        </div>

        {!isCollapsed && <div className="h-px bg-blue-800/40 mx-5 my-2" />}

        <div
          onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
          className={`flex items-center gap-3 cursor-pointer transition-colors rounded-xl mx-2 px-3 py-2.5 hover:bg-white/5 ${isCollapsed ? 'justify-center' : ''}`}
        >
          <div className="w-8 h-8 rounded-full bg-[#172554] border border-blue-700 flex items-center justify-center text-white font-semibold text-sm shrink-0">
            {userInitial}
          </div>
          {!isCollapsed && (
            <>
              <span className="text-[13px] font-medium text-blue-100 truncate flex-1">{userName}</span>
              <LogOut size={14} className="text-blue-300/60 shrink-0" />
            </>
          )}
        </div>

        {isUserMenuOpen && !isCollapsed && (
          <div className="mx-2 mb-1">
            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-2 px-3 py-2 text-xs font-medium text-red-300 hover:text-white hover:bg-red-500/20 rounded-lg transition-colors"
            >
              <LogOut size={13} />
              Disconnetti
            </button>
          </div>
        )}

        {!isCollapsed && (
          <div className="flex flex-col items-center gap-1.5 py-3 mt-1">
            <div className="flex items-center gap-[5px]">
              <span className="block rounded-full" style={{ width: 5, height: 5, background: '#365142' }} />
              <span className="block rounded-full" style={{ width: 5, height: 5, background: '#1b9162' }} />
              <span className="block rounded-full" style={{ width: 5, height: 5, background: '#4ade80' }} />
            </div>
            <p className="text-[10px] text-blue-400/50 text-center">Refink Suite v2.4.0</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default Sidebar;
