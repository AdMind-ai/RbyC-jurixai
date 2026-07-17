import React from 'react';
import { Search, FileText, ShieldCheck, Bot, Home, ChevronDown } from 'lucide-react';

export function Polished() {
  return (
    <div className="flex h-screen w-full min-h-[800px] min-w-[1280px] max-h-[800px] max-w-[1280px] bg-[#f8fafc] font-sans overflow-hidden">
      {/* Sidebar */}
      <aside className="w-[256px] flex-shrink-0 bg-gradient-to-b from-[#1a3480] to-[#1e3a8a] text-white flex flex-col justify-between">
        <div>
          {/* Header */}
          <div className="h-16 px-6 flex items-center bg-[#172554]">
            <h1 className="text-xl font-semibold tracking-wide">Refink</h1>
            <span className="text-[10px] text-white/50 ml-2 mt-1">powered by Consilia</span>
          </div>
          
          <nav className="mt-6 px-3 flex flex-col gap-1">
            <a href="#" className="flex items-center gap-3 px-3 py-2.5 rounded-md border-l-[3px] border-[#15803d] bg-[#172554]/80 text-white">
              <Home size={18} />
              <span className="text-[13px] font-medium">Dashboard</span>
            </a>
            
            <div className="mt-6 mb-2 px-3">
              <span className="text-[10px] uppercase tracking-[0.15em] text-white/50 font-semibold">Strumenti</span>
            </div>
            
            <a href="#" className="flex items-center gap-3 px-3 py-2.5 rounded-md border-l-[3px] border-transparent text-white/80 hover:bg-white/5 hover:text-white transition-colors">
              <Search size={18} />
              <span className="text-[13px] font-medium">Ricerca documentale</span>
            </a>
            
            <a href="#" className="flex items-center gap-3 px-3 py-2.5 rounded-md border-l-[3px] border-transparent text-white/80 hover:bg-white/5 hover:text-white transition-colors">
              <FileText size={18} />
              <span className="text-[13px] font-medium">Draft Document</span>
            </a>
            
            <a href="#" className="flex items-center gap-3 px-3 py-2.5 rounded-md border-l-[3px] border-transparent text-white/80 hover:bg-white/5 hover:text-white transition-colors">
              <ShieldCheck size={18} />
              <span className="text-[13px] font-medium">Check compliance</span>
            </a>
            
            <a href="#" className="flex items-center gap-3 px-3 py-2.5 rounded-md border-l-[3px] border-transparent text-white/80 hover:bg-white/5 hover:text-white transition-colors">
              <Bot size={18} />
              <span className="text-[13px] font-medium">Chat Assistant</span>
            </a>
          </nav>
        </div>

        {/* User profile */}
        <div className="p-4 border-t border-white/10">
          <div className="flex items-center gap-3 px-2 py-2 rounded-lg hover:bg-white/5 cursor-pointer transition-colors">
            <div className="w-[36px] h-[36px] rounded-full bg-blue-500/20 flex items-center justify-center flex-shrink-0 text-sm font-semibold border border-white/10">
              MC
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-[14px] font-semibold text-white truncate">Mario Rossi</div>
              <div className="text-[11px] text-blue-300 truncate">Avvocato Senior</div>
            </div>
            <ChevronDown size={14} className="text-white/50" />
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 bg-[#f8fafc] overflow-y-auto">
        <div className="p-12 max-w-5xl mx-auto">
          <h2 className="text-[28px] font-semibold text-slate-700 mb-10 tracking-tight">
            Cosa vuoi fare oggi?
          </h2>

          <div className="grid grid-cols-2 gap-6">
            {/* Card 1 */}
            <div className="bg-white rounded-xl p-7 shadow-sm hover:shadow-md border border-slate-100 transition-all duration-200 flex flex-col group cursor-pointer">
              <div className="w-[48px] h-[48px] rounded-2xl bg-blue-50 flex items-center justify-center mb-5 group-hover:bg-blue-100 transition-colors">
                <Search size={22} className="text-[#1e3a8a]" />
              </div>
              <h3 className="text-[15px] font-semibold text-slate-800 mb-2">Ricerca documentale</h3>
              <p className="text-[13px] text-slate-500 leading-relaxed mb-6 flex-1">
                Cerca e analizza documenti nell'intero archivio dello studio.
              </p>
              <button className="bg-[#1e3a8a] hover:bg-[#172554] text-white px-4 py-2.5 rounded-lg text-sm font-medium transition-colors w-full text-center">
                Apri strumento
              </button>
            </div>

            {/* Card 2 */}
            <div className="bg-white rounded-xl p-7 shadow-sm hover:shadow-md border border-slate-100 transition-all duration-200 flex flex-col group cursor-pointer">
              <div className="w-[48px] h-[48px] rounded-2xl bg-blue-50 flex items-center justify-center mb-5 group-hover:bg-blue-100 transition-colors">
                <FileText size={22} className="text-[#1e3a8a]" />
              </div>
              <h3 className="text-[15px] font-semibold text-slate-800 mb-2">Draft Document</h3>
              <p className="text-[13px] text-slate-500 leading-relaxed mb-6 flex-1">
                Crea bozze professionali da template e istruzioni aziendali.
              </p>
              <button className="bg-[#1e3a8a] hover:bg-[#172554] text-white px-4 py-2.5 rounded-lg text-sm font-medium transition-colors w-full text-center">
                Apri strumento
              </button>
            </div>

            {/* Card 3 */}
            <div className="bg-white rounded-xl p-7 shadow-sm hover:shadow-md border border-slate-100 transition-all duration-200 flex flex-col group cursor-pointer">
              <div className="w-[48px] h-[48px] rounded-2xl bg-blue-50 flex items-center justify-center mb-5 group-hover:bg-blue-100 transition-colors">
                <ShieldCheck size={22} className="text-[#1e3a8a]" />
              </div>
              <h3 className="text-[15px] font-semibold text-slate-800 mb-2">Check compliance</h3>
              <p className="text-[13px] text-slate-500 leading-relaxed mb-6 flex-1">
                Verifica la conformità normativa dei documenti caricati.
              </p>
              <button className="bg-[#1e3a8a] hover:bg-[#172554] text-white px-4 py-2.5 rounded-lg text-sm font-medium transition-colors w-full text-center">
                Apri strumento
              </button>
            </div>

            {/* Card 4 */}
            <div className="bg-white rounded-xl p-7 shadow-sm hover:shadow-md border border-slate-100 transition-all duration-200 flex flex-col group cursor-pointer">
              <div className="w-[48px] h-[48px] rounded-2xl bg-blue-50 flex items-center justify-center mb-5 group-hover:bg-blue-100 transition-colors">
                <Bot size={22} className="text-[#1e3a8a]" />
              </div>
              <h3 className="text-[15px] font-semibold text-slate-800 mb-2">Chat Assistant</h3>
              <p className="text-[13px] text-slate-500 leading-relaxed mb-6 flex-1">
                Supporto generico, stesura mail e brainstorming con LLM.
              </p>
              <button className="bg-[#1e3a8a] hover:bg-[#172554] text-white px-4 py-2.5 rounded-lg text-sm font-medium transition-colors w-full text-center">
                Apri strumento
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default Polished;
