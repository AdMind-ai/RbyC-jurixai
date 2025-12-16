
import React, { useState, useRef, useEffect, FormEvent } from 'react';
import { fetchWithAuth } from '../../api/fetchWithAuth';
import { Company, Role, CompanyType, Officer, Shareholder, Deadline } from '../../types/types';
import { toast } from 'react-toastify';
import { Search, Building, User, Calendar, ShieldCheck, Plus, X, Trash2, Upload, Edit, Clock, Building2 } from 'lucide-react';


const CompanyList: React.FC = () => {
    const [companies, setCompanies] = useState<Company[]>([]);
    const [deadlines, setDeadlines] = useState<Deadline[]>([]);
    const [isLoadingCompanies, setIsLoadingCompanies] = useState(false);

    const [searchTerm, setSearchTerm] = useState('');
    const [selectedCompany, setSelectedCompany] = useState<Company | null>(null);

    // Modals State
    const [isCompanyModalOpen, setIsCompanyModalOpen] = useState(false);
    const [isDeadlineModalOpen, setIsDeadlineModalOpen] = useState(false);
    const [isEditing, setIsEditing] = useState(false);
    // Delete confirmation modal state
    const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
    const [deleteTarget, setDeleteTarget] = useState<Company | null>(null);
    const [isDeleting, setIsDeleting] = useState(false);

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

    type LetterheadShape = Company['letterheadFile'] | string | { name?: string; url?: string } | null;

    const getLetterheadName = (lf: LetterheadShape) => {
        if (!lf) return null;
        if (typeof lf === 'string') return lf.split('/').pop();
        if (typeof lf === 'object' && 'name' in lf && lf.name) return lf.name;
        if (typeof lf === 'object' && 'url' in lf && lf.url) return lf.url.split('/').pop();
        return null;
    };

    // API shapes (snake_case) returned by backend
    type ApiOfficer = { id?: number | string; name: string; role: string; appointed_date?: string; appointedDate?: string; expiry_date?: string; expiryDate?: string };
    type ApiShareholder = { id?: number | string; name: string; quota_percentage?: number; quotaPercentage?: number };
    type ApiCompany = {
        id: number | string;
        name: string;
        vat_number?: string;
        company_type?: string;
        address?: string;
        capital?: number | string;
        status?: string;
        officers?: ApiOfficer[];
        shareholders?: ApiShareholder[];
        letterhead_file?: string | null;
        letterhead_filename?: string;
        letterhead_info?: string;
        next_meeting_date?: string;
    };

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

    const handleDeleteCompany = async (companyId?: string) => {
        const id = companyId ?? deleteTarget?.id;
        if (!id) return;
        setIsDeleting(true);
        try {
            const res = await fetchWithAuth(`/companies/${id}/`, { method: 'DELETE' });
            if (res && (res.status === 204 || res.ok)) {
                setCompanies(prev => prev.filter(c => c.id !== id));
                if (selectedCompany && selectedCompany.id === id) setSelectedCompany(null);
                toast.success('Società eliminata con successo');
            } else {
                const body = await res.text();
                console.error('Failed to delete company', res.status, body);
                toast.error('Impossibile eliminare la società. Verifica i permessi.');
            }
        } catch (err) {
            console.error('Error deleting company', err);
            toast.error('Errore durante l\'eliminazione della società.');
        } finally {
            setIsDeleting(false);
            setIsDeleteModalOpen(false);
            setDeleteTarget(null);
        }
    };

    const confirmDeleteCompany = (company?: Company) => {
        if (!company) return;
        setDeleteTarget(company);
        setIsDeleteModalOpen(true);
    };

    // Atualiza o status de completed da deadline
    const handleToggleDeadlineCompleted = async (deadline: Deadline) => {
        const payload = {
            completed: true
        };
        const res = await fetchWithAuth(`/deadlines/${deadline.id}/`, {
            method: 'PATCH',
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            const updated = await res.json();
            setDeadlines((prev: Deadline[]) => prev.map((d: Deadline) => d.id === deadline.id ? {
                ...d,
                completed: updated.completed
            } : d));
        }
    };

    const handleSaveCompany = async () => {
        // Only require company name (Ragione Sociale) to create a new company
        if (newCompany.name) {
            let res;
            // Prepare payload without file first (JSON)
            const payload = {
                name: newCompany.name,
                vat_number: newCompany.vatNumber,
                company_type: newCompany.type,
                address: newCompany.address,
                capital: newCompany.capital,
                status: newCompany.status,
                letterhead_info: newCompany.letterheadInfo,
                next_meeting_date: newCompany.nextMeetingDate,
                officers: newCompany.officers?.map(o => ({
                    name: o.name,
                    role: o.role,
                    appointed_date: o.appointedDate,
                    expiry_date: o.expiryDate || null
                })) || [],
                shareholders: newCompany.shareholders?.map(s => ({
                    name: s.name,
                    quota_percentage: s.quotaPercentage
                })) || [],
            };

            if (isEditing && newCompany.id) {
                // Update company without file first
                res = await fetchWithAuth(`/companies/${newCompany.id}/`, {
                    method: 'PUT',
                    body: JSON.stringify(payload)
                });
            } else {
                // Create company without file
                res = await fetchWithAuth('/companies/', {
                    method: 'POST',
                    body: JSON.stringify(payload)
                });
            }

            if (res && res.ok) {
                const c = await res.json();
                const companyId = c.id;
                // If there is a letterhead file, upload it in a separate PATCH multipart request
                // If the client-side `newCompany.letterheadFile` contains base64 data (fresh upload),
                // upload it as multipart. If it's already normalized to {name,url}, skip upload.
                if (
                    newCompany.letterheadFile &&
                    typeof newCompany.letterheadFile === 'object' &&
                    'data' in newCompany.letterheadFile &&
                    newCompany.letterheadFile.data
                ) {
                    const formData = new FormData();
                    // convert base64 -> File
                    const base64data = newCompany.letterheadFile.data as string;
                    const byteString = atob(base64data);
                    const mimeType = newCompany.letterheadFile.mimeType || 'application/octet-stream';
                    const filename = newCompany.letterheadFile.name || 'letterhead';
                    const ab = new ArrayBuffer(byteString.length);
                    const ia = new Uint8Array(ab);
                    for (let i = 0; i < byteString.length; i++) ia[i] = byteString.charCodeAt(i);
                    const file = new File([ab], filename, { type: mimeType });
                    formData.append('letterhead_file', file);

                    try {
                        const uploadRes = await fetchWithAuth(`/companies/${companyId}/`, {
                            method: 'PATCH',
                            body: formData
                        });
                        if (uploadRes && uploadRes.ok) {
                            // update company response with returned data
                            const updated = await uploadRes.json();
                            // reflect letterhead file in c
                            c.letterhead_file = updated.letterhead_file || c.letterhead_file;
                        } else {
                            console.warn('Letterhead upload failed', uploadRes);
                        }
                    } catch (err) {
                        console.error('Error uploading letterhead:', err);
                    }
                }
                // Normalize letterhead_file: API returns a URL string or null. If user uploaded
                // a file earlier in this flow, newCompany.letterheadFile may be an object with
                // `name` and `data`. We want `letterheadFile` on the client to be an object
                // { name, url } when possible so the UI can show the filename.
                type ApiLetterheadUpload = { data?: string; mimeType?: string; name?: string } | null;
                const normalizeLetterhead = (apiValue: string | null | undefined, originalUpload: ApiLetterheadUpload | undefined, apiFilename?: string) => {
                    if (!apiValue && !originalUpload && !apiFilename) return null;
                    if (apiFilename) {
                        return { name: apiFilename, url: apiValue || null };
                    }
                    if (typeof apiValue === 'string') {
                        try {
                            const url = apiValue;
                            const parts = url.split('/');
                            const filename = parts[parts.length - 1] || url;
                            return { name: decodeURIComponent(filename), url };
                        } catch (err) {
                            console.error('Error decoding letterhead filename:', err);
                            return { name: apiValue, url: apiValue };
                        }
                    }
                    if (originalUpload && originalUpload.name) {
                        return { name: originalUpload.name, url: null };
                    }
                    return null;
                };

                const company: Company = {
                    id: c.id.toString(),
                    name: c.name,
                    vatNumber: c.vat_number,
                    type: c.company_type,
                    address: c.address,
                    capital: Number(c.capital),
                    status: c.status,
                    officers: (c.officers || []).map((o: { id?: number | string; name: string; role: string; appointed_date?: string; appointedDate?: string; expiry_date?: string; expiryDate?: string }) => ({
                        id: o.id ? o.id.toString() : undefined,
                        name: o.name,
                        role: (o.role as Role) || Role.AMMINISTRATORE_UNICO,
                        appointedDate: o.appointed_date || o.appointedDate || '',
                        expiryDate: o.expiry_date || o.expiryDate || ''
                    })),
                    shareholders: (c.shareholders || []).map((s: { id?: number | string; name: string; quota_percentage?: number; quotaPercentage?: number }) => ({
                        id: s.id ? s.id.toString() : undefined,
                        name: s.name,
                        quotaPercentage: Number(s.quota_percentage ?? s.quotaPercentage ?? 0)
                    })),
                    letterheadInfo: c.letterhead_info,
                    letterheadFile: normalizeLetterhead(c.letterhead_file ?? null, newCompany.letterheadFile, c.letterhead_filename),
                    nextMeetingDate: c.next_meeting_date,
                };
                // Adiciona sócios
                if (newCompany.shareholders && newCompany.shareholders.length > 0) {
                    for (const sh of newCompany.shareholders) {
                        const shTyped = sh as Partial<Shareholder> & { quota_percentage?: number };
                        const quota = Number(shTyped.quotaPercentage ?? shTyped.quota_percentage ?? 0);
                        if (shTyped.id) {
                            await fetchWithAuth(`/shareholders/${shTyped.id}/`, {
                                method: 'PATCH',
                                body: JSON.stringify({
                                    company: companyId,
                                    name: shTyped.name,
                                    quota_percentage: quota
                                })
                            });
                        } else {
                            await fetchWithAuth('/shareholders/', {
                                method: 'POST',
                                body: JSON.stringify({
                                    company: companyId,
                                    name: shTyped.name,
                                    quota_percentage: quota
                                })
                            });
                        }
                    }
                }
                // Adiciona cariche sociali
                if (newCompany.officers && newCompany.officers.length > 0) {
                    for (const off of newCompany.officers) {
                        const offTyped = off as Partial<Officer> & { appointed_date?: string; expiry_date?: string };
                        const appointed = offTyped.appointedDate ?? offTyped.appointed_date ?? '';
                        const expiry = offTyped.expiryDate ?? offTyped.expiry_date ?? null;
                        if (offTyped.id) {
                            await fetchWithAuth(`/officers/${offTyped.id}/`, {
                                method: 'PATCH',
                                body: JSON.stringify({
                                    company: companyId,
                                    name: offTyped.name,
                                    role: offTyped.role,
                                    appointed_date: appointed,
                                    expiry_date: expiry
                                })
                            });
                        } else {
                            await fetchWithAuth('/officers/', {
                                method: 'POST',
                                body: JSON.stringify({
                                    company: companyId,
                                    name: offTyped.name,
                                    role: offTyped.role,
                                    appointed_date: appointed,
                                    expiry_date: expiry
                                })
                            });
                        }
                    }
                }
                // Adiciona scadenze
                // Remover integração de deadlines do cadastro de empresa, pois não existe no tipo Company
                if (isEditing) {
                    setCompanies(prev => prev.map(comp => comp.id === company.id ? company : comp));
                    setSelectedCompany(company);
                    toast.success('Modifiche salvate con successo');
                } else {
                    setCompanies(prev => [...prev, company]);
                    toast.success('Società creata con successo');
                }
                setIsCompanyModalOpen(false);
            }
        }
    };

    // Fetch deadlines from API
    useEffect(() => {
        const fetchDeadlines = async () => {
            try {
                const res = await fetchWithAuth('/deadlines/', { method: 'GET' });
                if (res.ok) {
                    const data = await res.json();
                    setDeadlines(data.map((d: Deadline) => ({
                        id: d.id.toString(),
                        companyId: d.company?.toString() || d.companyId,
                        title: d.title,
                        dueDate: d.due_date,
                        completed: d.completed,
                        type: d.category,
                    })));
                }
            } catch (err) {
                // Handle error if needed
                console.error('Error fetching deadlines:', err);
             }
        };
        fetchDeadlines();
    }, []);
    // Fetch companies from API
    useEffect(() => {
        const fetchCompanies = async () => {
            setIsLoadingCompanies(true);
            try {
                const res = await fetchWithAuth('/companies/', { method: 'GET' });
                if (res.ok) {
                    const data = await res.json();
                    type ApiLetterhead = string | null | { name?: string; url?: string };
                    const normalizeLetterhead = (apiValue: ApiLetterhead, apiFilename?: string) => {
                        if (!apiValue && !apiFilename) return null;
                        if (apiFilename) return { name: apiFilename, url: apiValue || null };
                        if (typeof apiValue === 'string') {
                            try {
                                const url = apiValue;
                                const parts = url.split('/');
                                const filename = parts[parts.length - 1] || url;
                                return { name: decodeURIComponent(filename), url };
                            } catch (err) {
                                console.error('Error decoding letterhead filename:', err);
                                return { name: apiValue, url: apiValue };
                            }
                        }
                        return apiValue;
                    };

                    setCompanies(data.map((c: ApiCompany) => ({
                        id: c.id.toString(),
                        name: c.name,
                        vatNumber: c.vat_number,
                        type: c.company_type,
                        address: c.address,
                        capital: Number(c.capital),
                        status: c.status,
                        officers: (c.officers || []).map((o: { id?: number | string; name: string; role: string; appointed_date?: string; appointedDate?: string; expiry_date?: string; expiryDate?: string }) => ({
                            id: o.id ? o.id.toString() : undefined,
                            name: o.name,
                            role: (o.role as Role) || Role.AMMINISTRATORE_UNICO,
                            appointedDate: o.appointed_date || o.appointedDate || '',
                            expiryDate: o.expiry_date || o.expiryDate || ''
                        })),
                        shareholders: (c.shareholders || []).map((s: { id?: number | string; name: string; quota_percentage?: number; quotaPercentage?: number }) => ({
                            id: s.id ? s.id.toString() : undefined,
                            name: s.name,
                            quotaPercentage: Number(s.quota_percentage ?? s.quotaPercentage ?? 0)
                        })),
                        letterheadInfo: c.letterhead_info,
                        letterheadFile: normalizeLetterhead(c.letterhead_file ?? null, c.letterhead_filename),
                        nextMeetingDate: c.next_meeting_date,
                    })));
                }
            } catch (err) {
                // Handle error if needed
                console.error('Error fetching companies:', err);
            } finally {
                setIsLoadingCompanies(false);
            }
        };
        fetchCompanies();
    }, []);

    const handleSaveDeadline = async (e: FormEvent) => {
        e.preventDefault();
        if (selectedCompany && quickDeadline.title && quickDeadline.dueDate) {
            try {
                const payload = {
                    company: Number(selectedCompany.id),
                    title: quickDeadline.title,
                    due_date: quickDeadline.dueDate,
                    category: quickDeadline.type,
                    completed: false
                };
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
                    setIsDeadlineModalOpen(false);
                    setQuickDeadline({ type: 'CORPORATE', completed: false });
                }
            } catch (err) {
                // Handle error if needed
                console.error('Error saving deadline:', err);
             }
        }
    };

    const addOfficer = () => {
        if (tempOfficer.name && tempOfficer.appointedDate) {
            const officer = {
                // do not set a persistent `id` for newly created items;
                // backend will return the real id after creation
                name: tempOfficer.name,
                role: tempOfficer.role || Role.AMMINISTRATORE_UNICO,
                appointedDate: tempOfficer.appointedDate,
                expiryDate: tempOfficer.expiryDate || ''
            } as Partial<Officer>;
            setNewCompany(prev => ({ ...(prev || {}), officers: [...(prev?.officers || []), officer] } as Partial<Company>));
            setTempOfficer({ role: Role.AMMINISTRATORE_UNICO, name: '', appointedDate: '', expiryDate: '' });
        }
    };

    const addShareholder = () => {
        if (tempShareholder.name) {
            const sh: Partial<Shareholder> = {
                // do not set an id here; backend will assign one
                name: tempShareholder.name,
                quotaPercentage: Number(tempShareholder.quotaPercentage)
            };
            setNewCompany(prev => ({ ...(prev || {}), shareholders: [...(prev?.shareholders || []), sh] } as Partial<Company>));
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
        <div className="w-full h-full p-8 flex flex-col gap-4 relative animate-fade-in max-w-6xl mx-auto text-sm">
            <div className="flex justify-between items-center border-b border-slate-300 pb-2 mb-2">
                <div>
                    <h2 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
                        <Building2 className="text-[#1e3a8a]" size={28} />
                        Registro Società
                    </h2>
                    <p className="text-slate-500">Gestisci le anagrafiche clienti e le cariche sociali</p>
                </div>
                <div className="flex gap-3">
                    <div className="relative hidden md:block">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
                        <input
                            type="text"
                            placeholder="Cerca per nome o P.IVA..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="pl-8 pr-2 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 w-52 text-sm"
                        />
                    </div>
                    <button
                        onClick={openCreateModal}
                        className="bg-[#1e3a8a] hover:bg-blue-900 text-white px-3 py-1.5 rounded-lg flex items-center gap-2 font-medium transition-colors shadow-sm text-sm"
                    >
                        <Plus size={16} />
                        <span className="hidden md:inline">Nuova Società</span>
                    </button>
                </div>
            </div>

            <div className="flex-1 flex gap-4 overflow-hidden">
                {/* List Side */}
                <div className={`bg-white rounded-lg shadow-sm border border-slate-300 flex-1 overflow-auto ${selectedCompany ? 'hidden lg:block lg:w-1/2' : 'w-full'}`}>
                    {isLoadingCompanies ? (
                        <div className="flex items-center justify-center p-8">
                            <div className="w-16 h-16 border-4 border-slate-200 border-t-[#1e3a8a] rounded-full animate-spin"></div>
                        </div>
                    ) : (
                        <>
                            <table className="w-full text-left">
                                <thead className="bg-slate-50 sticky top-0 z-10 border-b border-slate-200">
                                    <tr>
                                        <th className="p-2 font-semibold text-slate-600 text-xs">Ragione Sociale</th>
                                        <th className="p-2 font-semibold text-slate-600 text-xs">Forma Giuridica</th>
                                        <th className="p-2 font-semibold text-slate-600 text-xs">P. IVA</th>
                                        <th className="p-2 font-semibold text-slate-600 text-xs">Stato</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-200">
                                    {filteredCompanies.map(company => (
                                        <tr
                                            key={company.id}
                                            onClick={() => setSelectedCompany(company)}
                                            className={`cursor-pointer transition-colors ${selectedCompany?.id === company.id ? 'bg-blue-50' : 'hover:bg-slate-50'}`}
                                        >
                                            <td className="p-2 font-medium text-slate-800 text-sm">{company.name}</td>
                                            <td className="p-2 text-slate-600 text-xs">
                                                <span className="px-1.5 py-0.5 bg-slate-100 border border-slate-200 rounded text-[10px] font-semibold">{company.type}</span>
                                            </td>
                                            <td className="p-2 text-slate-600 font-mono text-xs">{company.vatNumber}</td>
                                            <td className="p-2">
                                                <div className="flex items-center justify-between">
                                                    <span className={`inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-medium border
                                                        ${company.status === 'Active' ? 'bg-green-100 text-green-700 border-green-200' : 'bg-amber-100 text-amber-700 border-amber-200'}`}>
                                                        {company.status === 'Active' ? 'Attiva' : company.status}
                                                    </span>
                                                    {!selectedCompany && (
                                                        <button
                                                            onClick={(e) => { e.stopPropagation(); confirmDeleteCompany(company); }}
                                                            className="ml-3 p-1.5 text-red-600 hover:bg-red-50 rounded-full transition-colors border border-transparent hover:border-red-100"
                                                            title="Elimina Società"
                                                        >
                                                            <Trash2 size={14} />
                                                        </button>
                                                    )}
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                            {filteredCompanies.length === 0 && (
                                <div className="p-8 text-center text-slate-400 text-sm">
                                    Nessuna società trovata.
                                </div>
                            )}
                        </>
                    )}
                </div>

                {/* Detail Side */}
                {selectedCompany && (
                    <div className="bg-white rounded-lg shadow-sm border border-slate-300 flex-1 overflow-auto animate-slide-in-right p-4 lg:w-1/2 h-full relative">

                        {/* Action Buttons Top Right */}
                        <div className="absolute top-2 right-2 flex gap-1">
                            <button
                                onClick={openEditModal}
                                className="p-1.5 text-[#1e3a8a] hover:bg-blue-50 rounded-full transition-colors border border-transparent hover:border-blue-100"
                                title="Modifica Società"
                            >
                                <Edit size={14} />
                            </button>
                            <button
                                onClick={() => confirmDeleteCompany(selectedCompany ?? undefined)}
                                className="p-1.5 text-red-600 hover:bg-red-50 rounded-full transition-colors border border-transparent hover:border-red-100"
                                title="Elimina Società"
                            >
                                <Trash2 size={14} />
                            </button>
                            <button
                                onClick={() => setSelectedCompany(null)}
                                className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-full transition-colors border border-transparent hover:border-slate-200"
                                title="Chiudi dettaglio"
                            >
                                <X size={16} />
                            </button>
                        </div>

                        <div className="flex justify-between items-start mb-4 pr-10">
                            <div>
                                <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                                    <Building className="text-[#1e3a8a]" size={16} />
                                    {selectedCompany.name}
                                </h3>
                                <p className="text-slate-500 flex items-center gap-2 mt-1 text-xs">
                                    {selectedCompany.type} &bull; {selectedCompany.vatNumber}
                                </p>
                            </div>
                        </div>

                        {/* Toolbar */}
                        <div className="flex gap-2 mb-4">
                            <button
                                onClick={() => setIsDeadlineModalOpen(true)}
                                className="flex items-center gap-2 px-2 py-1 bg-slate-100 hover:bg-slate-200 border border-slate-200 text-slate-700 text-xs rounded-lg font-medium transition-colors"
                            >
                                <Clock size={12} />
                                Aggiungi Scadenza
                            </button>
                        </div>

                        <div className="space-y-6">
                            {/* Deadlines */}
                            <div>
                                <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wide mb-2 flex items-center gap-1">
                                    <Clock size={12} className="text-amber-500" /> Scadenze
                                </h4>
                                {deadlines.filter(d => d.companyId === selectedCompany.id).length > 0 ? (
                                    <div className="space-y-2">
                                        {deadlines.filter(d => d.companyId === selectedCompany.id).map(deadline => (
                                            <div key={deadline.id} className="border border-slate-200 rounded-lg p-3 flex justify-between items-center hover:border-amber-200 transition-colors">
                                                <div>
                                                    <p className="font-medium text-slate-800 flex items-center gap-2">
                                                        <button
                                                            onClick={() => handleToggleDeadlineCompleted(deadline)}
                                                            className={`w-5 h-5 rounded-full border flex items-center justify-center mr-2 ${deadline.completed ? 'bg-green-500 border-green-600' : 'bg-white border-slate-300'}`}
                                                            title={deadline.completed ? 'Scadenza completata' : 'Marcar como completada'}
                                                        >
                                                            {deadline.completed ? <ShieldCheck size={14} className="text-white" /> : <Clock size={14} className="text-slate-400" />}
                                                        </button>
                                                        {deadline.title}
                                                    </p>
                                                    <p className="text-xs text-slate-500">{new Date(deadline.dueDate).toLocaleDateString('it-IT')}</p>
                                                </div>
                                                <div className="text-right">
                                                    <span className={`px-2 py-0.5 rounded text-xs font-semibold ${deadline.completed ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}`}>{deadline.completed ? 'Completata' : 'Pendente'}</span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                ) : <p className="text-xs text-slate-400 italic">Nessuna scadenza registrata.</p>}
                            </div>
                            {/* General Info */}
                            <div className="grid grid-cols-2 gap-3 p-3 bg-slate-50 rounded-lg border border-slate-200">
                                <div>
                                    <p className="text-[10px] text-slate-400 uppercase font-semibold">Capitale Sociale</p>
                                    <p className="text-base font-medium text-slate-800">€ {selectedCompany.capital.toLocaleString('it-IT')}</p>
                                </div>
                                <div>
                                    <p className="text-[10px] text-slate-400 uppercase font-semibold">Sede Legale</p>
                                    <p className="text-xs font-medium text-slate-800">{selectedCompany.address}</p>
                                </div>
                            </div>

                            {/* Letterhead Info */}
                            {(selectedCompany.letterheadInfo || selectedCompany.letterheadFile) && (
                                <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg">
                                    <p className="text-[10px] text-slate-400 uppercase font-semibold mb-1">Carta Intestata Configurata</p>
                                    {selectedCompany.letterheadFile && (
                                        <div className="flex items-center gap-2 text-xs text-[#1e3a8a] mb-1">
                                            <Upload size={12} />
                                            File Caricato: {getLetterheadName(selectedCompany.letterheadFile)}
                                        </div>
                                    )}
                                    
                                </div>
                            )}

                            {/* Officers */}
                            <div>
                                <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wide mb-2 flex items-center gap-1">
                                    <ShieldCheck size={12} className="text-blue-500" /> Organi Sociali
                                </h4>
                                {selectedCompany.officers.length > 0 ? (
                                    <div className="space-y-2">
                                        {selectedCompany.officers.map((officer, idx) => (
                                            <div key={officer.id ?? `off-${idx}`} className="border border-slate-200 rounded-lg p-3 flex justify-between items-center hover:border-blue-200 transition-colors">
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
                                ) : <p className="text-xs text-slate-400 italic">Nessun organo sociale registrato.</p>}
                            </div>

                            {/* Shareholders */}
                            <div>
                                <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wide mb-2 flex items-center gap-1">
                                    <User size={12} className="text-purple-500" /> Compagine Sociale
                                </h4>
                                {selectedCompany.shareholders.length > 0 ? (
                                    <div className="space-y-2">
                                        {selectedCompany.shareholders.map((sh, idx) => (
                                            <div key={sh.id ?? `sh-${idx}`} className="flex items-center gap-3 p-2 hover:bg-slate-50 rounded border border-transparent hover:border-slate-200 border-b-slate-100 last:border-b-0">
                                                <div className="w-12 h-12 rounded-full bg-purple-100 text-purple-600 border border-purple-200 flex items-center justify-center font-bold text-xs">
                                                    {sh.quotaPercentage}%
                                                </div>
                                                <span className="text-slate-700 font-medium">{sh.name}</span>
                                            </div>
                                        ))}
                                    </div>
                                ) : <p className="text-xs text-slate-400 italic">Nessun socio registrato.</p>}
                            </div>

                            {/* Next Actions */}
                            {selectedCompany.nextMeetingDate && (
                                <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-2">
                                    <Calendar className="text-amber-600 mt-0.5" size={14} />
                                    <div>
                                        <p className="font-bold text-amber-800 text-xs">Prossima Assemblea Prevista</p>
                                        <p className="text-amber-700 text-xs mt-1">
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
                    <div className="bg-white rounded-xl p-4 w-full max-w-2xl shadow-2xl border border-slate-200 max-h-[90vh] overflow-y-auto flex flex-col text-sm">
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="text-lg font-bold text-slate-800">{isEditing ? 'Modifica Società' : 'Nuova Società'} - Fase {step}/4</h3>
                            <button onClick={() => setIsCompanyModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                                <X size={16} />
                            </button>
                        </div>
                        {/* Progress Bar */}
                        <div className="w-full bg-slate-100 h-1.5 rounded-full mb-4">
                            <div className="bg-[#1e3a8a] h-1.5 rounded-full transition-all duration-300" style={{ width: `${step * 25}%` }}></div>
                        </div>

                        <div className="flex-1 overflow-y-auto px-1">
                            {step === 1 && (
                                <div className="space-y-4">
                                    <h4 className="font-medium text-slate-900 border-b border-slate-200 pb-2">Dati Generali</h4>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-sm font-medium text-slate-700 mb-1">Ragione Sociale *</label>
                                            <input type="text" className="w-full p-2 border border-slate-300 rounded-lg" value={newCompany.name || ''} onChange={e => setNewCompany({ ...newCompany, name: e.target.value })} />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-slate-700 mb-1">Partita IVA</label>
                                            <input type="text" className="w-full p-2 border border-slate-300 rounded-lg" value={newCompany.vatNumber || ''} onChange={e => setNewCompany({ ...newCompany, vatNumber: e.target.value })} />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-slate-700 mb-1">Tipo</label>
                                            <select className="w-full p-2 border border-slate-300 rounded-lg" value={newCompany.type} onChange={e => setNewCompany({ ...newCompany, type: e.target.value as CompanyType })}>
                                                {Object.values(CompanyType).map(t => <option key={t} value={t}>{t}</option>)}
                                            </select>
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-slate-700 mb-1">Capitale (€)</label>
                                            <input type="number" className="w-full p-2 border border-slate-300 rounded-lg" value={newCompany.capital || ''} onChange={e => setNewCompany({ ...newCompany, capital: Number(e.target.value) })} />
                                        </div>
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-slate-700 mb-1">Sede Legale</label>
                                        <input type="text" className="w-full p-2 border border-slate-300 rounded-lg" value={newCompany.address || ''} onChange={e => setNewCompany({ ...newCompany, address: e.target.value })} />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-slate-700 mb-1">Stato</label>
                                        <select className="w-full p-2 border border-slate-300 rounded-lg" value={newCompany.status} onChange={e => setNewCompany({ ...newCompany, status: e.target.value as 'Active' | 'Liquidation' | 'Inactive' })}>
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
                                                <button onClick={() => setNewCompany({ ...newCompany, officers: newCompany.officers?.filter((_, i) => i !== idx) })} className="text-red-500"><Trash2 size={16} /></button>
                                            </div>
                                        ))}
                                    </div>

                                    {/* Add Form */}
                                    <div className="bg-blue-50 p-4 rounded-lg space-y-3 border border-blue-100">
                                        <div className="grid grid-cols-2 gap-2">
                                            <input placeholder="Nome e Cognome" className="p-2 rounded border border-slate-300 text-sm" value={tempOfficer.name || ''} onChange={e => setTempOfficer({ ...tempOfficer, name: e.target.value })} />
                                            <select className="p-2 rounded border border-slate-300 text-sm" value={tempOfficer.role} onChange={e => setTempOfficer({ ...tempOfficer, role: e.target.value as Role })}>
                                                {Object.values(Role).map(r => <option key={r} value={r}>{r}</option>)}
                                            </select>
                                        </div>
                                        <div className="grid grid-cols-2 gap-2">
                                            <div>
                                                <label className="text-xs text-slate-500">Data Nomina</label>
                                                <input type="date" className="w-full p-2 rounded border border-slate-300 text-sm" value={tempOfficer.appointedDate || ''} onChange={e => setTempOfficer({ ...tempOfficer, appointedDate: e.target.value })} />
                                            </div>
                                            <div>
                                                <label className="text-xs text-slate-500">Data Scadenza</label>
                                                <input type="date" className="w-full p-2 rounded border border-slate-300 text-sm" value={tempOfficer.expiryDate || ''} onChange={e => setTempOfficer({ ...tempOfficer, expiryDate: e.target.value })} />
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
                                                <button onClick={() => setNewCompany({ ...newCompany, shareholders: newCompany.shareholders?.filter((_, i) => i !== idx) })} className="text-red-500"><Trash2 size={16} /></button>
                                            </div>
                                        ))}
                                    </div>

                                    {/* Add Form */}
                                    <div className="bg-purple-50 p-4 rounded-lg space-y-3 border border-purple-100">
                                        <div className="grid grid-cols-3 gap-2">
                                            <input placeholder="Nome Socio" className="col-span-2 p-2 rounded border border-slate-300 text-sm" value={tempShareholder.name || ''} onChange={e => setTempShareholder({ ...tempShareholder, name: e.target.value })} />
                                            <input type="number" placeholder="%" className="p-2 rounded border border-slate-300 text-sm" value={tempShareholder.quotaPercentage || ''} onChange={e => setTempShareholder({ ...tempShareholder, quotaPercentage: Number(e.target.value) })} />
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
                                                onChange={e => setNewCompany({ ...newCompany, letterheadInfo: e.target.value })}
                                            />
                                        </div>
                                    </div>
                                </div>
                            )}

                        </div>

                        <div className="pt-4 border-t border-slate-200 flex justify-between mt-3">
                            {step > 1 ? (
                                <button onClick={() => setStep(step - 1)} className="text-slate-500 px-3 py-1.5 hover:bg-slate-100 rounded text-xs">Indietro</button>
                            ) : <div></div>}
                            {step < 4 ? (
                                <button onClick={() => setStep(step + 1)} className="bg-[#1e3a8a] text-white px-4 py-1.5 rounded-lg hover:bg-blue-900 text-xs">Avanti</button>
                            ) : (
                                <button onClick={handleSaveCompany} className="bg-green-600 text-white px-4 py-1.5 rounded-lg hover:bg-green-700 font-bold shadow-md text-xs">
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
                    <div className="bg-white rounded-xl p-4 w-full max-w-sm shadow-2xl border border-slate-200">
                        <div className="flex justify-between items-center mb-2">
                            <h3 className="text-base font-bold text-slate-800">Aggiungi Scadenza</h3>
                            <button onClick={() => setIsDeadlineModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                                <X size={16} />
                            </button>
                        </div>
                        <form onSubmit={handleSaveDeadline} className="space-y-3">
                            <div className="p-2 bg-slate-50 rounded-lg border border-slate-200 mb-2">
                                <p className="text-xs text-slate-500">Società</p>
                                <p className="font-semibold text-slate-800">{selectedCompany.name}</p>
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-slate-700 mb-1">Descrizione</label>
                                <input
                                    required
                                    type="text"
                                    className="w-full p-1.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-sm"
                                    value={quickDeadline.title || ''}
                                    onChange={e => setQuickDeadline({ ...quickDeadline, title: e.target.value })}
                                    placeholder="Es: Rinnovo Cariche"
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-2">
                                <div>
                                    <label className="block text-xs font-medium text-slate-700 mb-1">Data</label>
                                    <input
                                        required
                                        type="date"
                                        className="w-full p-1.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-sm"
                                        value={quickDeadline.dueDate || ''}
                                        onChange={e => setQuickDeadline({ ...quickDeadline, dueDate: e.target.value })}
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-medium text-slate-700 mb-1">Tipo</label>
                                    <select
                                        required
                                        className="w-full p-1.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-sm"
                                        value={quickDeadline.type}
                                        onChange={e => setQuickDeadline({ ...quickDeadline, type: e.target.value as 'TAX' | 'CORPORATE' | 'LEGAL' })}
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

            {/* Delete Confirmation Modal */}
            {isDeleteModalOpen && deleteTarget && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
                    <div className="bg-white rounded-xl p-4 w-full max-w-md shadow-2xl border border-slate-200">
                        <div className="flex justify-between items-center mb-2">
                            <h3 className="text-base font-bold text-slate-800">Conferma eliminazione</h3>
                            <button onClick={() => { setIsDeleteModalOpen(false); setDeleteTarget(null); }} className="text-slate-400 hover:text-slate-600">
                                <X size={16} />
                            </button>
                        </div>
                        <p className="text-sm text-slate-600">Sei sicuro di voler eliminare <strong>{deleteTarget.name}</strong>? Questa operazione è irreversibile e rimuoverà tutti i dati collegati.</p>
                        <div className="mt-4 flex justify-end gap-2">
                            <button onClick={() => { setIsDeleteModalOpen(false); setDeleteTarget(null); }} className="px-3 py-1.5 bg-slate-100 rounded text-sm">Annulla</button>
                            <button onClick={() => handleDeleteCompany()} disabled={isDeleting} className="px-3 py-1.5 bg-red-600 text-white rounded text-sm font-semibold">{isDeleting ? 'Eliminando...' : 'Elimina Società'}</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default CompanyList;
