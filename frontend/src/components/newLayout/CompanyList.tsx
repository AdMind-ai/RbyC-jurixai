import React, { useState, useRef } from 'react';
import { Company, Role, CompanyType, Officer, Shareholder, Deadline } from '../../types/types';
import { Search, Building, User, Calendar, ShieldCheck, Plus, X, Trash2, Upload, Edit, Clock, Building2 } from 'lucide-react';

interface CompanyListProps {
  companies: Company[];
  onAddCompany: (company: Company) => void;
  onAddDeadline: (deadline: Deadline) => void;
}

const CompanyList: React.FC<CompanyListProps> = ({ companies, onAddCompany, onAddDeadline }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null);
  
  // Modals State
  const [isCompanyModalOpen, setIsCompanyModalOpen] = useState(false);
  const [isDeadlineModalOpen, setIsDeadlineModalOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  
  // New/Edit Company Form State
  const [step, setStep] = useState<number>(1); 
  const [newCompany, setNewCompany] = useState<Partial<Company>>({
    type: CompanyType.SRL,
    status: 'Active',
    officers: [],
    shareholders: []
  });

  // Quick Deadline State
  const [quickDeadline, setQuickDeadline] = useState<Partial<Deadline>>({
    type: 'CORPORATE',
    completed: false
  });

  // Temp states for nested lists
  const [tempOfficer, setTempOfficer] = useState<Partial<Officer>>({ role: Role.AMMINISTRATORE_UNICO });
  const [tempShareholder, setTempShareholder] = useState<Partial<Shareholder>>({ quotaPercentage: 0 });

  const letterheadInputRef = useRef<HTMLInputElement>(null);

  const filteredCompanies = companies.filter(c =>
    c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    c.vatNumber.includes(searchTerm)
  );

  const openCreateModal = () => {
      setIsEditing(false);
      setNewCompany({ type: CompanyType.SRL, status: 'Active', officers: [], shareholders: [] });
      setStep(1);
      setIsCompanyModalOpen(true);
  };

  const openEditModal = () => {
      if (!selectedCompany) return;
      setIsEditing(true);
      setNewCompany(JSON.parse(JSON.stringify(selectedCompany))); // Deep copy
      setStep(1);
      setIsCompanyModalOpen(true);
  };

  const handleSaveCompany = () => {
    if (newCompany.name && newCompany.vatNumber) {
        const company: Company = {
            id: isEditing && newCompany.id ? newCompany.id : Date.now().toString(),
            name: newCompany.name,
            vatNumber: newCompany.vatNumber,
            type: newCompany.type || CompanyType.SRL,
            address: newCompany.address || '',
            capital: newCompany.capital || 0,
            status: newCompany.status || 'Active',
            officers: newCompany.officers || [],
            shareholders: newCompany.shareholders || [],
            letterheadInfo: newCompany.letterheadInfo,
            letterheadFile: newCompany.letterheadFile,
            nextMeetingDate: newCompany.nextMeetingDate
        };
        onAddCompany(company);
        setIsCompanyModalOpen(false);
        // If editing, update the selected view immediately
        if (isEditing) setSelectedCompany(company);
    }
  };

  const handleSaveDeadline = (e: React.FormEvent) => {
      e.preventDefault();
      if (selectedCompany && quickDeadline.title && quickDeadline.dueDate) {
          const deadline: Deadline = {
              id: Date.now().toString(),
              companyId: selectedCompany.id,
              title: quickDeadline.title,
              dueDate: quickDeadline.dueDate,
              type: quickDeadline.type as 'TAX' | 'CORPORATE' | 'LEGAL',
              completed: false
          };
          onAddDeadline(deadline);
          setIsDeadlineModalOpen(false);
          setQuickDeadline({ type: 'CORPORATE', completed: false });
      }
  };

  const addOfficer = () => {
      if(tempOfficer.name && tempOfficer.appointedDate) {
          const officer: Officer = {
              id: Date.now().toString(),
              name: tempOfficer.name,
              role: tempOfficer.role || Role.AMMINISTRATORE_UNICO,
              appointedDate: tempOfficer.appointedDate,
              expiryDate: tempOfficer.expiryDate || ''
          };
          setNewCompany({...newCompany, officers: [...(newCompany.officers || []), officer]});
          setTempOfficer({ role: Role.AMMINISTRATORE_UNICO, name: '', appointedDate: '', expiryDate: '' });
      }
  };

  const addShareholder = () => {
      if(tempShareholder.name) {
          const sh: Shareholder = {
              id: Date.now().toString(),
              name: tempShareholder.name,
              quotaPercentage: Number(tempShareholder.quotaPercentage)
          };
          setNewCompany({...newCompany, shareholders: [...(newCompany.shareholders || []), sh]});
          setTempShareholder({ name: '', quotaPercentage: 0 });
      }
  };

  const handleLetterheadUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files.length > 0) {
          const file = e.target.files[0];
          const reader = new FileReader();
          reader.onloadend = () => {
              setNewCompany({
                  ...newCompany,
                  letterheadFile: {
                      data: (reader.result as string).split(',')[1],
                      mimeType: file.type,
                      name: file.name
                  }
              });
          };
          reader.readAsDataURL(file);
      }
  };

  return (
    <div className="w-full h-full p-8 flex flex-col gap-6 relative animate-fade-in max-w-7xl mx-auto">
      <div className="flex justify-between items-center border-b border-slate-300 pb-4 mb-2">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
             <Building2 className="text-[#1e3a8a]" size={28} />
             Registro Società
          </h2>
          <p className="text-slate-500">Gestisci le anagrafiche clienti e le cariche sociali</p>
        </div>
        <div className="flex gap-3">
            <div className="relative hidden md:block">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={20} />
            <input
                type="text"
                placeholder="Cerca per nome o P.IVA..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 w-64"
            />
            </div>
            <button 
                onClick={openCreateModal}
                className="bg-[#1e3a8a] hover:bg-blue-900 text-white px-4 py-2 rounded-lg flex items-center gap-2 font-medium transition-colors shadow-sm"
            >
                <Plus size={20} />
                <span className="hidden md:inline">Nuova Società</span>
            </button>
        </div>
      </div>

      <div className="flex-1 flex gap-6 overflow-hidden">
        {/* List Side */}
        <div className={`bg-white rounded-xl shadow-sm border border-slate-300 flex-1 overflow-auto ${selectedCompany ? 'hidden lg:block lg:w-1/2' : 'w-full'}`}>
          <table className="w-full text-left">
            <thead className="bg-slate-50 sticky top-0 z-10 border-b border-slate-200">
              <tr>
                <th className="p-4 font-semibold text-slate-600 text-sm">Ragione Sociale</th>
                <th className="p-4 font-semibold text-slate-600 text-sm">Forma Giuridica</th>
                <th className="p-4 font-semibold text-slate-600 text-sm">P. IVA</th>
                <th className="p-4 font-semibold text-slate-600 text-sm">Stato</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {filteredCompanies.map(company => (
                <tr 
                  key={company.id} 
                  onClick={() => setSelectedCompany(company)}
                  className={`cursor-pointer transition-colors ${selectedCompany?.id === company.id ? 'bg-blue-50' : 'hover:bg-slate-50'}`}
                >
                  <td className="p-4 font-medium text-slate-800">{company.name}</td>
                  <td className="p-4 text-slate-600 text-sm">
                    <span className="px-2 py-1 bg-slate-100 border border-slate-200 rounded text-xs font-semibold">{company.type}</span>
                  </td>
                  <td className="p-4 text-slate-600 font-mono text-sm">{company.vatNumber}</td>
                  <td className="p-4">
                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border
                      ${company.status === 'Active' ? 'bg-green-100 text-green-700 border-green-200' : 'bg-amber-100 text-amber-700 border-amber-200'}`}>
                      {company.status === 'Active' ? 'Attiva' : company.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filteredCompanies.length === 0 && (
            <div className="p-12 text-center text-slate-400">
              Nessuna società trovata.
            </div>
          )}
        </div>

        {/* Detail Side */}
        {selectedCompany && (
          <div className="bg-white rounded-xl shadow-sm border border-slate-300 flex-1 overflow-auto animate-slide-in-right p-6 lg:w-1/2 h-full relative">
             
             {/* Action Buttons Top Right */}
             <div className="absolute top-4 right-4 flex gap-2">
                <button 
                    onClick={openEditModal}
                    className="p-2 text-[#1e3a8a] hover:bg-blue-50 rounded-full transition-colors border border-transparent hover:border-blue-100"
                    title="Modifica Società"
                >
                    <Edit size={18} />
                </button>
                <button 
                    onClick={() => setSelectedCompany(null)} 
                    className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-full transition-colors border border-transparent hover:border-slate-200"
                    title="Chiudi dettaglio"
                >
                    <X size={20} />
                </button>
             </div>

             <div className="flex justify-between items-start mb-6 pr-20">
                <div>
                    <h3 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
                      <Building className="text-[#1e3a8a]" />
                      {selectedCompany.name}
                    </h3>
                    <p className="text-slate-500 flex items-center gap-2 mt-1">
                       {selectedCompany.type} &bull; {selectedCompany.vatNumber}
                    </p>
                </div>
             </div>

             {/* Toolbar */}
             <div className="flex gap-2 mb-6">
                <button 
                    onClick={() => setIsDeadlineModalOpen(true)}
                    className="flex items-center gap-2 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 border border-slate-200 text-slate-700 text-sm rounded-lg font-medium transition-colors"
                >
                    <Clock size={14} />
                    Aggiungi Scadenza
                </button>
             </div>

             <div className="space-y-6">
                {/* General Info */}
                <div className="grid grid-cols-2 gap-4 p-4 bg-slate-50 rounded-lg border border-slate-200">
                    <div>
                        <p className="text-xs text-slate-400 uppercase font-semibold">Capitale Sociale</p>
                        <p className="text-lg font-medium text-slate-800">€ {selectedCompany.capital.toLocaleString('it-IT')}</p>
                    </div>
                    <div>
                        <p className="text-xs text-slate-400 uppercase font-semibold">Sede Legale</p>
                        <p className="text-sm font-medium text-slate-800">{selectedCompany.address}</p>
                    </div>
                </div>

                {/* Letterhead Info */}
                {(selectedCompany.letterheadInfo || selectedCompany.letterheadFile) && (
                     <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg">
                        <p className="text-xs text-slate-400 uppercase font-semibold mb-2">Carta Intestata Configurata</p>
                        {selectedCompany.letterheadFile && (
                            <div className="flex items-center gap-2 text-sm text-[#1e3a8a] mb-2">
                                <Upload size={14} />
                                File Caricato: {selectedCompany.letterheadFile.name}
                            </div>
                        )}
                        {selectedCompany.letterheadInfo && (
                            <p className="text-sm text-slate-600 italic line-clamp-3">{selectedCompany.letterheadInfo}</p>
                        )}
                     </div>
                )}

                {/* Officers */}
                <div>
                    <h4 className="text-sm font-bold text-slate-900 uppercase tracking-wide mb-3 flex items-center gap-2">
                        <ShieldCheck size={16} className="text-blue-500"/> Organi Sociali
                    </h4>
                    {selectedCompany.officers.length > 0 ? (
                        <div className="space-y-2">
                            {selectedCompany.officers.map(officer => (
                                <div key={officer.id} className="border border-slate-200 rounded-lg p-3 flex justify-between items-center hover:border-blue-200 transition-colors">
                                    <div>
                                        <p className="font-medium text-slate-800">{officer.name}</p>
                                        <p className="text-xs text-[#1e3a8a] font-medium">{officer.role}</p>
                                    </div>
                                    <div className="text-right">
                                        <p className="text-xs text-slate-400">Nomina: {new Date(officer.appointedDate).toLocaleDateString('it-IT')}</p>
                                        {officer.expiryDate && <p className="text-sm text-slate-600">Scad: {new Date(officer.expiryDate).toLocaleDateString('it-IT')}</p>}
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : <p className="text-sm text-slate-400 italic">Nessun organo sociale registrato.</p>}
                </div>

                {/* Shareholders */}
                <div>
                    <h4 className="text-sm font-bold text-slate-900 uppercase tracking-wide mb-3 flex items-center gap-2">
                        <User size={16} className="text-purple-500"/> Compagine Sociale
                    </h4>
                    {selectedCompany.shareholders.length > 0 ? (
                    <div className="space-y-2">
                        {selectedCompany.shareholders.map(sh => (
                            <div key={sh.id} className="flex items-center gap-3 p-2 hover:bg-slate-50 rounded border border-transparent hover:border-slate-200 border-b-slate-100 last:border-b-0">
                                <div className="w-8 h-8 rounded-full bg-purple-100 text-purple-600 border border-purple-200 flex items-center justify-center font-bold text-xs">
                                    {sh.quotaPercentage}%
                                </div>
                                <span className="text-slate-700 font-medium">{sh.name}</span>
                            </div>
                        ))}
                    </div>
                    ) : <p className="text-sm text-slate-400 italic">Nessun socio registrato.</p>}
                </div>

                 {/* Next Actions */}
                 {selectedCompany.nextMeetingDate && (
                     <div className="mt-6 p-4 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-3">
                         <Calendar className="text-amber-600 mt-1" size={20} />
                         <div>
                             <p className="font-bold text-amber-800 text-sm">Prossima Assemblea Prevista</p>
                             <p className="text-amber-700 text-sm mt-1">
                                 {new Date(selectedCompany.nextMeetingDate).toLocaleDateString('it-IT', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
                             </p>
                         </div>
                     </div>
                 )}
             </div>
          </div>
        )}
      </div>

       {/* Create/Edit Company Modal */}
       {isCompanyModalOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-3xl shadow-2xl border border-slate-200 max-h-[90vh] overflow-y-auto flex flex-col">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-xl font-bold text-slate-800">{isEditing ? 'Modifica Società' : 'Nuova Società'} - Fase {step}/4</h3>
              <button onClick={() => setIsCompanyModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X size={20} />
              </button>
            </div>
            
            {/* Progress Bar */}
            <div className="w-full bg-slate-100 h-2 rounded-full mb-6">
                <div className="bg-[#1e3a8a] h-2 rounded-full transition-all duration-300" style={{ width: `${step * 25}%` }}></div>
            </div>

            <div className="flex-1 overflow-y-auto px-1">
                {step === 1 && (
                    <div className="space-y-4">
                        <h4 className="font-medium text-slate-900 border-b border-slate-200 pb-2">Dati Generali</h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">Ragione Sociale *</label>
                                <input type="text" className="w-full p-2 border border-slate-300 rounded-lg" value={newCompany.name || ''} onChange={e => setNewCompany({...newCompany, name: e.target.value})} />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">Partita IVA *</label>
                                <input type="text" className="w-full p-2 border border-slate-300 rounded-lg" value={newCompany.vatNumber || ''} onChange={e => setNewCompany({...newCompany, vatNumber: e.target.value})} />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">Tipo</label>
                                <select className="w-full p-2 border border-slate-300 rounded-lg" value={newCompany.type} onChange={e => setNewCompany({...newCompany, type: e.target.value as CompanyType})}>
                                    {Object.values(CompanyType).map(t => <option key={t} value={t}>{t}</option>)}
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">Capitale (€)</label>
                                <input type="number" className="w-full p-2 border border-slate-300 rounded-lg" value={newCompany.capital || ''} onChange={e => setNewCompany({...newCompany, capital: Number(e.target.value)})} />
                            </div>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">Sede Legale</label>
                            <input type="text" className="w-full p-2 border border-slate-300 rounded-lg" value={newCompany.address || ''} onChange={e => setNewCompany({...newCompany, address: e.target.value})} />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">Stato</label>
                            <select className="w-full p-2 border border-slate-300 rounded-lg" value={newCompany.status} onChange={e => setNewCompany({...newCompany, status: e.target.value as 'Active' | 'Liquidation' | 'Inactive'})}>
                                <option value="Active">Attiva</option>
                                <option value="Liquidation">In Liquidazione</option>
                                <option value="Inactive">Inattiva</option>
                            </select>
                        </div>
                    </div>
                )}

                {step === 2 && (
                    <div className="space-y-4">
                        <h4 className="font-medium text-slate-900 border-b border-slate-200 pb-2">Organi Sociali</h4>
                        
                        {/* List */}
                        <div className="space-y-2 mb-4">
                            {newCompany.officers?.map((off, idx) => (
                                <div key={idx} className="flex justify-between items-center bg-slate-50 p-2 rounded border border-slate-200">
                                    <div>
                                        <span className="font-bold">{off.name}</span> <span className="text-slate-500 text-sm">({off.role})</span>
                                    </div>
                                    <button onClick={() => setNewCompany({...newCompany, officers: newCompany.officers?.filter((_, i) => i !== idx)})} className="text-red-500"><Trash2 size={16} /></button>
                                </div>
                            ))}
                        </div>

                        {/* Add Form */}
                        <div className="bg-blue-50 p-4 rounded-lg space-y-3 border border-blue-100">
                            <div className="grid grid-cols-2 gap-2">
                                <input placeholder="Nome e Cognome" className="p-2 rounded border border-slate-300 text-sm" value={tempOfficer.name || ''} onChange={e => setTempOfficer({...tempOfficer, name: e.target.value})} />
                                <select className="p-2 rounded border border-slate-300 text-sm" value={tempOfficer.role} onChange={e => setTempOfficer({...tempOfficer, role: e.target.value as Role})}>
                                    {Object.values(Role).map(r => <option key={r} value={r}>{r}</option>)}
                                </select>
                            </div>
                            <div className="grid grid-cols-2 gap-2">
                                <div>
                                    <label className="text-xs text-slate-500">Data Nomina</label>
                                    <input type="date" className="w-full p-2 rounded border border-slate-300 text-sm" value={tempOfficer.appointedDate || ''} onChange={e => setTempOfficer({...tempOfficer, appointedDate: e.target.value})} />
                                </div>
                                <div>
                                    <label className="text-xs text-slate-500">Data Scadenza</label>
                                    <input type="date" className="w-full p-2 rounded border border-slate-300 text-sm" value={tempOfficer.expiryDate || ''} onChange={e => setTempOfficer({...tempOfficer, expiryDate: e.target.value})} />
                                </div>
                            </div>
                            <button onClick={addOfficer} className="w-full bg-[#1e3a8a] text-white py-1.5 rounded text-sm font-medium">Aggiungi Carica</button>
                        </div>
                    </div>
                )}

                {step === 3 && (
                    <div className="space-y-4">
                        <h4 className="font-medium text-slate-900 border-b border-slate-200 pb-2">Compagine Sociale</h4>
                        
                        {/* List */}
                        <div className="space-y-2 mb-4">
                            {newCompany.shareholders?.map((sh, idx) => (
                                <div key={idx} className="flex justify-between items-center bg-slate-50 p-2 rounded border border-slate-200">
                                    <div>
                                        <span className="font-bold">{sh.name}</span> <span className="text-slate-500 text-sm">({sh.quotaPercentage}%)</span>
                                    </div>
                                    <button onClick={() => setNewCompany({...newCompany, shareholders: newCompany.shareholders?.filter((_, i) => i !== idx)})} className="text-red-500"><Trash2 size={16} /></button>
                                </div>
                            ))}
                        </div>

                        {/* Add Form */}
                        <div className="bg-purple-50 p-4 rounded-lg space-y-3 border border-purple-100">
                            <div className="grid grid-cols-3 gap-2">
                                <input placeholder="Nome Socio" className="col-span-2 p-2 rounded border border-slate-300 text-sm" value={tempShareholder.name || ''} onChange={e => setTempShareholder({...tempShareholder, name: e.target.value})} />
                                <input type="number" placeholder="%" className="p-2 rounded border border-slate-300 text-sm" value={tempShareholder.quotaPercentage || ''} onChange={e => setTempShareholder({...tempShareholder, quotaPercentage: Number(e.target.value)})} />
                            </div>
                            <button onClick={addShareholder} className="w-full bg-purple-600 text-white py-1.5 rounded text-sm font-medium">Aggiungi Socio</button>
                        </div>
                    </div>
                )}

                {step === 4 && (
                    <div className="space-y-4">
                        <h4 className="font-medium text-slate-900 border-b border-slate-200 pb-2">Carta Intestata & Layout</h4>
                        
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">Carica PDF/Immagine Carta Intestata</label>
                                <p className="text-xs text-slate-500 mb-2">Carica un file (PDF o Immagine) che contiene l'intestazione. L'AI lo userà per formattare i documenti.</p>
                                <input 
                                    type="file" 
                                    accept=".pdf,.jpg,.png,.jpeg"
                                    ref={letterheadInputRef}
                                    className="hidden"
                                    onChange={handleLetterheadUpload}
                                />
                                <button 
                                    onClick={() => letterheadInputRef.current?.click()}
                                    className="flex items-center gap-2 px-4 py-2 border border-slate-300 rounded-lg hover:bg-slate-50 text-slate-700 text-sm"
                                >
                                    <Upload size={16} />
                                    {newCompany.letterheadFile ? 'Sostituisci File' : 'Carica File'}
                                </button>
                                {newCompany.letterheadFile && (
                                    <div className="mt-2 text-sm text-green-600 flex items-center gap-1">
                                        <ShieldCheck size={14} /> File caricato: {newCompany.letterheadFile.name}
                                    </div>
                                )}
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">Testo Intestazione / Piè di pagina (Opzionale)</label>
                                <textarea 
                                    className="w-full p-3 border border-slate-300 rounded-lg text-sm h-24 resize-none"
                                    placeholder="Inserisci qui il testo puro se non carichi un file (es. Indirizzo, P.IVA, PEC)"
                                    value={newCompany.letterheadInfo || ''}
                                    onChange={e => setNewCompany({...newCompany, letterheadInfo: e.target.value})}
                                />
                            </div>
                        </div>
                    </div>
                )}

            </div>

            <div className="pt-6 border-t border-slate-200 flex justify-between mt-4">
                {step > 1 ? (
                     <button onClick={() => setStep(step - 1)} className="text-slate-500 px-4 py-2 hover:bg-slate-100 rounded">Indietro</button>
                ) : <div></div>}
                
                {step < 4 ? (
                    <button onClick={() => setStep(step + 1)} className="bg-[#1e3a8a] text-white px-6 py-2 rounded-lg hover:bg-blue-900">Avanti</button>
                ) : (
                    <button onClick={handleSaveCompany} className="bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700 font-bold shadow-md">
                        {isEditing ? 'Salva Modifiche' : 'Crea Società'}
                    </button>
                )}
            </div>
          </div>
        </div>
       )}

       {/* Quick Deadline Modal */}
       {isDeadlineModalOpen && selectedCompany && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
            <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-2xl border border-slate-200">
             <div className="flex justify-between items-center mb-4">
               <h3 className="text-lg font-bold text-slate-800">Aggiungi Scadenza</h3>
               <button onClick={() => setIsDeadlineModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                 <X size={20} />
               </button>
             </div>
             <form onSubmit={handleSaveDeadline} className="space-y-4">
               <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 mb-2">
                   <p className="text-xs text-slate-500">Società</p>
                   <p className="font-semibold text-slate-800">{selectedCompany.name}</p>
               </div>
               <div>
                 <label className="block text-sm font-medium text-slate-700 mb-1">Descrizione</label>
                 <input 
                   required
                   type="text" 
                   className="w-full p-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                   value={quickDeadline.title || ''}
                   onChange={e => setQuickDeadline({...quickDeadline, title: e.target.value})}
                   placeholder="Es: Rinnovo Cariche"
                 />
               </div>
               <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Data</label>
                    <input 
                      required
                      type="date" 
                      className="w-full p-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                      value={quickDeadline.dueDate || ''}
                      onChange={e => setQuickDeadline({...quickDeadline, dueDate: e.target.value})}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Tipo</label>
                    <select 
                      required
                      className="w-full p-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                      value={quickDeadline.type}
                      onChange={e => setQuickDeadline({...quickDeadline, type: e.target.value as 'TAX' | 'CORPORATE' | 'LEGAL'})}
                    >
                      <option value="CORPORATE">Societario</option>
                      <option value="TAX">Fiscale</option>
                      <option value="LEGAL">Legale</option>
                    </select>
                  </div>
               </div>
               <button type="submit" className="w-full bg-[#1e3a8a] text-white py-2 rounded-lg hover:bg-blue-900 font-medium mt-4 shadow-sm">
                 Salva Scadenza
               </button>
             </form>
           </div>
        </div>
       )}
    </div>
  );
};

export default CompanyList;
