import React, { useEffect, useState, useMemo } from "react";
import {
  Box, Typography, Avatar, Button,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper,
  Dialog, DialogTitle, DialogContent, DialogActions, DialogContentText, TextField,
  IconButton, Link, Tooltip, TableSortLabel, TableFooter, TablePagination, 
  InputAdornment, Select, MenuItem
} from '@mui/material';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import CloseIcon from '@mui/icons-material/Close';
import SearchIcon from '@mui/icons-material/Search';
import Layout from '../layouts/Layout';

// Atualize o tipo do Member
export interface Member {
  id: number;
  name: string;
  email: string;
  role: string;
  avatar: string;
  password: string;
  createdAt: string;    
  modifiedAt: string;   
}

// Função para gerar data/hora do momento
function nowIso() {
  return new Date().toISOString();
}

// Função simulando fetch
function mockFetchMembers(): Promise<Member[]> {
  const now = Date.now();
  const firstNames = [
    "Luca", "Giulia", "Marco", "Anna", "Simone", "Sara", "Matteo", "Alice",
    "Francesco", "Elena", "Davide", "Martina", "Andrea", "Chiara", "Gabriele",
    "Valentina", "Alessio", "Federica", "Stefano", "Roberta", "Paolo",
    "Giorgia", "Alessandra", "Emanuele", "Serena", "Cristian", "Camilla",
    "Filippo", "Silvia", "Edoardo"
  ];
  const lastNames = [
    "Bianchi", "Rossi", "Verdi", "Neri", "Russo", "Ferrari", "Romano",
    "Gallo", "Costa", "Fontana", "Conti", "Esposito", "Ricci", "Marino",
    "Greco", "Bruno", "Galli", "Moretti", "De Luca", "Barbieri", "Rizzo",
    "Lombardi", "Martini", "Leone", "Longo", "Gentile", "Martinelli",
    "Vitale", "Bianco", "Lorenzi"
  ];
  const roles = ['Admin', 'Editor', 'Viewer'];
  
  const members: Member[] = Array.from({length: 30}, (_, i) => {
    const gender = i % 2 === 0 ? "men" : "women";
    return {
      id: i + 1,
      name: `${firstNames[i]} ${lastNames[i]}`,
      email: `${firstNames[i].toLowerCase()}.${lastNames[i].toLowerCase()}@email.com`,
      role: roles[i % roles.length],
      avatar: `https://randomuser.me/api/portraits/${gender}/${10+(i%80)}.jpg`,
      password: "",
      createdAt: new Date(now - 1000*60*60*24*(Math.floor(Math.random()*30+1))).toISOString(),
      modifiedAt: new Date(now - 1000*60*60*24*(Math.floor(Math.random()*10+1))).toISOString(),
    };
  });
  return Promise.resolve(members);
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
        <Avatar src={m.avatar} alt={m.name} />
        <span style={{fontSize: '16px'}}>{m.name}</span>
      </Box>
    )
  },
  {
    key: "email", label: "Email", sortable: true,
  },
  {
    key: "role", label: "Ruolo", sortable: true,
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

const TeamManagement: React.FC = () => {
  // Data
  const [members, setMembers] = useState<Member[]>([]);
  const rolesArray = ['Admin', 'Editor', 'Viewer'];
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
  const [deleteMember, setDeleteMember] = useState<Member | null>(null);
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [newUser, setNewUser] = useState({
    name:'', email:'', role:'', avatar:'', password:''
  });

  useEffect(() => {
    // fetch members from mock API
    mockFetchMembers().then(list => setMembers(list));
  }, []);

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
      if (orderBy === "createdAt" || orderBy === "modifiedAt") {
        // Sort by date
        return (order==="asc" ? 1 : -1) * (valA > valB ? 1 : -1);
      }
      if (typeof valA === "string" && typeof valB === "string") {
        return (order==="asc" ? 1 : -1) * valA.localeCompare(valB);
      }
      // fallback:
      if (valA === valB) return 0;
      return (order==="asc" ? 1 : -1) * (valA > valB ? 1 : -1);
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

  function openPasswordModal(member: Member) {
    setPasswordMember(member);
    setNewPassword('');
    setPasswordModalOpen(true);
  }
  function closePasswordModal() {
    setPasswordModalOpen(false);
  }
  function handlePasswordChange() {
    if (!passwordMember) return;
    setMembers(prev =>
      prev.map(m =>
        m.id === passwordMember.id
          ? { ...m, password: newPassword, modifiedAt: nowIso() }
          : m
      )
    );
    closePasswordModal();
  }

  function openDeleteModal(member: Member) {
    setDeleteMember(member);
    setDeleteModalOpen(true);
  }
  function cancelDelete() {
    setDeleteModalOpen(false);
  }
  function confirmDelete() {
    setMembers(prev => prev.filter(m => m.id !== deleteMember?.id));
    setDeleteModalOpen(false);
  }

  function openAddModal() {
    setAddModalOpen(true);
    setNewUser({name:'', email:'', role:'', avatar:'', password:''});
  }
  function closeAddModal() { setAddModalOpen(false); }
  function handleAddUser() {
    const now = nowIso();
    setMembers(prev => [
      ...prev,
      {
        id: Date.now()+Math.floor(Math.random()*1000),
        ...newUser,
        avatar: newUser.avatar || `https://randomuser.me/api/portraits/lego/${Math.floor(Math.random()*10)}.jpg`,
        createdAt: now,
        modifiedAt: now,
      }
    ]);
    setAddModalOpen(false);
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
            Accessi
          </Typography>
          <Button
            variant="outlined"
            color="secondary"
            sx={{ width: '190px' }}
            onClick={openAddModal}
          >
            + Aggiungi membro
          </Button>
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
                      <Link 
                        sx={{ cursor: 'pointer', fontSize: '16px', color:'grey', marginRight:2 }}
                        component="button"
                        onClick={()=>openPasswordModal(member)}
                        underline="hover"
                      >
                        Reimposta password
                      </Link>
                      <Tooltip title="Elimina membro">
                        <IconButton
                          color="error"
                          onClick={()=>openDeleteModal(member)}
                        >
                          <DeleteOutlineIcon sx={{fontSize:25}}/>
                        </IconButton>
                      </Tooltip>
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
              Vuoi davvero eliminare l’utente <strong>{deleteMember?.name}</strong>?
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
              <Select
                value={newUser.role}
                onChange={e=>setNewUser({...newUser, role: e.target.value as string})}
                displayEmpty
                fullWidth
                size="small"
                sx={{
                  fontSize: 14,
                  '& .MuiSelect-select': { fontSize: 14 },
                  '& .MuiInputLabel-root': { fontSize: 14 }
                }}
                renderValue={(selected) => selected ? selected : "Seleziona ruolo"}
                MenuProps={{
                  PaperProps: {
                    sx: {
                      fontSize: 14, 
                      '& .MuiMenuItem-root': {
                        fontSize: 14  
                      }
                    }
                  }
                }}
              >
                {rolesArray.map(role =>
                  <MenuItem key={role} value={role}>{role}</MenuItem>
                )}
              </Select>
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
              <TextField label="URL Avatar (opzionale)" value={newUser.avatar} onChange={e=>setNewUser({...newUser, avatar: e.target.value})} 
                size="small"
                sx={{
                    '& .MuiInputBase-input': {
                      fontSize: 16,     
                    },
                    '& .MuiInputLabel-root': {
                      fontSize: 16,
                    },
                  }}
              />
            </Box>
          </DialogContent>
          <DialogActions sx={{justifyContent:'center', pb:2}}>
            <Button
              variant="contained"
              color="secondary"
              onClick={handleAddUser}
              disabled={!newUser.name || !newUser.email || !newUser.role || !newUser.password}
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