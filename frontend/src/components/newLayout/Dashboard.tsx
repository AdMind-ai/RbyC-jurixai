import React, { useState, useEffect } from 'react';
import { fetchWithAuth } from '../../api/fetchWithAuth';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import { Company, Deadline, CompanyType } from '../../types/types';
import { Users, Calendar, AlertTriangle, CheckCircle2, Plus, X, List, Grid, Clock, Briefcase, ChevronLeft, ChevronRight } from 'lucide-react';

const COLORS = ['#3b82f6', '#6366f1', '#8b5cf6', '#ec4899'];

const Dashboard: React.FC = () => {
    const [companies, setCompanies] = useState<Company[]>([]);
    const [deadlines, setDeadlines] = useState<Deadline[]>([]);
    // Fetch companies and deadlines from API
    useEffect(() => {
        const fetchCompanies = async () => {
            try {
                const res = await fetchWithAuth('/companies/', { method: 'GET' });
                if (res.ok) {
                    const data = await res.json();
                    setCompanies(data.map((c: any) => ({
                        id: c.id.toString(),
                        name: c.name,
                        vatNumber: c.vat_number,
                        type: c.company_type,
                        address: c.address,
                        capital: Number(c.capital),
                        status: c.status,
                        officers: c.officers || [],
                        shareholders: c.shareholders || [],
                        letterheadInfo: c.letterhead_info,
                        letterheadFile: c.letterhead_file,
                        nextMeetingDate: c.next_meeting_date,
                    })));
                }
            } catch (err) {}
        };
        const fetchDeadlines = async () => {
            try {
                const res = await fetchWithAuth('/deadlines/', { method: 'GET' });
                if (res.ok) {
                    const data = await res.json();
                    setDeadlines(data.map((d: any) => ({
                        id: d.id.toString(),
                        companyId: d.company.toString(),
                        title: d.title,
                        dueDate: d.due_date,
                        completed: d.completed,
                        type: d.category,
                    })));
                }
            } catch (err) {}
        };
        fetchCompanies();
        fetchDeadlines();
    }, []);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [viewMode, setViewMode] = useState<'list' | 'calendar'>('list');
  const [deadlineFilter, setDeadlineFilter] = useState<'upcoming' | 'urgent' | 'completed'>('urgent');
  const [hoveredDay, setHoveredDay] = useState<number | null>(null);
  
  // Calendar Navigation State
  const [currentDate, setCurrentDate] = useState(new Date());
  
  const [newDeadline, setNewDeadline] = useState<Partial<Deadline>>({
    type: 'CORPORATE',
    completed: false
  });

  const now = new Date();

  // Calc Stats (always based on total data)
  const totalCompanies = companies.length;
  const activeDeadlines = deadlines.filter(d => !d.completed).length;
  
  // Filtering Logic for List View
  const getFilteredDeadlines = () => {
      let filtered = deadlines;
      if (deadlineFilter === 'completed') {
          return filtered.filter(d => d.completed);
      }
      
      filtered = filtered.filter(d => !d.completed);
      
      if (deadlineFilter === 'urgent') {
          // Due within 7 days or overdue
          return filtered.filter(d => {
              const due = new Date(d.dueDate);
              const diffTime = due.getTime() - now.getTime();
              const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)); 
              return diffDays <= 7;
          }).sort((a, b) => new Date(a.dueDate).getTime() - new Date(b.dueDate).getTime());
      } else {
          // Upcoming (future)
          return filtered.filter(d => new Date(d.dueDate) >= now)
                 .sort((a, b) => new Date(a.dueDate).getTime() - new Date(b.dueDate).getTime());
      }
  };

  const displayedDeadlines = getFilteredDeadlines();

  // Calendar Logic
  const currentYear = currentDate.getFullYear();
  const currentMonth = currentDate.getMonth();
  
  const getDaysInMonth = (year: number, month: number) => new Date(year, month + 1, 0).getDate();
  const daysInMonth = getDaysInMonth(currentYear, currentMonth);
  const firstDayOfMonth = new Date(currentYear, currentMonth, 1).getDay(); // 0 = Sunday
  
  // Adjust for Monday start (optional, but typical in IT)
  // If 0 (Sun) -> 6. If 1 (Mon) -> 0. 
  // Let's keep standard Sunday=0 for grid simplicity or shift if needed. 
  // Standard CSS grid usually fine with Sunday first, but let's assume Mon-Sun labels.
  // Mon=0, Tue=1 ... Sun=6
  const adjustedFirstDay = firstDayOfMonth === 0 ? 6 : firstDayOfMonth - 1;

  const changeMonth = (increment: number) => {
      setCurrentDate(new Date(currentYear, currentMonth + increment, 1));
  };

  const goToToday = () => {
      setCurrentDate(new Date());
  };

  // Chart Data: Company Types
  const typeData = Object.values(CompanyType).map(type => ({
    name: type,
    value: companies.filter(c => c.type === type).length
  })).filter(d => d.value > 0);

  // Chart Data: Deadlines by Type
  const deadlineData = [
    { name: 'Fiscali', value: deadlines.filter(d => d.type === 'TAX').length },
    { name: 'Societari', value: deadlines.filter(d => d.type === 'CORPORATE').length },
    { name: 'Legali', value: deadlines.filter(d => d.type === 'LEGAL').length },
  ];

    const [errorMsg, setErrorMsg] = useState<string>('');
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setErrorMsg('');
        if (newDeadline.title && newDeadline.dueDate && newDeadline.companyId) {
            try {
                const payload = {
                    company: Number(newDeadline.companyId),
                    title: newDeadline.title,
                    due_date: newDeadline.dueDate,
                    category: newDeadline.type,
                    completed: false
                };
                console.log('Payload deadline:', payload);
                const res = await fetchWithAuth('/deadlines/', {
                    method: 'POST',
                    body: JSON.stringify(payload)
                });
                if (res.ok) {
                    const d = await res.json();
                    setDeadlines(prev => [...prev, {
                        id: d.id.toString(),
                        companyId: d.company.toString(),
                        title: d.title,
                        dueDate: d.due_date,
                        completed: d.completed,
                        type: d.category,
                    }]);
                    setIsModalOpen(false);
                    setNewDeadline({ type: 'CORPORATE', completed: false });
                } else {
                    const errData = await res.json();
                    setErrorMsg(errData?.detail || JSON.stringify(errData));
                }
            } catch (err) {
                setErrorMsg('Erro ao adicionar scadenza.');
            }
        } else {
            setErrorMsg('Preencha todos os campos obrigatórios.');
        }
    };

    const toggleComplete = async (deadline: Deadline) => {
        try {
            const res = await fetchWithAuth(`/deadlines/${deadline.id}/`, {
                method: 'PUT',
                body: JSON.stringify({
                    completed: !deadline.completed
                })
            });
            if (res.ok) {
                setDeadlines(prev => prev.map(d => d.id === deadline.id ? { ...d, completed: !d.completed } : d));
            }
        } catch (err) {
            // handle error
        }
    };

  return (
    <div className="w-full h-full p-6 overflow-y-auto animate-fade-in relative">
    <div className="max-w-6xl mx-auto space-y-4">
        <div className="flex justify-between items-center border-b border-slate-300 pb-2 mb-4">
            <div>
            <h2 className="text-1xl font-bold text-slate-800 flex items-center gap-2">
                <Briefcase className="text-[#1e3a8a]" size={22} />
                Dashboard Segreteria
            </h2>
            <p className="text-slate-500 text-sm">Panoramica attività e scadenze societarie</p>
            </div>
            <div className="flex gap-2">
                <div className="bg-white border border-slate-300 rounded-lg p-0.5 flex">
                    <button 
                        onClick={() => setViewMode('list')}
                        className={`p-1.5 rounded ${viewMode === 'list' ? 'bg-[#1e3a8a]/10 text-[#1e3a8a]' : 'text-slate-400 hover:text-slate-600'}`}
                    >
                        <List size={16} />
                    </button>
                    <button 
                        onClick={() => setViewMode('calendar')}
                        className={`p-1.5 rounded ${viewMode === 'calendar' ? 'bg-[#1e3a8a]/10 text-[#1e3a8a]' : 'text-slate-400 hover:text-slate-600'}`}
                    >
                        <Grid size={16} />
                    </button>
                </div>
                <button 
                onClick={() => setIsModalOpen(true)}
                className="bg-[#1e3a8a] hover:bg-blue-900 text-white px-3 py-1.5 rounded-lg flex items-center gap-2 font-medium transition-colors shadow-sm text-sm"
                >
                <Plus size={20} />
                Nuova Scadenza
                </button>
            </div>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            <div className="bg-white p-4 rounded-lg shadow-sm border border-slate-300 flex items-center justify-between">
            <div>
                <p className="text-xs font-medium text-slate-500">Società Gestite</p>
                <p className="text-2xl font-bold text-slate-800">{totalCompanies}</p>
            </div>
            <div className="p-2 bg-blue-50 text-[#1e3a8a] rounded-full border border-blue-100">
                <Users size={18} />
            </div>
            </div>
            <div className="bg-white p-4 rounded-lg shadow-sm border border-slate-300 flex items-center justify-between">
            <div>
                <p className="text-xs font-medium text-slate-500">Scadenze Attive</p>
                <p className="text-2xl font-bold text-slate-800">{activeDeadlines}</p>
            </div>
            <div className="p-2 bg-amber-50 text-amber-600 rounded-full border border-amber-100">
                <Calendar size={18} />
            </div>
            </div>
            <div className="bg-white p-4 rounded-lg shadow-sm border border-slate-300 flex items-center justify-between">
            <div>
                <p className="text-xs font-medium text-slate-500">Urgente (7gg)</p>
                <p className="text-2xl font-bold text-red-600">
                {deadlines.filter(d => !d.completed && (new Date(d.dueDate).getTime() - now.getTime()) < 7 * 24 * 60 * 60 * 1000).length}
                </p>
            </div>
            <div className="p-2 bg-red-50 text-red-600 rounded-full border border-red-100">
                <AlertTriangle size={18} />
            </div>
            </div>
            <div className="bg-white p-4 rounded-lg shadow-sm border border-slate-300 flex items-center justify-between">
            <div>
                <p className="text-xs font-medium text-slate-500">Completate</p>
                <p className="text-2xl font-bold text-green-600">
                {deadlines.filter(d => d.completed).length}
                </p>
            </div>
            <div className="p-2 bg-green-50 text-green-600 rounded-full border border-green-100">
                <CheckCircle2 size={18} />
            </div>
            </div>
        </div>

        {/* Main Content Area */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            {/* Deadlines Section (2/3 width) */}
            <div className="lg:col-span-2 bg-white p-4 rounded-xl shadow-sm border border-slate-300 flex flex-col h-[600px]">
            
            {viewMode === 'list' ? (
                <>
                    <div className="flex items-center gap-3 mb-4 border-b border-slate-200 pb-1 shrink-0">
                        <button 
                            onClick={() => setDeadlineFilter('urgent')}
                            className={`pb-1 text-xs font-medium transition-colors ${deadlineFilter === 'urgent' ? 'text-red-600 border-b-2 border-red-600' : 'text-slate-500 hover:text-slate-800'}`}
                        >
                            Urgenti / Scadute
                        </button>
                        <button 
                            onClick={() => setDeadlineFilter('upcoming')}
                            className={`pb-1 text-xs font-medium transition-colors ${deadlineFilter === 'upcoming' ? 'text-[#1e3a8a] border-b-2 border-[#1e3a8a]' : 'text-slate-500 hover:text-slate-800'}`}
                        >
                            Prossime
                        </button>
                        <button 
                            onClick={() => setDeadlineFilter('completed')}
                            className={`pb-1 text-xs font-medium transition-colors ${deadlineFilter === 'completed' ? 'text-green-600 border-b-2 border-green-600' : 'text-slate-500 hover:text-slate-800'}`}
                        >
                            Completate
                        </button>
                    </div>

                    <div className="space-y-2 overflow-y-auto pr-2 flex-1">
                        {displayedDeadlines.length === 0 ? (
                        <div className="text-center py-12 text-slate-400 flex flex-col items-center gap-3">
                            <CheckCircle2 size={40} className="opacity-20" />
                            <p>Nessuna scadenza in questa categoria.</p>
                        </div>
                        ) : (
                        displayedDeadlines.map(d => {
                            const companyName = companies.find(c => c.id === d.companyId)?.name || 'Unknown';
                            const isOverdue = !d.completed && new Date(d.dueDate) < now;
                            
                            return (
                            <div key={d.id} className={`flex items-center gap-3 p-2 rounded-lg border transition-all text-sm ${d.completed ? 'bg-slate-50 border-slate-200 opacity-70' : 'bg-white border-slate-200 hover:border-blue-300 hover:shadow-sm'}`}> 
                                <div 
                                    onClick={() => toggleComplete(d)}
                                    className={`cursor-pointer w-4 h-4 rounded border flex items-center justify-center ${d.completed ? 'bg-green-500 border-green-500 text-white' : 'border-slate-400 hover:border-[#1e3a8a]'}`}
                                >
                                    {d.completed && <CheckCircle2 size={12} />}
                                </div>
                                <div className="flex-1">
                                    <div className="flex items-center gap-1">
                                        <h4 className={`font-medium ${d.completed ? 'text-slate-500 line-through' : 'text-slate-800'}`}>{d.title}</h4>
                                        {isOverdue && <span className="text-[10px] bg-red-100 text-red-600 px-1.5 py-0.5 rounded font-bold uppercase">Scaduta</span>}
                                    </div>
                                    <p className="text-xs text-slate-500 flex items-center gap-1">
                                        {companyName}
                                    </p>
                                </div>
                                <div className="text-right">
                                    <div className={`text-xs font-semibold flex items-center gap-1 justify-end ${isOverdue ? 'text-red-600' : 'text-slate-700'}`}> 
                                        <Clock size={12} />
                                        {new Date(d.dueDate).toLocaleDateString('it-IT')}
                                    </div>
                                    <span className={`inline-block mt-1 text-[9px] px-1.5 py-0.5 rounded-full font-medium ${
                                        d.type === 'TAX' ? 'bg-orange-100 text-orange-700 border border-orange-200' : 
                                        d.type === 'CORPORATE' ? 'bg-blue-100 text-blue-700 border border-blue-200' : 'bg-purple-100 text-purple-700 border border-purple-200'
                                    }`}>
                                        {d.type}
                                    </span>
                                </div>
                            </div>
                            );
                        })
                        )}
                    </div>
                </>
            ) : (
                <div className="h-full flex flex-col text-sm">
                    {/* Calendar Header */}
                    <div className="flex justify-between items-center mb-4 shrink-0">
                        <div className="flex items-center gap-2">
                            <div className="flex bg-slate-100 rounded-lg p-0.5 border border-slate-200">
                                <button onClick={() => changeMonth(-1)} className="p-0.5 hover:bg-white hover:shadow-sm rounded-md text-slate-500 transition-all">
                                    <ChevronLeft size={14} />
                                </button>
                                <button onClick={() => changeMonth(1)} className="p-0.5 hover:bg-white hover:shadow-sm rounded-md text-slate-500 transition-all">
                                    <ChevronRight size={14} />
                                </button>
                            </div>
                            <h3 className="font-bold text-slate-800 capitalize text-base">
                                {currentDate.toLocaleDateString('it-IT', { month: 'long', year: 'numeric' })}
                            </h3>
                            { (currentMonth !== now.getMonth() || currentYear !== now.getFullYear()) &&
                                <button onClick={goToToday} className="text-xs font-medium text-[#1e3a8a] hover:underline">Oggi</button>
                            }
                        </div>
                        <div className="flex gap-2 text-[11px]">
                            <div className="flex items-center gap-1"><div className="w-2.5 h-2.5 rounded-full bg-blue-500 border border-blue-600"></div>Societario</div>
                            <div className="flex items-center gap-1"><div className="w-2.5 h-2.5 rounded-full bg-red-500 border border-red-600"></div>Fiscale</div>
                            <div className="flex items-center gap-1"><div className="w-2.5 h-2.5 rounded-full bg-purple-500 border border-purple-600"></div>Legale</div>
                        </div>
                    </div>
                    
                    <div className="grid grid-cols-7 gap-1 text-center text-xs font-semibold text-slate-500 mb-1 shrink-0 uppercase tracking-wide">
                        <div>Lun</div><div>Mar</div><div>Mer</div><div>Gio</div><div>Ven</div><div>Sab</div><div>Dom</div>
                    </div>
                    
                    <div className="flex-1 grid grid-cols-7 gap-1 overflow-y-auto">
                        {Array.from({ length: adjustedFirstDay }).map((_, i) => (
                            <div key={`empty-${i}`} className="bg-slate-50 rounded-lg opacity-30 border border-slate-100"></div>
                        ))}
                        {Array.from({ length: daysInMonth }).map((_, i) => {
                            const day = i + 1;
                            // Check if this specific day is Today
                            const isToday = 
                                day === now.getDate() && 
                                currentMonth === now.getMonth() && 
                                currentYear === now.getFullYear();

                            // Create date string in YYYY-MM-DD format for comparison
                            const checkDate = new Date(currentYear, currentMonth, day);
                            const yyyy = checkDate.getFullYear();
                            const mm = String(checkDate.getMonth() + 1).padStart(2, '0');
                            const dd = String(checkDate.getDate()).padStart(2, '0');
                            const dateStr = `${yyyy}-${mm}-${dd}`;

                            const dayDeadlines = deadlines.filter(d => d.dueDate === dateStr && !d.completed);
                            
                            return (
                                <div 
                                    key={day} 
                                    className={`border rounded-lg p-0.5 flex flex-col relative group min-h-[60px] transition-colors
                                        ${isToday ? 'border-blue-600 bg-blue-50/50 ring-1 ring-blue-600' : 'border-slate-200 bg-white'}
                                        ${dayDeadlines.length > 0 && !isToday ? 'border-blue-300 bg-blue-50/20 cursor-pointer hover:bg-blue-50 hover:border-blue-400' : ''}
                                    `}
                                    onMouseEnter={() => setHoveredDay(day)}
                                    onMouseLeave={() => setHoveredDay(null)}
                                >
                                    <div className="flex justify-between items-start mb-0.5">
                                        <span className={`text-xs font-medium ${isToday ? 'text-blue-700 font-bold bg-blue-200 px-1 rounded-full' : (dayDeadlines.length > 0 ? 'text-[#1e3a8a]' : 'text-slate-500')}`}> 
                                            {day}
                                        </span>
                                        {isToday && <span className="text-[8px] font-bold text-blue-600 uppercase">Oggi</span>}
                                    </div>

                                    <div className="flex-1 overflow-hidden space-y-1">
                                        {dayDeadlines.slice(0, 3).map(d => {
                                            const co = companies.find(c => c.id === d.companyId);
                                            return (
                                                <div 
                                                    key={d.id} 
                                                    className={`h-2 rounded-sm w-full cursor-help transition-transform hover:scale-y-125 ${
                                                        d.type === 'TAX' ? 'bg-red-500' : d.type === 'CORPORATE' ? 'bg-blue-500' : 'bg-purple-500'
                                                    }`} 
                                                    title={`${d.title} - ${co?.name}`}
                                                />
                                            )
                                        })}
                                        {dayDeadlines.length > 3 && <div className="text-[9px] text-slate-500 text-center font-bold">+{dayDeadlines.length - 3}</div>}
                                    </div>

                                    {/* Hover Tooltip (Day Summary) */}
                                    {dayDeadlines.length > 0 && hoveredDay === day && (
                                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-72 bg-slate-800 text-white rounded-lg p-4 shadow-2xl z-50 animate-fade-in pointer-events-none lg:pointer-events-auto border border-slate-600">
                                            <div className="text-sm font-bold border-b border-slate-600 pb-2 mb-2 flex justify-between items-center">
                                                <span>{day} {currentDate.toLocaleDateString('it-IT', { month: 'long' })}</span>
                                                <span className="text-[10px] bg-slate-700 px-2 py-0.5 rounded-full">{dayDeadlines.length} Scadenze</span>
                                            </div>
                                            <div className="space-y-3 max-h-48 overflow-y-auto custom-scrollbar-dark">
                                                {dayDeadlines.map(d => (
                                                    <div key={d.id} className="text-xs flex items-start gap-2 pb-2 border-b border-slate-700/50 last:border-0 last:pb-0">
                                                        <div className={`w-2 h-2 rounded-full mt-1 shrink-0 shadow-sm ${
                                                            d.type === 'TAX' ? 'bg-red-400' : d.type === 'CORPORATE' ? 'bg-blue-400' : 'bg-purple-400'
                                                        }`}></div>
                                                        <div className="flex-1">
                                                            <p className="font-bold text-white leading-tight mb-0.5">{d.title}</p>
                                                            <p className="text-[11px] text-slate-300 flex items-center gap-1">
                                                                <Briefcase size={10} />
                                                                {companies.find(c => c.id === d.companyId)?.name}
                                                            </p>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                            {/* Tiny triangle arrow */}
                                            <div className="absolute top-full left-1/2 -translate-x-1/2 border-8 border-transparent border-t-slate-800"></div>
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}
            </div>

            {/* Charts Column (1/3 width) */}
            <div className="grid grid-cols-1 gap-3 content-start">
            <div className="bg-white p-4 rounded-lg shadow-sm border border-slate-300 flex flex-col">
                <h3 className="text-base font-semibold text-slate-800 mb-2">Tipologia Società</h3>
                <div className="flex-1 min-h-[200px]">
                <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                    <Pie
                        data={typeData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={80}
                        paddingAngle={5}
                        dataKey="value"
                    >
                        {typeData.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} strokeWidth={0} />
                        ))}
                    </Pie>
                    <Tooltip contentStyle={{backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#fff', fontSize: '12px'}} itemStyle={{color: '#fff'}} />
                    </PieChart>
                </ResponsiveContainer>
                </div>
                <div className="flex justify-center gap-4 mt-4 flex-wrap">
                {typeData.map((entry, index) => (
                    <div key={entry.name} className="flex items-center gap-2 text-sm text-slate-600">
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[index % COLORS.length] }} />
                    {entry.name}
                    </div>
                ))}
                </div>
            </div>
            
            <div className="bg-white p-6 rounded-lg shadow-sm border border-slate-300">
                <h3 className="text-base font-semibold text-slate-800 mb-2">Statistiche Scadenze</h3>
                <div className="h-[200px]">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={deadlineData}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                        <XAxis dataKey="name" axisLine={false} tickLine={false} fontSize={12} tick={{fill: '#64748b'}} />
                        <YAxis axisLine={false} tickLine={false} fontSize={12} tick={{fill: '#64748b'}} />
                        <Tooltip cursor={{fill: '#f1f5f9'}} contentStyle={{backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#fff', fontSize: '12px'}} itemStyle={{color: '#fff'}} />
                        <Bar dataKey="value" fill="#3b82f6" radius={[4, 4, 0, 0]} barSize={40} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>
            </div>
        </div>
       </div>

       {/* Modal for New Deadline */}
             {isModalOpen && (
                 <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 animate-fade-in backdrop-blur-sm">
                     <div className="bg-white rounded-xl p-4 w-full max-w-sm shadow-2xl border border-slate-200">
                         <div className="flex justify-between items-center mb-2">
                             <h3 className="text-base font-bold text-slate-800">Aggiungi Scadenza</h3>
                             <button onClick={() => setIsModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                                 <X size={16} />
                             </button>
                         </div>
                         <form onSubmit={handleSubmit} className="space-y-3">
                             {errorMsg && (
                                 <div className="text-red-500 text-xs mb-2">{errorMsg}</div>
                             )}
                             <div>
                                 <label className="block text-xs font-medium text-slate-700 mb-1">Descrizione</label>
                                 <input 
                                     required
                                     type="text" 
                                     className="w-full p-1.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-sm"
                                     value={newDeadline.title || ''}
                                     onChange={e => setNewDeadline({...newDeadline, title: e.target.value})}
                                     placeholder="Es: Deposito Bilancio"
                                 />
                             </div>
                             <div>
                                 <label className="block text-xs font-medium text-slate-700 mb-1">Società</label>
                                 <select 
                                     required
                                     className="w-full p-1.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-sm"
                                     value={newDeadline.companyId || ''}
                                     onChange={e => setNewDeadline({...newDeadline, companyId: e.target.value})}
                                 >
                                     <option value="">Seleziona...</option>
                                     {companies.map(c => (
                                         <option key={c.id} value={c.id}>{c.name}</option>
                                     ))}
                                 </select>
                             </div>
                             <div className="grid grid-cols-2 gap-2">
                                    <div>
                                        <label className="block text-xs font-medium text-slate-700 mb-1">Data</label>
                                        <input 
                                            required
                                            type="date" 
                                            className="w-full p-1.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-sm"
                                            value={newDeadline.dueDate || ''}
                                            onChange={e => setNewDeadline({...newDeadline, dueDate: e.target.value})}
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-xs font-medium text-slate-700 mb-1">Tipo</label>
                                        <select 
                                            required
                                            className="w-full p-1.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-sm"
                                            value={newDeadline.type}
                                            onChange={e => setNewDeadline({...newDeadline, type: e.target.value as 'TAX' | 'CORPORATE' | 'LEGAL'})}
                                        >
                                            <option value="CORPORATE">Societario</option>
                                            <option value="TAX">Fiscale</option>
                                            <option value="LEGAL">Legale</option>
                                        </select>
                                    </div>
                             </div>
                             <button type="submit" className="w-full bg-[#1e3a8a] text-white py-1.5 rounded-lg hover:bg-blue-900 font-medium mt-2 shadow-sm text-sm">
                                 Salva Scadenza
                             </button>
                         </form>
                     </div>
                 </div>
             )}
    </div>
  );
};

export default Dashboard;
