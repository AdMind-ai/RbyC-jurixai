import { Company, CompanyType, Deadline, Officer, Role, Shareholder } from './types/types';

export const MOCK_COMPANIES: Company[] = [
  {
    id: 'c1',
    name: 'Innovazione Digitale',
    type: CompanyType.SRL,
    vatNumber: '01234567890',
    address: 'Via Roma 10, Milano',
    capital: 10000,
    status: 'Active',
    nextMeetingDate: '2024-04-30',
    officers: [
      { id: 'o1', name: 'Mario Rossi', role: Role.AMMINISTRATORE_UNICO, appointedDate: '2022-01-01', expiryDate: '2025-12-31' }
    ],
    shareholders: [
      { id: 's1', name: 'Mario Rossi', quotaPercentage: 60 },
      { id: 's2', name: 'Luigi Verdi', quotaPercentage: 40 }
    ]
  },
  {
    id: 'c2',
    name: 'Costruzioni Edili Nord',
    type: CompanyType.SPA,
    vatNumber: '09876543210',
    address: 'Corso Italia 50, Torino',
    capital: 120000,
    status: 'Active',
    nextMeetingDate: '2024-05-15',
    officers: [
      { id: 'o2', name: 'Giulia Bianchi', role: Role.PRESIDENTE_CDA, appointedDate: '2023-05-20', expiryDate: '2026-05-20' },
      { id: 'o3', name: 'Roberto Neri', role: Role.CONSIGLIERE, appointedDate: '2023-05-20', expiryDate: '2026-05-20' }
    ],
    shareholders: [
      { id: 's3', name: 'Holding Nord S.r.l.', quotaPercentage: 100 }
    ]
  },
  {
    id: 'c3',
    name: 'Green Energy Solutions',
    type: CompanyType.SRL,
    vatNumber: '11223344556',
    address: 'Via Verde 8, Bologna',
    capital: 25000,
    status: 'Active',
    officers: [
      { id: 'o4', name: 'Elena Gialli', role: Role.AMMINISTRATORE_UNICO, appointedDate: '2021-10-10', expiryDate: '2024-10-10' }
    ],
    shareholders: [
      { id: 's4', name: 'Elena Gialli', quotaPercentage: 100 }
    ]
  }
];

export const MOCK_DEADLINES: Deadline[] = [
  { id: 'd1', companyId: 'c1', title: 'Approvazione Bilancio 2023', dueDate: '2024-04-30', completed: false, type: 'CORPORATE' },
  { id: 'd2', companyId: 'c1', title: 'Pagamento IVA 1° Trimestre', dueDate: '2024-05-16', completed: true, type: 'TAX' },
  { id: 'd3', companyId: 'c2', title: 'Rinnovo Cariche Sociali', dueDate: '2026-05-20', completed: false, type: 'CORPORATE' },
  { id: 'd4', companyId: 'c3', title: 'Deposito Bilancio', dueDate: '2024-05-30', completed: false, type: 'LEGAL' },
  { id: 'd5', companyId: 'c2', title: 'Consiglio di Amministrazione Trimestrale', dueDate: '2024-06-15', completed: false, type: 'CORPORATE' }
];