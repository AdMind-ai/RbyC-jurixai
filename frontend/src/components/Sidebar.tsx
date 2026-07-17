import React, { useState, useEffect, useContext } from 'react';
import {
  LayoutDashboard,
  Building2,
  FileText,
  Bot,
  Search,
  ShieldCheck,
  MessageSquareText,
  FolderOpen,
  Home,
  ChevronRight,
  ChevronDown,
  Briefcase,
  UserPlus,
  LogOut,
  BarChart3
} from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import Logo from '../assets/logo.png';
import CollapsedIcon from '../assets/collapsed-icon.svg';

const routeMap = {
  home: '/',
  search: '/search',
  draft: '/draft-document',
  compliance: '/compliance/chat',
  'compliance-chat': '/compliance/chat',
  'compliance-documents': '/compliance/documents',
  'chat-general': '/chat-general',
  accessi: '/accessi',
  usage: '/usage',
  'seg-dashboard': '/segreteria/dashboard',
  'seg-companies': '/segreteria/companies',
  'seg-documents': '/segreteria/documents',
  'seg-assistant': '/segreteria/assistant',
} as const;

type RouteKey = keyof typeof routeMap;

type SvgIconComponent = React.ComponentType<React.SVGProps<SVGSVGElement> & { size?: number | string }>;

const segreteriaTabs: { key: RouteKey; label: string; Icon: SvgIconComponent }[] = [
  { key: 'seg-dashboard', label: 'Dashboard', Icon: LayoutDashboard },
  { key: 'seg-companies', label: 'Società', Icon: Building2 },
  { key: 'seg-documents', label: 'Documenti AI', Icon: FileText },
  { key: 'seg-assistant', label: 'Assistente Legale', Icon: Bot },
];

const complianceTabs: { key: RouteKey; label: string; Icon: SvgIconComponent }[] = [
  { key: 'compliance-chat', label: 'Chat', Icon: MessageSquareText },
  { key: 'compliance-documents', label: 'Documenti', Icon: FolderOpen },
];

type SidebarProps = {
  onCollapseChange?: (collapsed: boolean) => void;
};

const Sidebar: React.FC<SidebarProps> = ({ onCollapseChange }) => {
  const auth = useContext(AuthContext);
  const userFirst = auth?.user?.first_name || '';
  const userLast = auth?.user?.last_name || '';
  const userName = (userFirst || userLast) ? `${userFirst} ${userLast}`.trim() : (auth?.user?.username || 'User');
  const usernameOrFirst = userFirst || auth?.user?.username || '';
  const userInitial = usernameOrFirst ? usernameOrFirst.charAt(0).toUpperCase() : 'U';
  const userRole = auth?.user?.is_admin ? "Amministratore" : "Standard";


  const navigate = useNavigate();
  const location = useLocation();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isSegreteriaOpen, setIsSegreteriaOpen] = useState(false);
  const [isComplianceOpen, setIsComplianceOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);

  // Open Segreteria if current route matches
  useEffect(() => {
    if (location.pathname.startsWith('/segreteria') || location.pathname.startsWith('/seg-')) {
      setIsSegreteriaOpen(true);
    }
  }, [location.pathname]);

  useEffect(() => {
    if (location.pathname.startsWith('/compliance')) {
      setIsComplianceOpen(true);
    }
  }, [location.pathname]);

  useEffect(() => {
    // if user navigates to segreteria route while collapsed, keep collapsed state but
    // ensure segreteria section doesn't auto-expand visually (we keep state as-is)
  }, [isCollapsed]);

  const handleNav = (tab: RouteKey) => {
    const route = routeMap[tab];
    if (route) navigate(route);
  };

  const toggleSegreteria = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsSegreteriaOpen(!isSegreteriaOpen);
    if (!isSegreteriaOpen && !(location.pathname.startsWith('/segreteria') || location.pathname.startsWith('/seg-'))) {
      navigate(routeMap['seg-dashboard']);
    }
  };

  const toggleCompliance = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsComplianceOpen(!isComplianceOpen);
    if (!isComplianceOpen && !location.pathname.startsWith('/compliance')) {
      navigate(routeMap['compliance-chat']);
    }
  };

  const toggleCollapse = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsCollapsed(!isCollapsed);
  };

  useEffect(() => {
    if (onCollapseChange) onCollapseChange(isCollapsed);
  }, [isCollapsed, onCollapseChange]);

  const iconSize = isCollapsed ? 24 : 20;
  const subIconSize = isCollapsed ? 20 : 16;

  const handleLogout = () => {
    auth?.logout();
    navigate("/login");
  };

  return (
    <div className={`${isCollapsed ? 'w-24' : 'w-64'} bg-[#1e3a8a] text-white h-screen flex flex-col fixed left-0 top-0 shadow-2xl z-20 border-r border-blue-900 transition-[width] duration-200`}>
      {/* Logo Section */}
      <div className={`relative border-b border-blue-800 bg-[#172554] ${isCollapsed ? 'py-4' : 'p-6'}`}>
        {!isCollapsed ? (
          <>
            <img src={Logo} alt="Refink Logo" className="w-32 mx-auto" />
            <button
              onClick={toggleCollapse}
              title={isCollapsed ? 'Apri sidebar' : 'Comprimi sidebar'}
              className="absolute right-2 top-2 p-1 rounded-md text-blue-200 hover:text-white hover:bg-blue-800/30 flex items-center justify-center"
            >
              <img src={CollapsedIcon} alt="" className="w-5 h-5" />
            </button>
          </>
        ) : (
          <div className="flex items-center justify-center h-full">
            <button
              onClick={toggleCollapse}
              title={isCollapsed ? 'Apri sidebar' : 'Comprimi sidebar'}
              className="p-1 rounded-md text-blue-200 hover:text-white hover:bg-blue-800/30 flex items-center justify-center"
            >
              <img src={CollapsedIcon} alt="" className="w-5 h-5" />
            </button>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className={`flex-1 overflow-y-auto ${isCollapsed ? 'pt-4 px-1' : 'py-6 px-3 space-y-1'}`}>
        <button
          onClick={() => handleNav('home')}
          title={isCollapsed ? 'Home' : undefined}
          className={`w-full flex items-center gap-3 ${isCollapsed ? 'justify-center py-3' : 'px-4 py-3'} rounded-lg transition-all duration-200 mb-4 ${location.pathname === routeMap['home']
            ? 'bg-[#172554] text-white border-l-4 border-[#15803d]'
            : 'text-blue-200 hover:bg-blue-800/50 hover:text-white'
            }`}
        >
          <Home size={iconSize} />
          <span className={`${isCollapsed ? 'hidden' : 'font-medium text-sm'}`}>Home</span>
        </button>

        <div className={`${isCollapsed ? 'hidden' : 'px-4 py-2 text-[11px] font-bold text-blue-300 uppercase tracking-wider opacity-70'}`}>
          Strumenti
        </div>

        <button
          onClick={() => handleNav('search')}
          title={isCollapsed ? 'Ricerca documentale' : undefined}
          className={`w-full flex items-center gap-3 ${isCollapsed ? 'justify-center py-3' : 'px-4 py-3'} rounded-lg transition-all duration-200 ${location.pathname === routeMap['search']
            ? 'bg-[#172554] text-white border-l-4 border-[#15803d]'
            : 'text-blue-200 hover:bg-blue-800/50 hover:text-white'
            }`}
        >
          <Search size={iconSize} />
          <span className={`${isCollapsed ? 'hidden' : 'font-medium text-sm'}`}>Ricerca documentale</span>
        </button>

        <button
          onClick={() => handleNav('draft')}
          title={isCollapsed ? 'Draft Document' : undefined}
          className={`w-full flex items-center gap-3 ${isCollapsed ? 'justify-center py-3' : 'px-4 py-3'} rounded-lg transition-all duration-200 ${location.pathname === routeMap['draft']
            ? 'bg-[#172554] text-white border-l-4 border-[#15803d]'
            : 'text-blue-200 hover:bg-blue-800/50 hover:text-white'
            }`}
        >
          <FileText size={iconSize} />
          <span className={`${isCollapsed ? 'hidden' : 'font-medium text-sm'}`}>Draft Document</span>
        </button>

        <div>
          <button
            onClick={toggleCompliance}
            title={isCollapsed ? 'Check compliance' : undefined}
            className={`w-full flex items-center ${isCollapsed ? 'justify-center py-3' : 'justify-between px-4 py-3'} rounded-lg transition-all duration-200 ${location.pathname.startsWith('/compliance')
              ? 'bg-[#172554] text-white border-l-4 border-[#15803d]'
              : 'text-blue-200 hover:bg-blue-800/50 hover:text-white'
              }`}
          >
            <div className="flex items-center gap-3">
              <ShieldCheck size={iconSize} />
              <span className={`${isCollapsed ? 'hidden' : 'font-medium text-sm'}`}>Check compliance</span>
            </div>
            {!isCollapsed && (isComplianceOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />)}
          </button>

          {isComplianceOpen && (
            <div className={`${isCollapsed ? 'mt-1 ml-0 space-y-1' : 'mt-1 ml-4 space-y-1 border-l border-blue-700 pl-2'}`}>
              {complianceTabs.map(tab => (
                <button
                  key={tab.key}
                  title={isCollapsed ? tab.label : undefined}
                  onClick={() => handleNav(tab.key)}
                  className={`w-full flex items-center gap-3 ${isCollapsed ? 'justify-center py-3' : 'px-4 py-2'} rounded-lg text-xs transition-all duration-200 ${location.pathname === routeMap[tab.key]
                    ? 'text-[#4ade80] font-semibold bg-blue-900/50'
                    : 'text-blue-300 hover:text-white'
                    }`}
                >
                  <tab.Icon size={subIconSize} />
                  <span className={`${isCollapsed ? 'hidden' : 'text-xs font-medium'}`}>{tab.label}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        <button
          onClick={() => handleNav('chat-general')}
          title={isCollapsed ? 'Chat Assistant' : undefined}
          className={`w-full flex items-center gap-3 ${isCollapsed ? 'justify-center py-3' : 'px-4 py-3'} rounded-lg transition-all duration-200 ${location.pathname === routeMap['chat-general']
            ? 'bg-[#172554] text-white border-l-4 border-[#15803d]'
            : 'text-blue-200 hover:bg-blue-800/50 hover:text-white'
            }`}
        >
          <Bot size={iconSize} />
          <span className={`${isCollapsed ? 'hidden' : 'font-medium text-sm'}`}>Chat Assistant</span>
        </button>

        {/* Segreteria Societaria - nascosta temporaneamente */}
      </nav>

      {/* Accessi & Usage Buttons */}
      <div className={`border-t border-blue-800 bg-[#1e3a8a] ${isCollapsed ? 'py-2 px-1' : 'px-3 py-2'} space-y-2`}>
        <button
          onClick={() => handleNav('usage')}
          title={isCollapsed ? 'Usage' : undefined}
          className={`w-full flex items-center gap-3 ${isCollapsed ? 'justify-center py-3' : 'px-4 py-3'} rounded-lg transition-all duration-200 ${location.pathname === routeMap['usage']
            ? 'bg-[#172554] text-white border-l-4 border-[#15803d]'
            : 'text-blue-200 hover:bg-blue-800/50 hover:text-white'
            }`}
        >
          <BarChart3 size={iconSize} />
          <span className={`${isCollapsed ? 'hidden' : 'font-medium text-sm'}`}>Consumo AI</span>
        </button>

        <button
          onClick={() => handleNav('accessi')}
          title={isCollapsed ? 'Accessi' : undefined}
          className={`w-full flex items-center gap-3 ${isCollapsed ? 'justify-center py-3' : 'px-4 py-3'} rounded-lg transition-all duration-200 ${location.pathname === routeMap['accessi']
            ? 'bg-[#172554] text-white border-l-4 border-[#15803d]'
            : 'text-blue-200 hover:bg-blue-800/50 hover:text-white'
            }`}
        >
          <UserPlus size={iconSize} />
          <span className={`${isCollapsed ? 'hidden' : 'font-medium text-sm'}`}>Accessi</span>
        </button>
      </div>

      {/* User Profile Section */}
      <div className={`border-t border-blue-800 bg-[#172554] ${isCollapsed ? 'py-3 px-2' : 'p-4'}`}>
        <div
          onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
          title={isCollapsed ? 'Profilo' : undefined}
          className={`flex items-center gap-3 cursor-pointer hover:bg-[#1e3a8a] p-2 rounded-lg transition-colors ${isCollapsed ? 'justify-center' : ''}`}
        >
          <div className={`${isCollapsed ? 'w-10 h-10' : 'w-9 h-9'} bg-[#15803d] rounded-full flex items-center justify-center text-white font-bold text-sm shadow-sm border-2 border-blue-900`}>
            {userInitial}
          </div>
          {!isCollapsed && (
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">{userName}</p>
              <p className="text-[12px] text-blue-300 truncate">{userRole}</p>
            </div>
          )}
          {!isCollapsed && (isUserMenuOpen ? <ChevronDown size={16} className="text-blue-300" /> : <ChevronRight size={16} className="text-blue-300" />)}
        </div>

        {isUserMenuOpen && (
          <div className="mt-2 space-y-1 animate-fade-in">
            <button
              onClick={handleLogout}
              title={isCollapsed ? 'Disconnetti' : ''}
              className={`w-full flex items-center gap-2 px-3 py-2 text-xs font-medium text-red-300 hover:text-white hover:bg-red-500/20 rounded-lg transition-colors ${isCollapsed ? 'justify-center' : ''}`}
            >
              <LogOut size={14} />
              {!isCollapsed && 'Disconnetti'}
            </button>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className={`py-2 bg-[#172554] text-[10px] text-blue-400 text-center border-t border-blue-800 ${isCollapsed ? 'text-xs' : ''}`}>
        {!isCollapsed ? 'Refink Suite v2.4.0' : ''}
      </div>
    </div>
  );
};

export default Sidebar;
