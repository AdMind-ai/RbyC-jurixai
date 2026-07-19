import React, { useState, useEffect } from 'react';
import { api } from '../api/api';
import { Search, Trash2, Shield } from 'lucide-react';
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
        <div className="page-root">
            <div className="page-header">
                <h2 className="page-title">Gestione Accessi</h2>
                {isAdmin ? (
                    <button
                        onClick={() => setIsModalOpen(true)}
                        className="btn-primary"
                    >
                        Nuovo utente
                    </button>
                ) : (
                    <div className="text-[13px] text-slate-400">Solo amministratori possono aggiungere membri</div>
                )}
            </div>
            
            <div className="page-divider" />

            <div className="page-body">
                {/* Search Bar */}
                <div className="relative max-w-sm mb-4">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
                    <input
                        type="text"
                        placeholder="Ricerca per nome o email..."
                        className="apple-input pl-9"
                        value={searchTerm}
                        onChange={e => setSearchTerm(e.target.value)}
                    />
                </div>

                {/* Table */}
                <div className="bg-white rounded-2xl overflow-hidden shadow-[var(--shadow-sm)]">
                    <table className="w-full text-left border-collapse">
                        <thead className="bg-slate-50 border-b border-slate-100">
                            <tr>
                                <th className="px-5 py-3.5 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-400">Nome</th>
                                <th className="px-5 py-3.5 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-400">Email</th>
                                <th className="px-5 py-3.5 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-400">Ruolo</th>
                                <th className="px-5 py-3.5 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-400">Creato il</th>
                                <th className="px-5 py-3.5 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-400">Ultima modifica</th>
                                <th className="px-5 py-3.5 text-right text-[11px] font-semibold uppercase tracking-wide text-slate-400">Azioni</th>
                            </tr>
                        </thead>
                        <tbody>
                            {paginatedUsers.map(user => (
                                <tr key={user.id} className="border-b border-slate-100/60 hover:bg-slate-50/50 transition-colors">
                                    <td className="px-5 py-4 flex items-center gap-3">
                                        <div className="w-[34px] h-[34px] bg-[#1e3a8a]/10 text-[#1e3a8a] font-semibold text-[13px] rounded-full flex items-center justify-center shrink-0">
                                            {user.name.charAt(0).toUpperCase()}
                                        </div>
                                        <div>
                                            <div className="font-medium text-slate-800 text-sm">{user.name}</div>
                                            <div className="text-slate-500 text-[13px]">{user.username}</div>
                                        </div>
                                    </td>
                                    <td className="px-5 py-4 text-sm text-slate-700">{user.email}</td>
                                    <td className="px-5 py-4">
                                        <span className={`badge ${user.role === 'Admin' ? 'badge-blue' : user.role === 'Editor' ? 'badge-green' : 'badge-gray'}`}>
                                            {user.role}
                                        </span>
                                    </td>
                                    <td className="px-5 py-4 text-sm text-slate-700">{user.createdDate}</td>
                                    <td className="px-5 py-4 text-sm text-slate-700">{user.lastModified}</td>
                                    <td className="px-5 py-4 text-right">
                                        <div className="flex items-center justify-end gap-2">
                                            {isAdmin && (
                                                <button className="text-slate-300 hover:text-[#1e3a8a] transition-colors p-1" onClick={() => { setPasswordUser(user); setIsPasswordModalOpen(true); }} title="Reimposta password">
                                                    <Shield size={16} />
                                                </button>
                                            )}
                                            {isAdmin && user.role !== 'Admin' && (
                                                <button className="text-slate-300 hover:text-red-400 transition-colors p-1" onClick={() => { setDeleteUser(user); setIsDeleteModalOpen(true); }} title="Elimina">
                                                    <Trash2 size={16} />
                                                </button>
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                <div className="flex justify-between items-center mt-4 text-sm text-slate-500">
                    <div>
                        {filteredUsers.length === 0 ? "Nessun membro" : `${page * rowsPerPage + 1}–${Math.min((page + 1) * rowsPerPage, filteredUsers.length)} di ${filteredUsers.length}`}
                    </div>
                    <div className="flex items-center gap-2">
                        <button
                            className="px-2 py-1 rounded hover:bg-slate-100 disabled:opacity-50 disabled:hover:bg-transparent"
                            onClick={() => setPage(page - 1)}
                            disabled={page === 0}
                        >
                            Precedente
                        </button>
                        <span>{page + 1} / {totalPages || 1}</span>
                        <button
                            className="px-2 py-1 rounded hover:bg-slate-100 disabled:opacity-50 disabled:hover:bg-transparent"
                            onClick={() => setPage(page + 1)}
                            disabled={page + 1 >= totalPages}
                        >
                            Successiva
                        </button>
                    </div>
                </div>
            </div>

            {/* Modal - Nuovo Utente */}
            {isModalOpen && (
                <div className="modal-overlay">
                    <div className="modal-box w-full max-w-md">
                        <h3 className="text-lg font-semibold text-slate-800 mb-6">Aggiungi nuovo membro</h3>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-[13px] font-medium text-slate-700 mb-1">Username</label>
                                <input
                                    type="text"
                                    className="apple-input"
                                    placeholder="Username"
                                    value={newUser.username}
                                    onChange={e => {
                                        const v = e.target.value;
                                        setNewUser({ ...newUser, username: v });
                                        if (!usernameRegex.test(v)) setUsernameError('Username non valido (solo lettere, numeri, @/./+/-/_)');
                                        else setUsernameError(null);
                                    }}
                                />
                                {usernameError && <div className="text-xs text-red-500 mt-1">{usernameError}</div>}
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-[13px] font-medium text-slate-700 mb-1">Nome</label>
                                    <input
                                        type="text"
                                        className="apple-input"
                                        placeholder="Nome"
                                        value={newUser.first_name}
                                        onChange={e => setNewUser({ ...newUser, first_name: e.target.value })}
                                    />
                                </div>
                                <div>
                                    <label className="block text-[13px] font-medium text-slate-700 mb-1">Cognome</label>
                                    <input
                                        type="text"
                                        className="apple-input"
                                        placeholder="Cognome"
                                        value={newUser.last_name}
                                        onChange={e => setNewUser({ ...newUser, last_name: e.target.value })}
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="block text-[13px] font-medium text-slate-700 mb-1">Email</label>
                                <input
                                    type="email"
                                    className="apple-input"
                                    placeholder="Email"
                                    value={newUser.email}
                                    onChange={e => setNewUser({ ...newUser, email: e.target.value })}
                                />
                            </div>
                            <div>
                                <label className="block text-[13px] font-medium text-slate-700 mb-1">Password</label>
                                <input
                                    type="password"
                                    className="apple-input"
                                    placeholder="Password"
                                    value={newUser.password}
                                    onChange={e => setNewUser({ ...newUser, password: e.target.value })}
                                />
                            </div>
                            <div>
                                <label className="block text-[13px] font-medium text-slate-700 mb-1">Ruolo</label>
                                <select
                                    className="apple-select"
                                    value={newUser.role}
                                    onChange={e => setNewUser({ ...newUser, role: e.target.value })}
                                >
                                    {isAdmin && <option value="Admin">Admin</option>}
                                    <option value="Standard">Standard</option>
                                </select>
                            </div>
                        </div>
                        <div className="flex justify-end gap-3 mt-8">
                            <button className="btn-secondary" onClick={() => setIsModalOpen(false)}>Annulla</button>
                            <button className="btn-primary" onClick={handleAddUser}>Aggiungi</button>
                        </div>
                    </div>
                </div>
            )}

            {/* Modal - Conferma Eliminazione */}
            {isDeleteModalOpen && deleteUser && (
                <div className="modal-overlay">
                    <div className="modal-box w-full max-w-sm">
                        <h3 className="text-lg font-semibold text-slate-800 mb-2">Elimina utente</h3>
                        <p className="text-sm text-slate-500 mb-6">
                            Vuoi davvero eliminare l’utente <strong className="text-slate-700">{deleteUser.name}</strong>? Questa azione non può essere annullata.
                        </p>
                        <div className="flex justify-end gap-3">
                            <button className="btn-secondary" onClick={() => { setIsDeleteModalOpen(false); setDeleteUser(null); }}>Annulla</button>
                            <button className="btn-danger" onClick={handleDelete}>Elimina</button>
                        </div>
                    </div>
                </div>
            )}

            {/* Modal - Reset Password */}
            {isPasswordModalOpen && passwordUser && (
                <div className="modal-overlay">
                    <div className="modal-box w-full max-w-sm">
                        <h3 className="text-lg font-semibold text-slate-800 mb-2">Reimposta password</h3>
                        <p className="text-sm text-slate-500 mb-6">
                            Inserisci la nuova password per <strong className="text-slate-700">{passwordUser.name}</strong>.
                        </p>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-[13px] font-medium text-slate-700 mb-1">Nuova password</label>
                                <input
                                    type="password"
                                    className="apple-input"
                                    placeholder="Nuova password"
                                    value={newPassword}
                                    onChange={e => setNewPassword(e.target.value)}
                                />
                            </div>
                            <div>
                                <label className="block text-[13px] font-medium text-slate-700 mb-1">Conferma password</label>
                                <input
                                    type="password"
                                    className="apple-input"
                                    placeholder="Conferma password"
                                    value={confirmPassword}
                                    onChange={e => setConfirmPassword(e.target.value)}
                                />
                            </div>
                        </div>
                        <div className="flex justify-end gap-3 mt-8">
                            <button className="btn-secondary" onClick={() => { setIsPasswordModalOpen(false); setPasswordUser(null); setNewPassword(''); setConfirmPassword(''); }}>Annulla</button>
                            <button className="btn-primary" onClick={handleResetPassword}>Aggiorna</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default TeamManagement;
