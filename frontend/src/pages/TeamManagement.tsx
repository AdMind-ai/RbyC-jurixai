import React, { useState, useEffect } from 'react';
import { api } from '../api/api';
import { Search, Plus, Trash2, Shield } from 'lucide-react';
import { AppUser } from '../types/types';

// API user mapping helper
type ApiUser = {
    id: string | number;
    username: string;
    email: string;
    first_name?: string;
    last_name?: string;
    is_company_admin?: boolean;
    is_editor?: boolean;
    createdAt?: string;
    modifiedAt?: string;
};
function mapApiUser(u: ApiUser): AppUser {
    let role: 'Admin' | 'Editor' | 'Viewer' = 'Viewer';
    if (u.is_company_admin) role = 'Admin';
    else if (u.is_editor) role = 'Editor';
    const displayName = (u.first_name || u.last_name) ? `${u.first_name || ''} ${u.last_name || ''}`.trim() : u.username;
    return {
        id: u.id.toString(),
        name: displayName,
        username: u.username,
        email: u.email,
        role,
        createdDate: u.createdAt ? new Date(u.createdAt).toLocaleDateString('it-IT') : '',
        lastModified: u.modifiedAt ? new Date(u.modifiedAt).toLocaleDateString('it-IT') : '',
        avatarColor: '#' + Math.floor(Math.random() * 16777215).toString(16)
    };
}

import { AuthContext } from '../context/AuthContext';
import { useContext } from 'react';
import { toast } from 'react-toastify';

const TeamManagement: React.FC = () => {
    const [users, setUsers] = useState<AppUser[]>([]);
    const { user: currentUser } = useContext(AuthContext) || {};
    const isAdmin = currentUser && currentUser.is_admin === true;
    // Password modal state
    // const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false);
    // const [passwordUser, setPasswordUser] = useState<AppUser|null>(null);
    // const [newPassword, setNewPassword] = useState('');

    // Delete modal state
    const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
    const [deleteUser, setDeleteUser] = useState<AppUser | null>(null);
    // Password modal state
    const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false);
    const [passwordUser, setPasswordUser] = useState<AppUser | null>(null);
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');


    // Fetch users from API
    useEffect(() => {
        fetchUsers();
    }, []);

    const fetchUsers = async () => {
        try {
            const res = await api.get('/auth/users/');
            setUsers(res.data.map(mapApiUser));
        } catch {
            setUsers([]);
        }
    };
    const [searchTerm, setSearchTerm] = useState('');
    const [isModalOpen, setIsModalOpen] = useState(false);

    // New User Form State
    const [newUser, setNewUser] = useState({ username: '', first_name: '', last_name: '', email: '', password: '', role: 'Admin' });
    const [usernameError, setUsernameError] = useState<string | null>(null);
    const usernameRegex = /^[\w.@+-]+$/; // letters, numbers and @/./+/-/_

    const filteredUsers = users.filter(u =>
        u.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        u.email.toLowerCase().includes(searchTerm.toLowerCase())
    );

    // Pagination state
    const [page, setPage] = useState(0);
    const rowsPerPage = 6;

    const paginatedUsers = filteredUsers.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);

    const totalPages = Math.ceil(filteredUsers.length / rowsPerPage);

    const handleAddUser = async () => {
        if (newUser.username && newUser.email && newUser.password) {
            if (!usernameRegex.test(newUser.username)) {
                toast.error('Username non valido. Usa solo lettere, numeri e @/./+/-/_');
                return;
            }
            try {
                await api.post('/auth/users/', {
                    username: newUser.username,
                    first_name: newUser.first_name,
                    last_name: newUser.last_name,
                    email: newUser.email,
                    password: newUser.password,
                    is_company_admin: newUser.role === 'Admin',
                });
                setIsModalOpen(false);
                setNewUser({ username: '', first_name: '', last_name: '', email: '', password: '', role: 'Admin' });
                fetchUsers();
                toast.success('Utente aggiunto con successo.');
            } catch {
                toast.error('Errore durante l\'aggiunta dell\'utente.');
            }
        }
    };

    const handleDelete = async () => {
        if (!deleteUser) return;
        try {
            await api.delete(`/auth/users/${deleteUser.id}/`);
            setIsDeleteModalOpen(false);
            setDeleteUser(null);
            fetchUsers();
            toast.success('Utente eliminato con successo.');
        } catch {
            toast.error('Errore durante l\'eliminazione dell\'utente.');
        }
    };

    const handleResetPassword = async () => {
        if (!passwordUser) return;
        if (newPassword.length < 6) {
            toast.error('La password deve contenere almeno 6 caratteri.');
            return;
        }
        if (newPassword !== confirmPassword) {
            toast.error('Le password non corrispondono.');
            return;
        }
        try {
            await api.post(`/auth/users/${passwordUser.id}/set_password/`, { password: newPassword });
            setIsPasswordModalOpen(false);
            setPasswordUser(null);
            setNewPassword('');
            setConfirmPassword('');
            toast.success('Password aggiornata con successo.');
            fetchUsers();
        } catch (err) {
            console.error(err);
            toast.error('Errore durante l\'aggiornamento della password.');
        }
    };

    return (
        <div className="w-full h-full p-8 flex flex-col animate-fade-in relative max-w-6xl mx-auto">
            <div className="flex justify-between items-center mb-4">
                <h2 className="text-3xl font-bold text-slate-800">Membri e accesso</h2>
                {isAdmin ? (
                    <button
                        onClick={() => setIsModalOpen(true)}
                        className="border border-green-600 text-green-700 hover:bg-green-50 px-6 py-2.5 rounded-lg font-medium flex items-center gap-2 transition-colors bg-white shadow-sm text-sm"
                    >
                        <Plus size={20} /> Aggiungi membro
                    </button>
                ) : (
                    <div className="text-sm text-slate-500 italic">Solo amministratori possono aggiungere membri</div>
                )}
            </div>

            {/* Search Bar */}
            <div className="bg-white rounded-lg border border-slate-300 shadow-sm p-1 flex items-center mb-4">
                <div className="p-2 text-slate-400">
                    <Search size={18} />
                </div>
                <input
                    type="text"
                    placeholder="Ricerca per nome o email..."
                    className="flex-1 p-1 outline-none text-slate-700 placeholder:text-slate-400 text-sm"
                    value={searchTerm}
                    onChange={e => setSearchTerm(e.target.value)}
                />
            </div>

            {/* Table */}
            <div className="bg-white rounded-lg shadow-sm border border-slate-300 overflow-hidden flex-1">
                <table className="w-full text-left border-collapse">
                    <thead className="bg-slate-50/50 border-b border-slate-200">
                        <tr>
                            <th className="p-4 font-medium text-slate-500 text-sm">Nome</th>
                            <th className="p-4 font-medium text-slate-500 text-sm">Ruolo</th>
                            <th className="p-4 font-medium text-slate-500 text-sm">Username</th>
                            <th className="p-4 font-medium text-slate-500 text-sm">Email</th>
                            <th className="p-4 font-medium text-slate-500 text-sm">Creato il</th>
                            <th className="p-4 font-medium text-slate-500 text-sm">Ultima modifica</th>
                            <th className="p-4"></th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200">
                        {paginatedUsers.map(user => (
                            <tr key={user.id} className="hover:bg-slate-50 transition-colors group">
                                <td className="p-5 flex items-center gap-4">
                                    <div className="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-xs" style={{ backgroundColor: user.avatarColor }}>
                                        {user.name.charAt(0).toUpperCase()}
                                    </div>
                                    <span className="font-medium text-slate-800 text-sm">{user.name}</span>
                                </td>
                                <td className="p-4">
                                    <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded font-bold text-[10px] uppercase tracking-wide border border-green-200">
                                        {user.role}
                                    </span>
                                </td>
                                <td className="p-3 text-slate-600 text-sm">{user.username}</td>
                                <td className="p-3 text-slate-600 text-sm">{user.email}</td>
                                <td className="p-3 text-slate-600 tabular-nums text-xs">{user.createdDate}</td>
                                <td className="p-3 text-slate-600 tabular-nums text-xs">{user.lastModified}</td>
                                <td className="p-3 text-right flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                    {isAdmin && (
                                        <button className="text-slate-400 hover:text-blue-600 text-xs font-medium" onClick={() => { setPasswordUser(user); setIsPasswordModalOpen(true); }}>Reimposta password</button>
                                    )}
                                    {isAdmin && user.role !== 'Admin' && (
                                        <button onClick={() => { setDeleteUser(user); setIsDeleteModalOpen(true); }} className="text-slate-400 hover:text-red-500">
                                            <Trash2 size={16} />
                                        </button>
                                    )}
                                    {/* Delete Confirmation Modal */}
                                    {isDeleteModalOpen && deleteUser && (
                                        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 animate-fade-in">
                                            <div className="bg-white rounded-lg shadow-2xl p-6 w-full max-w-sm transform transition-all scale-100 border border-slate-200">
                                                <h3 className="text-xl font-bold text-center text-slate-800 mb-6 flex items-center justify-center gap-2">
                                                    <span className="text-red-500">&#9888;</span> Conferma richiesta <span className="text-red-500">&#9888;</span>
                                                </h3>
                                                <div className="text-center text-slate-700 mb-4 text-base">
                                                    Vuoi davvero eliminare l’utente <strong>{deleteUser.name}</strong>?<br />
                                                    Una volta eliminato, non sarà possibile recuperarlo.
                                                </div>
                                                <div className="flex gap-2 mt-6">
                                                    <button
                                                        onClick={handleDelete}
                                                        className="flex-1 py-2 bg-red-500 text-white font-bold rounded-md hover:bg-red-600 transition-colors text-sm"
                                                    >
                                                        Elimina utente
                                                    </button>
                                                    <button
                                                        onClick={() => { setIsDeleteModalOpen(false); setDeleteUser(null); }}
                                                        className="flex-1 py-2 text-[#1e3a8a] font-bold hover:bg-blue-50 rounded-md transition-colors text-sm"
                                                    >
                                                        Annulla
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    )}

                                    {/* Password Reset Modal */}
                                    {isPasswordModalOpen && passwordUser && (
                                        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 animate-fade-in">
                                            <div className="bg-white rounded-lg shadow-2xl p-6 w-full max-w-sm transform transition-all scale-100 border border-slate-200">
                                                <h3 className="text-xl font-bold text-center text-slate-800 mb-4">Reimposta password per <span className="text-slate-600">{passwordUser.name}</span></h3>
                                                <div className="space-y-3">
                                                    <input
                                                        type="password"
                                                        placeholder="Nuova password"
                                                        className="w-full p-2 rounded-md border border-slate-300 bg-white outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all text-sm"
                                                        value={newPassword}
                                                        onChange={e => setNewPassword(e.target.value)}
                                                    />
                                                    <input
                                                        type="password"
                                                        placeholder="Conferma password"
                                                        className="w-full p-2 rounded-md border border-slate-300 bg-white outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all text-sm"
                                                        value={confirmPassword}
                                                        onChange={e => setConfirmPassword(e.target.value)}
                                                    />
                                                </div>
                                                <div className="flex gap-2 mt-6">
                                                    <button
                                                        onClick={handleResetPassword}
                                                        className="flex-1 py-2 bg-slate-200 text-slate-700 font-bold rounded-md hover:bg-slate-300 transition-colors text-sm"
                                                    >
                                                        Aggiorna
                                                    </button>
                                                    <button
                                                        onClick={() => { setIsPasswordModalOpen(false); setPasswordUser(null); setNewPassword(''); setConfirmPassword(''); }}
                                                        className="flex-1 py-2 text-[#1e3a8a] font-bold hover:bg-blue-50 rounded-md transition-colors text-sm"
                                                    >
                                                        Annulla
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            <div className="flex justify-between items-center gap-2 mt-2 text-xs text-slate-500">
                <div className="flex items-center gap-2">
                    <span>Righe per pagina: 6</span>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        className="px-2 py-0.5 border rounded text-xs bg-white border-slate-300 disabled:opacity-50"
                        onClick={() => setPage(page - 1)}
                        disabled={page === 0}
                    >
                        &lt;
                    </button>
                    <span>{page + 1} / {totalPages || 1}</span>
                    <button
                        className="px-2 py-0.5 border rounded text-xs bg-white border-slate-300 disabled:opacity-50"
                        onClick={() => setPage(page + 1)}
                        disabled={page + 1 >= totalPages}
                    >
                        &gt;
                    </button>
                </div>
                <span>{filteredUsers.length === 0 ? "Nessun membro" : `${page * rowsPerPage + 1}–${Math.min((page + 1) * rowsPerPage, filteredUsers.length)} di ${filteredUsers.length}`}</span>
            </div>

            {/* Modal */}
            {isModalOpen && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 animate-fade-in">
                    <div className="bg-white rounded-lg shadow-2xl p-6 w-full max-w-sm transform transition-all scale-100 border border-slate-200">
                        <h3 className="text-xl font-bold text-center text-slate-800 mb-6">Aggiungi nuovo membro</h3>

                        <div className="space-y-3">
                            <input
                                type="text"
                                placeholder="Username (letters, numbers and @/./+/-/_ )"
                                className="w-full p-2 rounded-md border border-slate-300 bg-white outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all text-sm"
                                value={newUser.username}
                                onChange={e => {
                                    const v = e.target.value;
                                    setNewUser({ ...newUser, username: v });
                                    if (!usernameRegex.test(v)) setUsernameError('Username non valido');
                                    else setUsernameError(null);
                                }}
                            />
                            {usernameError && <div className="text-xs text-red-500">{usernameError}</div>}
                            <div className="grid grid-cols-2 gap-2">
                                <input
                                    type="text"
                                    placeholder="Nome (first name)"
                                    className="w-full p-2 rounded-md border border-slate-300 bg-white outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all text-sm"
                                    value={newUser.first_name}
                                    onChange={e => setNewUser({ ...newUser, first_name: e.target.value })}
                                />
                                <input
                                    type="text"
                                    placeholder="Cognome (last name)"
                                    className="w-full p-2 rounded-md border border-slate-300 bg-white outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all text-sm"
                                    value={newUser.last_name}
                                    onChange={e => setNewUser({ ...newUser, last_name: e.target.value })}
                                />
                            </div>
                            <input
                                type="email"
                                placeholder="Email"
                                className="w-full p-2 rounded-md border border-slate-300 bg-white outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all text-sm"
                                value={newUser.email}
                                onChange={e => setNewUser({ ...newUser, email: e.target.value })}
                            />
                            <input
                                type="password"
                                placeholder="Password"
                                className="w-full p-2 rounded-md border border-slate-300 bg-white outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all text-sm"
                                value={newUser.password}
                                onChange={e => setNewUser({ ...newUser, password: e.target.value })}
                            />
                            <div className="relative">
                                <select
                                    className="w-full p-2 rounded-md border border-slate-300 bg-white outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all appearance-none text-sm"
                                    value={newUser.role}
                                    onChange={e => setNewUser({ ...newUser, role: e.target.value })}
                                >
                                    {isAdmin && <option value="Admin">Admin</option>}
                                    <option value="Standard">Standard</option>
                                </select>
                                <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
                                    <Shield size={14} className="text-slate-400" />
                                </div>
                            </div>
                        </div>

                        <div className="flex gap-2 mt-6">
                            <button
                                onClick={handleAddUser}
                                className="flex-1 py-2 bg-slate-200 text-slate-700 font-bold rounded-md hover:bg-slate-300 transition-colors text-sm"
                            >
                                Aggiungi
                            </button>
                            <button
                                onClick={() => setIsModalOpen(false)}
                                className="flex-1 py-2 text-[#1e3a8a] font-bold hover:bg-blue-50 rounded-md transition-colors text-sm"
                            >
                                Annulla
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default TeamManagement;