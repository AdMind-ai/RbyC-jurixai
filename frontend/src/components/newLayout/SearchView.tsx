import React, { useState } from 'react';
import { Search, ArrowRight, FileText } from 'lucide-react';

const SearchView: React.FC = () => {
  const [query, setQuery] = useState('');
  const [hasSearched, setHasSearched] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleSearch = () => {
    if (!query) return;
    setIsLoading(true);
    setTimeout(() => {
      setIsLoading(false);
      setHasSearched(true);
    }, 800);
  };

  const results = [
    { id: 1, title: 'Contratto Marco Fornitura Servizi 2024', snippet: '...in relazione al <strong>contratto di servizi</strong> stipulato in data odierna, le parti concordano quanto segue...', type: 'PDF', date: '12/01/2024' },
    { id: 2, title: 'Visura Camerale Ordinaria - Beta S.r.l.', snippet: '...la società denominata <strong>Beta S.r.l.</strong> risulta iscritta al registro delle imprese con numero...', type: 'PDF', date: '10/02/2024' },
    { id: 3, title: 'Verbale Assemblea Ordinaria del 05/03/2024', snippet: '...il presidente dichiara aperta la seduta e constata la regolare costituzione dell\'<strong>assemblea</strong>...', type: 'DOCX', date: '05/03/2024' },
  ];

  return (
    <div className="w-full h-full p-8 overflow-y-auto animate-fade-in max-w-7xl mx-auto">
      <div className="flex flex-col h-full">
        <h2 className="text-2xl font-bold text-slate-800 mb-6 border-b border-slate-300 pb-4 flex justify-between items-center shrink-0">
          <span>Ricerca documentale</span>
          {hasSearched && <button onClick={() => { setHasSearched(false); setQuery(''); }} className="text-sm text-[#1e3a8a] font-medium hover:underline">Nuova Ricerca</button>}
        </h2>
        {!hasSearched ? (
          <div className="flex-1 flex flex-col items-center justify-center max-w-3xl mx-auto w-full transition-all">
            <div className="w-full mb-8 text-center">
              <h3 className="text-xl font-medium text-slate-600 mb-2">Seleziona una categoria e poi effettua una ricerca tra i documenti</h3>
            </div>
            <div className="w-full bg-white p-2 rounded-xl shadow-sm border border-slate-300 flex items-center relative">
              <div className="p-4">
                <Search className="text-slate-400" size={24} />
              </div>
              <input
                type="text"
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSearch()}
                placeholder="Descrivi il documento o l'informazione che ti serve"
                className="flex-1 p-4 text-lg outline-none text-slate-700 placeholder:text-slate-300"
              />
              <button
                onClick={handleSearch}
                className="px-8 py-3 bg-slate-200 text-slate-500 font-medium rounded-lg hover:bg-slate-300 transition-colors"
              >
                {isLoading ? '...' : 'Invia'}
              </button>
            </div>
            <div className="flex gap-4 mt-4 self-end">
              <div className="flex items-center gap-2 text-slate-500 text-sm bg-white px-4 py-2 rounded-lg border border-slate-300 cursor-pointer hover:border-[#1e3a8a]">
                <span>Ricerche salvate</span>
                <ArrowRight size={14} />
              </div>
            </div>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <p className="text-slate-500">Risultati trovati per: <span className="font-bold text-slate-800">"{query}"</span></p>
              <div className="text-sm text-slate-400">3 documenti trovati</div>
            </div>
            <div className="space-y-4">
              {results.map(res => (
                <div key={res.id} className="bg-white p-6 rounded-xl shadow-sm border border-slate-300 hover:shadow-md hover:border-blue-300 transition-all cursor-pointer group">
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center text-blue-600">
                        <FileText size={20} />
                      </div>
                      <h4 className="font-bold text-lg text-blue-900 group-hover:underline">{res.title}</h4>
                    </div>
                    <span className="text-xs font-mono text-slate-400 bg-slate-50 px-2 py-1 rounded border border-slate-200">{res.type} &bull; {res.date}</span>
                  </div>
                  <p className="text-slate-600 ml-14" dangerouslySetInnerHTML={{ __html: res.snippet }}></p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default SearchView;
