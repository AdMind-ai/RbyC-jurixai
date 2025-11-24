
export enum CompanyType {
  SRL = 'S.r.l.',
  SPA = 'S.p.A.',
  SAPAA = 'S.a.p.a.',
  SRLS = 'S.r.l.s.'
}

export enum Role {
  AMMINISTRATORE_UNICO = 'Amministratore Unico',
  CONSIGLIERE = 'Consigliere',
  PRESIDENTE_CDA = 'Presidente CdA',
  SINDACO = 'Sindaco',
  REVISORE = 'Revisore'
}

export interface Officer {
  id: string;
  name: string;
  role: Role;
  appointedDate: string;
  expiryDate: string; // ISO Date string
}

export interface Shareholder {
  id: string;
  name: string;
  quotaPercentage: number;
}

export interface Company {
  id: string;
  name: string;
  vatNumber: string; // Partita IVA
  type: CompanyType;
  address: string;
  officers: Officer[];
  shareholders: Shareholder[];
  capital: number;
  nextMeetingDate?: string;
  status: 'Active' | 'Liquidation' | 'Inactive';
  letterheadInfo?: string; // Text details
  letterheadFile?: { // File details (PDF/Image)
    data: string; // base64
    mimeType: string;
    name: string;
  };
}

export interface Deadline {
  id: string;
  companyId: string;
  title: string;
  dueDate: string;
  completed: boolean;
  type: 'TAX' | 'CORPORATE' | 'LEGAL';
}

export interface GeneratedDocument {
  id: string;
  title: string;
  content: string;
  createdAt: string;
  type: 'VERBALE' | 'DELIBERA' | 'EMAIL';
}

export interface AppUser {
  id: string;
  name: string;
  role: 'Admin' | 'Editor' | 'Viewer';
  email: string;
  createdDate: string;
  lastModified: string;
  avatarColor: string; // hex code
}