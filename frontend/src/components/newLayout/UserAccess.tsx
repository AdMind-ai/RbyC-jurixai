
import React, { useState } from 'react';
import { Search, Plus, Trash2, X, UserPlus, Shield } from 'lucide-react';
import { AppUser } from '../../types/types';

const MOCK_USERS: AppUser[] = [
  { id: '1', name: 'Dalila', role: 'Admin', email: 'd.dimartino@rbyc.eu', createdDate: '09/09/2025', lastModified: '09/09/2025', avatarColor: '#ec4899' },
  { id: '2', name: 'Maria', role: 'Admin', email: 'm.bordoli@rbyc.eu', createdDate: '10/09/2025', lastModified: '10/09/2025', avatarColor: '#a3e635' },
  { id: '3', name: 'rbyc_admin', role: 'Admin', email: 'rbyc_admin@email.com', createdDate: '08/08/2025', lastModified: '03/09/2025', avatarColor: '#15803d' },
];

const UserAccess: React.FC = () => {
  const [users, setUsers] = useState<AppUser[]>(MOCK_USERS);
  const [searchTerm, setSearchTerm] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  
  // New User Form State
  const [newUser, setNewUser] = useState({ name: '', email: '', password: '', role: 'Admin' });

  const filteredUsers = users.filter(u => 
    u.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
    u.email.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleAddUser = () => {
      if(newUser.name && newUser.email) {
          const u: AppUser = {
              id: Date.now().toString(),
              name: newUser.name,
              email: newUser.email,
              role: newUser.role as any,
              createdDate: new Date().toLocaleDateString('it-IT'),
              lastModified: new Date().toLocaleDateString('it-IT'),
              avatarColor: '#' + Math.floor(Math.random()*16777215).toString(16)
          };
          setUsers([...users, u]);
          setIsModalOpen(false);
          setNewUser({ name: '', email: '', password: '', role: 'Admin' });
      }
  };

  const handleDelete = (id: string) => {
      setUsers(users.filter(u => u.id !== id));
  };

  return (
    <div className="w-full h-full p-8 flex flex-col animate-fade-in relative max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
         <h2 className="text-3xl font-bold text-slate-800">Membri e accesso</h2>
         <button 
            onClick={() => setIsModalOpen(true)}
            className="border border-green-600 text-green-700 hover:bg-green-50 px-6 py-2.5 rounded-lg font-medium flex items-center gap-2 transition-colors bg-white shadow-sm"
         >
             <Plus size={20} /> Aggiungi membro
         </button>
      </div>

      {/* Search Bar */}
      <div className="bg-white rounded-xl border border-slate-300 shadow-sm p-1.5 flex items-center mb-6">
          <div className="p-3 text-slate-400">
              <Search size={20} />
          </div>
          <input 
             type="text" 
             placeholder="Ricerca per nome o email..." 
             className="flex-1 p-2 outline-none text-slate-700 placeholder:text-slate-400"
             value={searchTerm}
             onChange={e => setSearchTerm(e.target.value)}
          />
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-300 overflow-hidden flex-1">
          <table className="w-full text-left border-collapse">
              <thead className="bg-slate-50/50 border-b border-slate-200">
                  <tr>
                      <th className="p-6 font-medium text-slate-500 text-sm">Nome ↑</th>
                      <th className="p-6 font-medium text-slate-500 text-sm">Ruolo</th>
                      <th className="p-6 font-medium text-slate-500 text-sm">Email</th>
                      <th className="p-6 font-medium text-slate-500 text-sm">Creato il</th>
                      <th className="p-6 font-medium text-slate-500 text-sm">Ultima modifica</th>
                      <th className="p-6"></th>
                  </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                  {filteredUsers.map(user => (
                      <tr key={user.id} className="hover:bg-slate-50 transition-colors group">
                          <td className="p-6 flex items-center gap-4">
                              <div className="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-sm" style={{ backgroundColor: user.avatarColor }}>
                                  {user.name.charAt(0).toUpperCase()}
                              </div>
                              <span className="font-medium text-slate-800">{user.name}</span>
                          </td>
                          <td className="p-6">
                              <span className="px-3 py-1 bg-green-100 text-green-700 rounded font-bold text-xs uppercase tracking-wide border border-green-200">
                                  {user.role}
                              </span>
                          </td>
                          <td className="p-6 text-slate-600">{user.email}</td>
                          <td className="p-6 text-slate-600 tabular-nums">{user.createdDate}</td>
                          <td className="p-6 text-slate-600 tabular-nums">{user.lastModified}</td>
                          <td className="p-6 text-right flex items-center justify-end gap-4 opacity-0 group-hover:opacity-100 transition-opacity">
                              <button className="text-slate-400 hover:text-blue-600 text-sm font-medium">Reimposta password</button>
                              <button onClick={() => handleDelete(user.id)} className="text-slate-400 hover:text-red-500">
                                  <Trash2 size={18} />
                              </button>
                          </td>
                      </tr>
                  ))}
              </tbody>
          </table>
      </div>
      
      <div className="flex justify-end items-center gap-4 mt-4 text-sm text-slate-500">
         <span>Righe per pagina: 5</span>
         <span>1–{filteredUsers.length} of {filteredUsers.length}</span>
      </div>

      {/* Modal */}
      {isModalOpen && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 animate-fade-in">
              <div className="bg-white rounded-xl shadow-2xl p-8 w-full max-w-md transform transition-all scale-100 border border-slate-200">
                  <h3 className="text-2xl font-bold text-center text-slate-800 mb-8">Aggiungi nuovo membro</h3>
                  
                  <div className="space-y-5">
                      <input 
                        type="text" 
                        placeholder="Nome" 
                        className="w-full p-4 rounded-lg border border-slate-300 bg-white outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all"
                        value={newUser.name}
                        onChange={e => setNewUser({...newUser, name: e.target.value})}
                      />
                      <input 
                        type="email" 
                        placeholder="Email" 
                        className="w-full p-4 rounded-lg border border-slate-300 bg-white outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all"
                        value={newUser.email}
                        onChange={e => setNewUser({...newUser, email: e.target.value})}
                      />
                      <input 
                        type="password" 
                        placeholder="Password" 
                        className="w-full p-4 rounded-lg border border-slate-300 bg-white outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all"
                        value={newUser.password}
                        onChange={e => setNewUser({...newUser, password: e.target.value})}
                      />
                      <div className="relative">
                        <select 
                           className="w-full p-4 rounded-lg border border-slate-300 bg-white outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all appearance-none"
                           value={newUser.role}
                           onChange={e => setNewUser({...newUser, role: e.target.value})}
                        >
                           <option value="Admin">Admin</option>
                           <option value="Editor">Editor</option>
                           <option value="Viewer">Viewer</option>
                        </select>
                        <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none">
                           <Shield size={16} className="text-slate-400" />
                        </div>
                      </div>
                  </div>

                  <div className="flex gap-3 mt-8">
                      <button 
                        onClick={handleAddUser}
                        className="flex-1 py-3 bg-slate-200 text-slate-700 font-bold rounded-lg hover:bg-slate-300 transition-colors"
                      >
                          Aggiungi
                      </button>
                      <button 
                        onClick={() => setIsModalOpen(false)}
                        className="flex-1 py-3 text-[#1e3a8a] font-bold hover:bg-blue-50 rounded-lg transition-colors"
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

export default UserAccess;
