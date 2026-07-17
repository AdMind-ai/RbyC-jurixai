import React from 'react';
import { Search, ShieldCheck, Bot, FileText, ArrowRight } from 'lucide-react';
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
      id: 'draft',
      title: 'Draft Document',
      desc: 'Crea bozze professionali partendo da template e istruzioni aziendali.',
      icon: FileText,
      action: '/draft-document',
    },
    {
      id: 'compliance',
      title: 'Check compliance',
      icon: ShieldCheck,
      desc: 'Verifica la conformità normativa dei documenti caricati rispetto alle policy interne.',
      action: '/compliance/chat',
    },
    {
      id: 'chat',
      title: 'Chat Assistant',
      icon: Bot,
      desc: 'Interfaccia diretta con i modelli LLM per supporto generico, stesura mail e brainstorming.',
      action: '/chat-general',
    },
  ];

  const now = new Date();
  const hour = now.getHours();
  const greeting = hour < 12 ? 'Buongiorno' : hour < 18 ? 'Buon pomeriggio' : 'Buonasera';

  return (
    <div className="w-full h-full overflow-y-auto">
      <div className="max-w-3xl mx-auto pt-14 px-10 pb-12">

        {/* Greeting */}
        <div className="mb-10">
          <p className="text-slate-400 text-sm font-medium mb-1">{greeting}</p>
          <h1 className="text-2xl font-semibold text-slate-800">Cosa vuoi fare oggi?</h1>
        </div>

        {/* Cards Grid */}
        <div className="grid grid-cols-2 gap-6">
          {cards.map((card) => {
            const Icon = card.icon;
            return (
              <div
                key={card.id}
                onClick={() => navigate(card.action)}
                className="bg-white p-8 rounded-2xl cursor-pointer group transition-shadow duration-300"
                style={{
                  boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
                }}
                onMouseEnter={e => (e.currentTarget.style.boxShadow = '0 4px 16px rgba(30,58,138,0.10)')}
                onMouseLeave={e => (e.currentTarget.style.boxShadow = '0 1px 4px rgba(0,0,0,0.06)')}
              >
                <Icon size={28} className="text-[#1e3a8a] mb-5" strokeWidth={1.5} />
                <h3 className="text-base font-semibold text-slate-800 mb-2">{card.title}</h3>
                <p className="text-[13px] text-slate-400 leading-relaxed mb-6">
                  {card.desc}
                </p>
                <div className="inline-flex items-center text-sm font-medium text-[#1e3a8a] group-hover:text-[#15803d] transition-colors duration-200">
                  Apri
                  <ArrowRight size={15} className="ml-1.5 transition-transform duration-200 group-hover:translate-x-1" />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default Home;
