import React, { useState } from 'react';
import { 
  Search, 
  FileText, 
  ShieldCheck, 
  Bot, 
  ChevronDown,
  LogOut,
  Settings,
  User,
  Activity,
  History,
  Scale,
  Building,
  ArrowRight
} from 'lucide-react';

export default function Airy() {
  const [activeItem, setActiveItem] = useState('Ricerca documentale');
  const [isComplianceOpen, setIsComplianceOpen] = useState(true);

  const NavItem = ({ icon: Icon, label, isActive, hasSubmenu, isOpen, onToggle, isSubitem }: any) => {
    return (
      <div 
        className={`
          flex items-center justify-between cursor-pointer
          px-3 py-2.5 mx-2 rounded-xl transition-all duration-200
          ${isActive 
            ? 'bg-white/10 text-white' 
            : 'text-blue-200/70 hover:bg-white/5 hover:text-blue-100'
          }
          ${isSubitem ? 'ml-8 mr-2' : ''}
        `}
        onClick={hasSubmenu ? onToggle : () => setActiveItem(label)}
      >
        <div className={`flex items-center ${isSubitem ? 'gap-2' : 'gap-3'}`}>
          <Icon size={isSubitem ? 14 : 17} className={isActive ? 'text-white' : ''} />
          <span className={`${isSubitem ? 'text-[12px]' : 'text-[13px]'} font-medium`}>
            {label}
          </span>
        </div>
        {hasSubmenu && (
          <ChevronDown 
            size={14} 
            className={`transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
          />
        )}
      </div>
    );
  };

  return (
    <div className="flex w-[1280px] h-[800px] font-sans bg-slate-50 overflow-hidden text-slate-800">
      
      {/* Sidebar */}
      <div className="w-[256px] flex-shrink-0 bg-[#1e3a8a] flex flex-col justify-between">
        <div>
          {/* Logo Area */}
          <div className="h-[80px] bg-[#172554] flex flex-col justify-center px-6">
            <h1 className="text-xl font-light tracking-[0.15em] text-white leading-tight">
              REFINK
            </h1>
            <p className="text-[9px] tracking-wider text-blue-300/60 uppercase mt-0.5">
              powered by CONSILIA
            </p>
          </div>

          <div className="py-6 flex flex-col gap-1">
            <NavItem icon={Search} label="Ricerca documentale" isActive={activeItem === 'Ricerca documentale'} />
            <NavItem icon={FileText} label="Draft Document" isActive={activeItem === 'Draft Document'} />
            
            <div className="my-2 px-6">
              <div className="h-px w-full bg-blue-800/50"></div>
            </div>

            <NavItem 
              icon={ShieldCheck} 
              label="Check compliance" 
              hasSubmenu 
              isOpen={isComplianceOpen}
              onToggle={() => setIsComplianceOpen(!isComplianceOpen)}
              isActive={false}
            />
            
            {isComplianceOpen && (
              <div className="flex flex-col gap-1 mt-1 mb-2">
                <NavItem icon={Scale} label="Privacy & GDPR" isSubitem isActive={activeItem === 'Privacy & GDPR'} />
                <NavItem icon={Building} label="Modello 231" isSubitem isActive={activeItem === 'Modello 231'} />
              </div>
            )}
            
            <NavItem icon={Bot} label="Chat Assistant" isActive={activeItem === 'Chat Assistant'} />
          </div>
        </div>

        {/* Bottom Section */}
        <div>
          <div className="px-6 mb-3">
            <div className="h-px w-full bg-blue-800/50"></div>
          </div>
          
          <div className="flex flex-col gap-1 pb-4">
            <NavItem icon={Activity} label="Utilizzo mensile" isActive={activeItem === 'Utilizzo mensile'} />
            <NavItem icon={History} label="Storico accessi" isActive={activeItem === 'Storico accessi'} />
            
            <div className="px-6 my-2">
              <div className="h-px w-full bg-blue-800/50"></div>
            </div>
            
            {/* User Profile */}
            <div className="flex items-center gap-3 px-5 py-2 mx-2 cursor-pointer text-blue-200/70 hover:text-white transition-colors">
              <div className="w-8 h-8 rounded-full bg-[#172554] flex items-center justify-center text-white flex-shrink-0">
                <User size={15} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[13px] font-medium truncate">Mario Rossi</p>
              </div>
              <LogOut size={15} className="flex-shrink-0 hover:text-blue-100" />
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col bg-[#f8fafc] relative">
        {/* Top Stripe */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#1e3a8a] to-[#15803d]"></div>
        
        <div className="flex-1 overflow-y-auto pt-16 px-12 pb-12">
          
          <div className="max-w-3xl mx-auto">
            {/* Greeting */}
            <div className="mb-10">
              <p className="text-slate-400 text-sm font-medium mb-1">Buongiorno, Admin</p>
              <h2 className="text-2xl font-semibold text-slate-800">Cosa vuoi fare oggi?</h2>
            </div>

            {/* Cards Grid */}
            <div className="grid grid-cols-2 gap-6">
              
              {/* Card 1 */}
              <div className="bg-white p-8 rounded-2xl shadow-[0_1px_4px_rgba(0,0,0,0.06)] hover:shadow-[0_4px_16px_rgba(30,58,138,0.10)] transition-shadow duration-300 group cursor-pointer">
                <Search size={28} className="text-[#1e3a8a] mb-5" />
                <h3 className="text-base font-semibold text-slate-800 mb-2">Ricerca documentale</h3>
                <p className="text-[13px] text-slate-400 leading-relaxed mb-6 min-h-[40px]">
                  Cerca e analizza documenti nell'intero archivio.
                </p>
                <div className="inline-flex items-center text-sm font-medium text-[#1e3a8a] group-hover:text-[#15803d] transition-colors">
                  Apri <ArrowRight size={16} className="ml-1.5 transition-transform group-hover:translate-x-1" />
                </div>
              </div>

              {/* Card 2 */}
              <div className="bg-white p-8 rounded-2xl shadow-[0_1px_4px_rgba(0,0,0,0.06)] hover:shadow-[0_4px_16px_rgba(30,58,138,0.10)] transition-shadow duration-300 group cursor-pointer">
                <FileText size={28} className="text-[#1e3a8a] mb-5" />
                <h3 className="text-base font-semibold text-slate-800 mb-2">Draft Document</h3>
                <p className="text-[13px] text-slate-400 leading-relaxed mb-6 min-h-[40px]">
                  Crea bozze da template e istruzioni aziendali.
                </p>
                <div className="inline-flex items-center text-sm font-medium text-[#1e3a8a] group-hover:text-[#15803d] transition-colors">
                  Apri <ArrowRight size={16} className="ml-1.5 transition-transform group-hover:translate-x-1" />
                </div>
              </div>

              {/* Card 3 */}
              <div className="bg-white p-8 rounded-2xl shadow-[0_1px_4px_rgba(0,0,0,0.06)] hover:shadow-[0_4px_16px_rgba(30,58,138,0.10)] transition-shadow duration-300 group cursor-pointer">
                <ShieldCheck size={28} className="text-[#1e3a8a] mb-5" />
                <h3 className="text-base font-semibold text-slate-800 mb-2">Check compliance</h3>
                <p className="text-[13px] text-slate-400 leading-relaxed mb-6 min-h-[40px]">
                  Verifica conformità normativa dei documenti.
                </p>
                <div className="inline-flex items-center text-sm font-medium text-[#1e3a8a] group-hover:text-[#15803d] transition-colors">
                  Apri <ArrowRight size={16} className="ml-1.5 transition-transform group-hover:translate-x-1" />
                </div>
              </div>

              {/* Card 4 */}
              <div className="bg-white p-8 rounded-2xl shadow-[0_1px_4px_rgba(0,0,0,0.06)] hover:shadow-[0_4px_16px_rgba(30,58,138,0.10)] transition-shadow duration-300 group cursor-pointer">
                <Bot size={28} className="text-[#1e3a8a] mb-5" />
                <h3 className="text-base font-semibold text-slate-800 mb-2">Chat Assistant</h3>
                <p className="text-[13px] text-slate-400 leading-relaxed mb-6 min-h-[40px]">
                  Supporto generico, mail e brainstorming con AI.
                </p>
                <div className="inline-flex items-center text-sm font-medium text-[#1e3a8a] group-hover:text-[#15803d] transition-colors">
                  Apri <ArrowRight size={16} className="ml-1.5 transition-transform group-hover:translate-x-1" />
                </div>
              </div>

            </div>
          </div>
        </div>
      </div>

    </div>
  );
}
