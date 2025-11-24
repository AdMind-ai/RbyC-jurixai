import React, { useState, useEffect } from 'react';
import { 
  LayoutDashboard, 
  Building2, 
  FileText, 
  Bot, 
  Search, 
  ShieldCheck, 
  Home, 
  ChevronDown, 
  ChevronRight,
  Briefcase,
  UserPlus,
  LogOut
} from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';

const routeMap = {
  home: '/',
  search: '/search',
  compliance: '/compliance',
  'chat-general': '/chat-general',
  accessi: '/accessi',
  'seg-dashboard': '/segreteria/dashboard',
  'seg-companies': '/segreteria/companies',
  'seg-documents': '/segreteria/documents',
  'seg-assistant': '/segreteria/assistant',
} as const;

type RouteKey = keyof typeof routeMap;

const segreteriaTabs: { key: RouteKey; label: string; icon: React.ReactElement }[] = [
  { key: 'seg-dashboard', label: 'Dashboard', icon: <LayoutDashboard size={16} /> },
  { key: 'seg-companies', label: 'Società', icon: <Building2 size={16} /> },
  { key: 'seg-documents', label: 'Documenti AI', icon: <FileText size={16} /> },
  { key: 'seg-assistant', label: 'Assistente Legale', icon: <Bot size={16} /> },
];

const Sidebar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [isSegreteriaOpen, setIsSegreteriaOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);

  // Open Segreteria if current route matches
  useEffect(() => {
    if (location.pathname.startsWith('/seg-')) {
      setIsSegreteriaOpen(true);
    }
  }, [location.pathname]);

  const handleNav = (tab: RouteKey) => {
    const route = routeMap[tab];
    if (route) navigate(route);
  };

  const toggleSegreteria = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsSegreteriaOpen(!isSegreteriaOpen);
    if (!isSegreteriaOpen && !location.pathname.startsWith('/seg-')) {
      navigate(routeMap['seg-dashboard']);
    }
  };

  return (
    <div className="w-64 bg-[#1e3a8a] text-white h-screen flex flex-col fixed left-0 top-0 shadow-2xl z-20 border-r border-blue-900">
      {/* Logo Section */}
      <div className="p-6 border-b border-blue-800 bg-[#172554]">
        <div className="flex items-center gap-2 mb-1">
           <span className="text-3xl font-light tracking-tight">Re<span className="font-bold">fink</span></span>
        </div>
        <div className="flex items-center gap-1">
            <div className="h-px w-8 bg-[#15803d]"></div>
            <p className="text-[10px] uppercase tracking-wider text-slate-300">Powered by <span className="font-bold text-white">CONSILIA</span></p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-6 px-3 space-y-1 overflow-y-auto">
        <button
          onClick={() => handleNav('home')}
          className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 mb-4 ${
            location.pathname === routeMap['home']
              ? 'bg-[#172554] text-white border-l-4 border-[#15803d]'
              : 'text-blue-200 hover:bg-blue-800/50 hover:text-white'
          }`}
        >
          <Home size={20} />
          <span className="font-medium text-sm">Home</span>
        </button>

        <div className="px-4 py-2 text-[11px] font-bold text-blue-300 uppercase tracking-wider opacity-70">
          Strumenti
        </div>

        <button
          onClick={() => handleNav('search')}
          className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 ${
            location.pathname === routeMap['search']
              ? 'bg-[#172554] text-white border-l-4 border-[#15803d]'
              : 'text-blue-200 hover:bg-blue-800/50 hover:text-white'
          }`}
        >
          <Search size={20} />
          <span className="font-medium text-sm">Ricerca documentale</span>
        </button>

        <button
          onClick={() => handleNav('compliance')}
          className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 ${
            location.pathname === routeMap['compliance']
              ? 'bg-[#172554] text-white border-l-4 border-[#15803d]'
              : 'text-blue-200 hover:bg-blue-800/50 hover:text-white'
          }`}
        >
          <ShieldCheck size={20} />
          <span className="font-medium text-sm">Check compliance</span>
        </button>

        <button
          onClick={() => handleNav('chat-general')}
          className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 ${
            location.pathname === routeMap['chat-general']
              ? 'bg-[#172554] text-white border-l-4 border-[#15803d]'
              : 'text-blue-200 hover:bg-blue-800/50 hover:text-white'
          }`}
        >
          <Bot size={20} />
          <span className="font-medium text-sm">Chat Assistant</span>
        </button>

        {/* Dropdown Group */}
        <div>
          <button
            onClick={toggleSegreteria}
            className={`w-full flex items-center justify-between px-4 py-3 rounded-lg transition-all duration-200 ${
              location.pathname.startsWith('/seg-')
                ? 'bg-[#172554] text-white'
                : 'text-blue-200 hover:bg-blue-800/50 hover:text-white'
            }`}
          >
            <div className="flex items-center gap-3">
              <Briefcase size={20} />
              <span className="font-medium text-sm">Segreteria Societaria</span>
            </div>
            {isSegreteriaOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          </button>

          {isSegreteriaOpen && (
            <div className="mt-1 ml-4 space-y-1 border-l border-blue-700 pl-2">
              {segreteriaTabs.map(tab => (
                <button
                  key={tab.key}
                  onClick={() => handleNav(tab.key)}
                  className={`w-full flex items-center gap-3 px-4 py-2 rounded-lg text-xs transition-all duration-200 ${
                    location.pathname === routeMap[tab.key]
                      ? 'text-[#4ade80] font-semibold bg-blue-900/50'
                      : 'text-blue-300 hover:text-white'
                  }`}
                >
                  {tab.icon}
                  <span className="text-xs font-medium">{tab.label}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </nav>

      {/* Accessi Button */}
      <div className="px-3 py-2 border-t border-blue-800 bg-[#1e3a8a]">
        <button
          onClick={() => handleNav('accessi')}
          className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 ${
            location.pathname === routeMap['accessi']
              ? 'bg-[#172554] text-white border-l-4 border-[#15803d]'
              : 'text-blue-200 hover:bg-blue-800/50 hover:text-white'
          }`}
        >
          <UserPlus size={20} />
          <span className="font-medium text-sm">Accessi</span>
        </button>
      </div>

      {/* User Profile Section */}
      <div className="border-t border-blue-800 bg-[#172554] p-4">
        <div 
          onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
          className="flex items-center gap-3 cursor-pointer hover:bg-[#1e3a8a] p-2 rounded-lg transition-colors"
        >
          <div className="w-9 h-9 bg-[#15803d] rounded-full flex items-center justify-center text-white font-bold text-sm shadow-sm border-2 border-blue-900">
            R
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-white truncate">rbyc_admin</p>
            <p className="text-[9px] text-blue-300 truncate">Amministratore</p>
          </div>
          {isUserMenuOpen ? <ChevronDown size={16} className="text-blue-300" /> : <ChevronRight size={16} className="text-blue-300" />}
        </div>

        {isUserMenuOpen && (
          <div className="mt-2 space-y-1 animate-fade-in">
            <button 
              onClick={() => console.log('Logout clicked')}
              className="w-full flex items-center gap-2 px-3 py-2 text-xs font-medium text-red-300 hover:text-white hover:bg-red-500/20 rounded-lg transition-colors"
            >
              <LogOut size={14} />
              Disconnetti
            </button>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="py-2 bg-[#172554] text-[10px] text-blue-400 text-center border-t border-blue-800">
        Refink Suite v2.4.0
      </div>
    </div>
  );
};

export default Sidebar;
 