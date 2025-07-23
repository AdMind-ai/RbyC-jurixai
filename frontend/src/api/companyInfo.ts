// src/api/companyInfo.ts

import { api } from './api';
import type { CompanyInfoAdm } from '../interfaces/companyInfoInterface';

export async function fetchCompanyInfo(): Promise<CompanyInfoAdm | null> {
  const res = await api.get('/company-info/');
  return res.data as CompanyInfoAdm;
}