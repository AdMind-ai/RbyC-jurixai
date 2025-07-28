import React, { useEffect, useState, useMemo } from "react";
import { api } from '../api/api';
import {
  Box, Typography, Avatar, Button,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper,
  Dialog, DialogTitle, DialogContent, DialogActions, DialogContentText, TextField,
  IconButton, Link, Tooltip, TableSortLabel, TableFooter, TablePagination, 
  InputAdornment
} from '@mui/material';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import CloseIcon from '@mui/icons-material/Close';
import SearchIcon from '@mui/icons-material/Search';
import Layout from '../layouts/Layout';
import { toast } from "react-toastify";

export interface Member {
  id: number;
  name: string;
  email: string;
  avatar: string;
  createdAt: string;    
  modifiedAt: string;   
  is_company_admin?: boolean; 
}

export interface MemberApi {
  id: number;
  username: string; 
  email: string;
  is_company_admin?: boolean;
  createdAt: string;    
  modifiedAt: string;   
}


function getColorFromName(name: string) {
  // Gera uma cor "aleatória" mas sempre igual para o mesmo nome
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  let color = '#';
  for (let i = 0; i < 3; i++) {
    color += ('00' + ((hash >> (i * 8)) & 0xff).toString(16)).slice(-2);
  }
  return color;
}

// Funções auxiliares
function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('it-IT');
}

// Tipos para sorting
type Order = 'asc' | 'desc';
type ColumnKey = keyof Omit<Member, "avatar" | "password">; 

// config de colunas para sort e titles
const columns: {
  key: ColumnKey;
  label: string;
  sortable?: boolean;
  render?: (member: Member) => React.ReactNode;
  align?: "left" | "right" | "center";
}[] = [
  {
    key: "name", label: "Nome e cognome", sortable: true,
    render: (m: Member) => (
      <Box sx={{display:'flex',alignItems:'center',gap:2}}>
        <Avatar
          sx={{
            bgcolor: getColorFromName(m.name),
            color: "#fff",
            width: 40,
            height: 40,
            fontWeight: 700,
            fontSize: '1.3rem'
          }}
          src={undefined} 
        >
          {m.name ? m.name[0].toUpperCase() : '?'}
        </Avatar>
        <span style={{fontSize: '16px'}}>{m.name}</span>
      </Box>
    )
  },
  {
    key: "is_company_admin", label: "Tipo", sortable: false, align: "center",
      render: (m: Member) => (
        <span style={{
            padding: '3px 8px',
            borderRadius: '12px',
            fontWeight: 'bold',
            background: m.is_company_admin ? '#EDF7ED' : '#F6F7FB',
            color: m.is_company_admin ? '#2BA52B' : '#606B75',
            fontSize: 14
          }}>
          {m.is_company_admin ? "Admin" : "Standard"}
        </span>
      )
  },
  {
    key: "email", label: "Email", sortable: true,
  },
  {
    key: "createdAt", label: "Creato il", sortable: true,
    render: m => formatDate(m.createdAt),
    align: "center",
  },
  {
    key: "modifiedAt", label: "Ultima modifica", sortable: true,
    render: m => formatDate(m.modifiedAt),
    align: "center",
  }
];


// Main component
const TeamManagement: React.FC = () => {
  // Data
  const [members, setMembers] = useState<Member[]>([]);
  const [isAdmin, setIsAdmin] = useState(false);
  // Sorting
  const [orderBy, setOrderBy] = useState<ColumnKey>("name");
  const [order, setOrder] = useState<Order>("asc");
  // Pagination
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(5);
  // Search
  const [search, setSearch] = useState("");

  // Modal states
  const [passwordModalOpen, setPasswordModalOpen] = useState(false);
  const [passwordMember, setPasswordMember] = useState<Member | null>(null);
  const [newPassword, setNewPassword] = useState('');
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deleteMemberId, setDeleteMemberId] = useState<number | null>(null);
  const [deleteMemberName, setDeleteMemberName] = useState<string | null>(null);
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [newUser, setNewUser] = useState({
    name:'', email:'', avatar:'', password:''
  });


  // Fetch members and admin status
  useEffect(() => {
    fetchMembers();

    api.get('/auth/users/me/')
      .then(res => setIsAdmin(res.data.is_company_admin === true));
  }, []);

  // Fetch members
  function fetchMembers() {
    api.get('/auth/users/')
      .then(res => {
        const mappedMembers = res.data.map((user: MemberApi) => ({
          id: user.id,
          name: user.username,
          email: user.email,
          avatar: "", 
          createdAt: user.createdAt,
          modifiedAt: user.modifiedAt,
          is_company_admin: user.is_company_admin || false,
        }));
        setMembers(mappedMembers);
      })
      .catch((err) => {
      alert(err); 
      setMembers([])
      });
  }


  // Sorting handlers
  function handleSort(column: ColumnKey) {
    if (orderBy === column) setOrder(prev=>prev==="asc"?"desc":"asc");
    else {
      setOrderBy(column);
      setOrder("asc");
    }
  }
  const sortedData = useMemo(() => {
    const arr = [...members];
    arr.sort((a, b) => {
      const valA = a[orderBy];
      const valB = b[orderBy];
      // Proteção contra undefined:
      if (valA === undefined && valB === undefined) return 0;
      if (valA === undefined) return 1;
      if (valB === undefined) return -1;

      if (orderBy === "createdAt" || orderBy === "modifiedAt") {
        return (order === "asc" ? 1 : -1) * (valA > valB ? 1 : -1);
      }
      if (typeof valA === "string" && typeof valB === "string") {
        return (order === "asc" ? 1 : -1) * valA.localeCompare(valB);
      }
      // fallback:
      if (valA === valB) return 0;
      return (order === "asc" ? 1 : -1) * (valA > valB ? 1 : -1);
    });
    return arr;
  }, [members, orderBy, order]);

  // Search filter
  const filteredData = useMemo(()=>
    sortedData.filter(m =>
      m.name.toLowerCase().includes(search.toLowerCase()) ||
      m.email.toLowerCase().includes(search.toLowerCase())
    ),
  [sortedData, search]);

  // Pagination
  const paginatedData = useMemo(()=>filteredData.slice(page*rowsPerPage, page*rowsPerPage+rowsPerPage), [filteredData, page, rowsPerPage]);

  // ------ Table Actions -----
  
  // Password reset modal handlers
  function openPasswordModal(member: Member) {
    setPasswordMember(member);
    setNewPassword('');
    setPasswordModalOpen(true);
  }
  function closePasswordModal() {
    setPasswordModalOpen(false);
    setPasswordMember(null);
  }
  function handlePasswordChange() {
    if (!passwordMember) return;
    api.post(`/auth/users/${passwordMember.id}/set_password/`, {
      password: newPassword
    })
    .then(() => {
      closePasswordModal();
      setPasswordMember(null);
      toast.success(`Password di ${passwordMember.name} aggiornata con successo!`);
      fetchMembers();
    })
    .catch((err) => {
      alert(err);
      closePasswordModal();
    });
  }

  // Delete member modal handlers
  function openDeleteModal(member: Member) {
    setDeleteMemberId(member.id);
    setDeleteMemberName(member.name);
    setDeleteModalOpen(true);
  }
  function cancelDelete() {
    setDeleteModalOpen(false);
    setDeleteMemberId(null);
    setDeleteMemberName(null);
  }
  function confirmDelete() {
    if (!deleteMemberId) return;
    api.delete(`/auth/users/${deleteMemberId}/`)
      .then(() => {
        fetchMembers();
        setDeleteModalOpen(false);
        setDeleteMemberId(null);
        setDeleteMemberName(null);
        toast.success(`Utente ${deleteMemberName} eliminato con successo!`);
      })
      .catch((err) => {
        alert(err);
      });
    
  }

  // Add user modal handlers
  function openAddModal() {
    setAddModalOpen(true);
    setNewUser({name:'', email:'', avatar:'', password:''});
  }
  function closeAddModal() { setAddModalOpen(false); }
  function handleAddUser() {
    api.post("/auth/users/", {
      username: newUser.name, 
      email: newUser.email,
      password: newUser.password
    })
      .then(() => {
        toast.success(`Utente ${newUser.name} aggiunto con successo!`);
        fetchMembers();
        setAddModalOpen(false);
      })
      .catch(err => {
        // Isso mostra a mensagem do backend DRF
        alert(JSON.stringify(err.response.data))
        // ou console.log(err.response?.data)
      })

    
  }
  

  // Pagination handlers
  function handleChangePage(
    _e: React.MouseEvent<HTMLButtonElement> | null,
    newPage: number
  ) {
    setPage(newPage);
  }
  function handleChangeRowsPerPage(event: React.ChangeEvent<HTMLInputElement>) {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  }

  return (
    <Layout>
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          overflow: 'auto',
          height: '100%',
          width: '100%',
        }}
      >
        {/* Title and Add Member */}
        <Box sx={{
          display: 'flex',
          justifyContent: 'space-between',
          marginBottom: 2,
          alignItems:'center',
          padding: 'calc(3vh) calc(3vh) 0 calc(3vh)',
          mx: '1vw',
        }}>
          <Typography variant="h2">
            Membri e accesso
          </Typography>
          {isAdmin && (
            <Button
              variant="outlined"
              color="secondary"
              sx={{ width: '190px' }}
              onClick={openAddModal}
            >
              + Aggiungi membro
            </Button>
          )}
        </Box>
        {/* Searcher */}
        <Box sx={{ width: '95%', mx:"auto", mb:2.5 }}>
          <TextField
            variant="outlined"
            placeholder="Ricerca per nome o email..."
            value={search}
            onChange={e=>{ setSearch(e.target.value); setPage(0);}}
            fullWidth
            size="small"
            sx={{
              '& .MuiInputBase-input': {
                fontSize: 16,       
                py: 1,             
              }
            }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start"><SearchIcon /></InputAdornment>
              ),
            }}
          />
        </Box>

        {/* MAIN CONTENT - Members Table */}
        <Box sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'flex-start',
          width: '100%',
        }}>
          <TableContainer component={Paper} sx={{ width: '95%', borderRadius: 3, boxShadow: 3, bgcolor: '#fff' }}>
            <Table>
              <TableHead>
                <TableRow>
                  {columns.map(col => (
                    <TableCell
                      key={col.key}
                      align={col.align || "left"}
                      sortDirection={orderBy === col.key ? order : false}
                      sx={{ color: 'grey', fontSize: '16px' }}
                    >
                      {col.sortable ? (
                        <TableSortLabel
                          active={orderBy===col.key}
                          direction={orderBy===col.key ? order : "asc"}
                          onClick={()=>handleSort(col.key)}
                        >
                          {col.label}
                        </TableSortLabel>
                      ) : col.label}
                    </TableCell>
                  ))}
                  <TableCell align="right"></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {paginatedData.map((member) => (
                  <TableRow key={member.id}>
                    {columns.map(col => (
                      <TableCell
                        key={col.key}
                        align={col.align || "left"}
                        sx={{ fontSize:"16px" }}
                      >
                        {col.render ? col.render(member) : member[col.key as keyof Member]}
                      </TableCell>
                    ))}
                    <TableCell align="right">
                      {isAdmin && (
                        <Link 
                          sx={{ cursor: 'pointer', fontSize: '16px', color:'grey', marginRight:2 }}
                          component="button"
                          onClick={()=>openPasswordModal(member)}
                          underline="hover"
                        >
                          Reimposta password
                        </Link>
                      )}
                      {isAdmin && (
                        <Tooltip title={member.is_company_admin ? "Impossibile eliminare admin" : "Elimina membro"}>
                          <span>
                            <IconButton
                              color="error"
                              onClick={member.is_company_admin
                                ? undefined
                                : () => openDeleteModal(member)}
                              disabled={member.is_company_admin}
                              sx={{
                                color: member.is_company_admin ? '#aaa' : '#d32f2f',
                                cursor: member.is_company_admin ? 'not-allowed' : 'pointer'
                              }}
                            >
                              <DeleteOutlineIcon sx={{
                                fontSize: 25,
                                color: member.is_company_admin ? '#aaa' : undefined
                              }}/>
                            </IconButton>
                          </span>
                        </Tooltip>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
                {filteredData.length===0 && (
                  <TableRow>
                    <TableCell colSpan={columns.length+1} align="center" sx={{fontStyle:'italic', fontSize:'16px' }}>Nessun utente</TableCell>
                  </TableRow>
                )}
              </TableBody>
              <TableFooter>
                <TableRow>
                  <TablePagination
                    count={filteredData.length}
                    page={page}
                    onPageChange={handleChangePage}
                    rowsPerPage={rowsPerPage}
                    onRowsPerPageChange={handleChangeRowsPerPage}
                    labelRowsPerPage="Righe per pagina:"
                    rowsPerPageOptions={[5,10,25]}
                    sx={{
                      '& .MuiTablePagination-selectLabel': { fontSize: 14 },
                      '& .MuiTablePagination-displayedRows': { fontSize: 16 },
                      '& .MuiSelect-select': { fontSize: 14, paddingY: 0.5 },
                      '& .MuiIconButton-root': { fontSize: 14 }
                    }}
                    slotProps={{
                      select: {
                        MenuProps: {
                          PaperProps: {
                            sx: {
                              fontSize: 14, 
                              '& .MuiMenuItem-root': {
                                fontSize: 14
                              }
                            }
                          }
                        }
                      }
                    }}
                  />
                </TableRow>
              </TableFooter>
            </Table>
          </TableContainer>
        </Box>

        {/* DIALOG CHANGE PASSWORD */}
        <Dialog open={passwordModalOpen} onClose={closePasswordModal}>
          <DialogTitle sx={{display: 'flex', alignItems:'center', fontWeight:'bold', justifyContent:'center', mt:2, fontSize:'24px'}}>
            Reimposta password
          </DialogTitle>
          <DialogContent>
            <DialogContentText sx={{ mb:2, mx:2 }}>
              Inserisci la nuova password per <strong>{passwordMember?.name}</strong>
            </DialogContentText>
            <TextField
              autoFocus
              label="Nuova password"
              type="password"
              fullWidth
              value={newPassword}
              size="small"
              onChange={e=>setNewPassword(e.target.value)}
              sx={{
                mb: 1,
                '& .MuiInputBase-input': {
                  fontSize: 14,           
                },
                '& .MuiInputLabel-root': {
                  fontSize: 16      
                },
              }}
            />
          </DialogContent>
          <DialogActions sx={{ justifyContent:'center', pb:2 }}>
            <Button variant="contained" color="primary" 
              onClick={handlePasswordChange}
              disabled={!newPassword}>
              Conferma
            </Button>
            <Button onClick={closePasswordModal}>Annulla</Button>
          </DialogActions>
        </Dialog>

        {/* DIALOG CONFIRM DELETE */}
        <Dialog open={deleteModalOpen} onClose={cancelDelete}>
          <DialogTitle sx={{ display: 'flex', alignItems: 'center', fontWeight: 'bold', justifyContent: 'center', mt:2, fontSize:'26px' }}>
            <Box sx={{display: 'flex', alignItems: 'center'}}>
              <WarningAmberIcon sx={{ color: '#000', mr: 1}}/>
              Conferma richiesta
              <WarningAmberIcon sx={{ color: '#000', ml: 1}}/>
            </Box>
            <IconButton onClick={cancelDelete} sx={{ position: 'absolute', top:10, right:10 }} >
              <CloseIcon sx={{color:'#000'}} />
            </IconButton>
          </DialogTitle>
          <DialogContent>
            <DialogContentText sx={{ color: 'black', textAlign: 'center', fontSize:'20px', my:0.5, mx:1 }}>
              Vuoi davvero eliminare l’utente <strong>{deleteMemberName}</strong>?
              <br /> Una volta eliminato, non sarà possibile recuperarlo.
            </DialogContentText>
          </DialogContent>
          <DialogActions sx={{justifyContent: 'center', pb:2.5, mb:2}}>
            <Button variant="contained" onClick={confirmDelete}
              sx={{ bgcolor: '#d32f2f', color: '#fff', py:2.6, '&:hover': {bgcolor: '#c62828'} }} 
            >
              Elimina utente
            </Button>
          </DialogActions>
        </Dialog>

        {/* MODAL ADD USER */}
        <Dialog open={addModalOpen} onClose={closeAddModal}>
          <DialogTitle sx={{ fontWeight: 'bold', fontSize:'22px', textAlign:'center', mt:1, mx:8 }}>
            Aggiungi nuovo membro
          </DialogTitle>
          <DialogContent>
            <Box sx={{display:'flex', flexDirection:'column', gap:2, pt:1}}>
              <TextField label="Nome" value={newUser.name} onChange={e=>setNewUser({...newUser, name: e.target.value})} 
                size="small"
                sx={{
                    '& .MuiInputBase-input': {
                      fontSize: 16,     
                    },
                    '& .MuiInputLabel-root': {
                      fontSize: 16       
                    },
                  }}
              />
              <TextField label="Email" value={newUser.email} onChange={e=>setNewUser({...newUser, email: e.target.value})} 
                size="small"
                sx={{
                    '& .MuiInputBase-input': {
                      fontSize: 16,     
                    },
                    '& .MuiInputLabel-root': {
                      fontSize: 16       
                    },
                  }}
              />
              <TextField label="Password" type="password" value={newUser.password} onChange={e=>setNewUser({...newUser, password: e.target.value})} 
                size="small"
                sx={{
                    '& .MuiInputBase-input': {
                      fontSize: 16,     
                    },
                    '& .MuiInputLabel-root': {
                      fontSize: 16       
                    },
                  }}
              />
              {/* <TextField label="URL Avatar (opzionale)" value={newUser.avatar} onChange={e=>setNewUser({...newUser, avatar: e.target.value})} 
                size="small"
                sx={{
                    '& .MuiInputBase-input': {
                      fontSize: 16,     
                    },
                    '& .MuiInputLabel-root': {
                      fontSize: 16,
                    },
                  }}
              /> */}
            </Box>
          </DialogContent>
          <DialogActions sx={{justifyContent:'center', pb:2}}>
            <Button
              variant="contained"
              color="secondary"
              onClick={handleAddUser}
              disabled={!newUser.name || !newUser.email || !newUser.password}
            >
              Aggiungi
            </Button>
            <Button onClick={closeAddModal}>Annulla</Button>
          </DialogActions>
        </Dialog>
      </Box>
    </Layout>
  );
};

export default TeamManagement;