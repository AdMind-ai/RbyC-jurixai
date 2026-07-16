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
  documents: ComplianceDocument[];
}

export const checkComplianceDocumentsService = {
  async listDocuments() {
    const { data } = await api.get<ComplianceDocumentListResponse>(
      '/check-compliance/documents/'
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

  async getDownloadUrl(key: string) {
    const { data } = await api.post<{ url: string; expiresIn: number }>(
      '/check-compliance/documents/download/',
      { key }
    );
    return data;
  },

  async permanentlyDeleteDocument(key: string) {
    const { data } = await api.post('/check-compliance/documents/permanent-delete/', { key });
    return data;
  },
};
