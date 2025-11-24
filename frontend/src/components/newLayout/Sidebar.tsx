
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

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ activeTab, setActiveTab }) => {
  const [isSegreteriaOpen, setIsSegreteriaOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);

  // Auto-open submenu if a child is active
  useEffect(() => {
    if (activeTab.startsWith('seg-')) {
      setIsSegreteriaOpen(true);
    }
  }, [activeTab]);

  const toggleSegreteria = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsSegreteriaOpen(!isSegreteriaOpen);
    if (!isSegreteriaOpen && !activeTab.startsWith('seg-')) {
        setActiveTab('seg-dashboard');
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
          onClick={() => setActiveTab('home')}
          className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 mb-4 ${
            activeTab === 'home' 
              ? 'bg-[#172554] text-white border-l-4 border-[#15803d]' 
              : 'text-blue-200 hover:bg-blue-800/50 hover:text-white'
          }`}
        >
          <Home size={20} />
          <span className="font-medium">Home</span>
        </button>

        <div className="px-4 py-2 text-xs font-bold text-blue-300 uppercase tracking-wider opacity-70">
            Strumenti
        </div>

        <button
          onClick={() => setActiveTab('search')}
          className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 ${
            activeTab === 'search' 
              ? 'bg-[#172554] text-white border-l-4 border-[#15803d]' 
              : 'text-blue-200 hover:bg-blue-800/50 hover:text-white'
          }`}
        >
          <Search size={20} />
          <span className="font-medium">Ricerca documentale</span>
        </button>

        <button
          onClick={() => setActiveTab('compliance')}
          className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 ${
            activeTab === 'compliance' 
              ? 'bg-[#172554] text-white border-l-4 border-[#15803d]' 
              : 'text-blue-200 hover:bg-blue-800/50 hover:text-white'
          }`}
        >
          <ShieldCheck size={20} />
          <span className="font-medium">Check compliance</span>
        </button>

        <button
          onClick={() => setActiveTab('chat-general')}
          className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 ${
            activeTab === 'chat-general' 
              ? 'bg-[#172554] text-white border-l-4 border-[#15803d]' 
              : 'text-blue-200 hover:bg-blue-800/50 hover:text-white'
          }`}
        >
          <Bot size={20} />
          <span className="font-medium">Chat Assistant</span>
        </button>

        {/* Dropdown Group - Removed pt-2 to align with other items */}
        <div>
            <button
            onClick={toggleSegreteria}
            className={`w-full flex items-center justify-between px-4 py-3 rounded-lg transition-all duration-200 ${
                activeTab.startsWith('seg-') 
                ? 'bg-[#172554] text-white' 
                : 'text-blue-200 hover:bg-blue-800/50 hover:text-white'
            }`}
            >
                <div className="flex items-center gap-3">
                    <Briefcase size={20} />
                    <span className="font-medium">Segreteria Societaria</span>
                </div>
                {isSegreteriaOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            </button>

            {isSegreteriaOpen && (
                <div className="mt-1 ml-4 space-y-1 border-l border-blue-700 pl-2">
                     <button
                        onClick={() => setActiveTab('seg-dashboard')}
                        className={`w-full flex items-center gap-3 px-4 py-2 rounded-lg text-sm transition-all duration-200 ${
                            activeTab === 'seg-dashboard' 
                            ? 'text-[#4ade80] font-semibold bg-blue-900/50' 
                            : 'text-blue-300 hover:text-white'
                        }`}
                    >
                        <LayoutDashboard size={16} />
                        Dashboard
                    </button>
                    <button
                        onClick={() => setActiveTab('seg-companies')}
                        className={`w-full flex items-center gap-3 px-4 py-2 rounded-lg text-sm transition-all duration-200 ${
                            activeTab === 'seg-companies' 
                            ? 'text-[#4ade80] font-semibold bg-blue-900/50' 
                            : 'text-blue-300 hover:text-white'
                        }`}
                    >
                        <Building2 size={16} />
                        Società
                    </button>
                    <button
                        onClick={() => setActiveTab('seg-documents')}
                        className={`w-full flex items-center gap-3 px-4 py-2 rounded-lg text-sm transition-all duration-200 ${
                            activeTab === 'seg-documents' 
                            ? 'text-[#4ade80] font-semibold bg-blue-900/50' 
                            : 'text-blue-300 hover:text-white'
                        }`}
                    >
                        <FileText size={16} />
                        Documenti AI
                    </button>
                    <button
                        onClick={() => setActiveTab('seg-assistant')}
                        className={`w-full flex items-center gap-3 px-4 py-2 rounded-lg text-sm transition-all duration-200 ${
                            activeTab === 'seg-assistant' 
                            ? 'text-[#4ade80] font-semibold bg-blue-900/50' 
                            : 'text-blue-300 hover:text-white'
                        }`}
                    >
                        <Bot size={16} />
                        Assistente Legale
                    </button>
                </div>
            )}
        </div>
      </nav>

      {/* Accessi Button (Moved to Bottom) */}
      <div className="px-3 py-2 border-t border-blue-800 bg-[#1e3a8a]">
          <button
            onClick={() => setActiveTab('accessi')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 ${
              activeTab === 'accessi' 
                ? 'bg-[#172554] text-white border-l-4 border-[#15803d]' 
                : 'text-blue-200 hover:bg-blue-800/50 hover:text-white'
            }`}
          >
            <UserPlus size={20} />
            <span className="font-medium">Accessi</span>
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
                <p className="text-sm font-medium text-white truncate">rbyc_admin</p>
                <p className="text-[10px] text-blue-300 truncate">Amministratore</p>
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
