import React from 'react';
import { Search, ShieldCheck, Bot, Briefcase, FileText } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const Home: React.FC = () => {
  const navigate = useNavigate();

  const cards = [
    {
      id: 'search',
      title: 'Ricerca documentale',
      icon: Search,
      desc: 'Cerca e analizza documenti nell\'intero archivio dello studio. Supporta ricerca semantica e full-text.',
      action: '/search',
    },
    {
      title: 'Draft Document',
      desc: 'Crea bozze professionali partendo da template e istruzioni aziendali.',
      icon: FileText,
      action: '/draft-document',
      disable: false,
    },
    {
      id: 'compliance',
      title: 'Check compliance',
      icon: ShieldCheck,
      desc: 'Verifica la conformità normativa dei documenti caricati rispetto alle policy interne e GDPR.',
      action: '/compliance'
    },
    {
      id: 'chat',
      title: 'Chat Assistant',
      icon: Bot,
      desc: 'Interfaccia diretta con i modelli LLM per supporto generico, stesura mail e brainstorming.',
      action: '/chat-general'
    },
    {
      id: 'segreteria',
      title: 'Segreteria Societaria',
      icon: Briefcase,
      desc: 'Gestione completa di scadenze, verbali, anagrafiche societarie e libro soci.',
      action: '/segreteria/dashboard'
    }
  ];

  return (
    <div className="w-full h-full p-8 overflow-y-auto animate-fade-in">
      <div className="flex flex-col h-full items-center justify-center">
        <h1 className="text-3xl font-bold text-slate-800 mb-12">Cosa vuoi fare oggi?</h1>

        <div className="flex flex-wrap justify-center gap-6 w-full max-w-7xl mx-auto">
          {cards.map((card) => {
            const Icon = card.icon;
            return (
              <div
                key={card.id}
                className="bg-white w-full sm:w-1/3 md:w-1/3 max-w-[330px] p-6 rounded-2xl shadow-sm border border-slate-300 hover:shadow-xl hover:border-[#1e3a8a]/20 transition-all duration-300 flex flex-col items-start group min-h-[130px]"
              >
                <div className="w-12 h-12 rounded-xl bg-blue-50 text-[#1e3a8a] flex items-center justify-center mb-4 group-hover:bg-[#1e3a8a] group-hover:text-white transition-colors shrink-0 border border-blue-100">
                  <Icon size={24} strokeWidth={1.5} />
                </div>
                <h3 className="text-lg font-bold text-slate-800 mb-3 group-hover:text-[#1e3a8a] transition-colors shrink-0">
                  {card.title}
                </h3>
                <p className="text-slate-500 text-sm leading-relaxed mb-5 flex-1">
                  {card.desc}
                </p>

                <button
                  onClick={() => navigate(card.action)}
                  className="w-full py-2 bg-[#1e3a8a] text-white rounded-lg font-semibold text-xs uppercase tracking-wide hover:bg-blue-900 transition-colors shadow-md shadow-blue-900/20 mt-auto shrink-0"
                >
                  VAI ALLA FUNZIONE
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default Home;
