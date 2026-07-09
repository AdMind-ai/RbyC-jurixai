import { api } from '../api/api';

export interface ComplianceDocument {
  key: string;
  name: string;
  folder: string;
  size: number;
  lastModified: string | null;
  storageClass?: string | null;
}

export interface ComplianceDocumentListResponse {
  bucket: string;
  prefix: string;
  trash: boolean;
  documents: ComplianceDocument[];
}

export const complianceDocumentFolders = [
  'documents/regulatory/banca-ditalia/',
  'documents/regulatory/consob/',
  'documents/regulatory/eur-lex/',
  'documents/regulatory/normattiva-gazzetta/',
  'documents/regulatory/esma/',
  'documents/regulatory/eba/',
  'documents/regulatory/ivass/',
  'documents/regulatory/assogestioni/',
  'documents/regulatory/fonte-da-definire/',
] as const;

export type ComplianceDocumentFolder = typeof complianceDocumentFolders[number];

export const checkComplianceDocumentsService = {
  async listDocuments(trash = false) {
    const { data } = await api.get<ComplianceDocumentListResponse>(
      '/check-compliance/documents/',
      { params: { trash } }
    );
    return data;
  },

  async uploadDocuments(files: File[], prefix: string) {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('file', file);
    });
    formData.append('prefix', prefix);

    const { data } = await api.post('/check-compliance/documents/upload/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  async moveToTrash(key: string) {
    const { data } = await api.post('/check-compliance/documents/delete/', { key });
    return data;
  },

  async restoreDocument(key: string) {
    const { data } = await api.post('/check-compliance/documents/restore/', { key });
    return data;
  },
};
