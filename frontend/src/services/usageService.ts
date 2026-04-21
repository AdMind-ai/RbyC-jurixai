import { api } from '../api/api';
import { MonthlyReport } from '../types/types';

export interface UsageReportParams {
  month: string;
  userId?: number;
  companyId?: number;
}

export interface UsageMonthOption {
  value: string;
  label: string;
}

export const usageService = {
  async getMonthlyReport(params: UsageReportParams) {
    const queryParams: Record<string, string | number> = {
      month: params.month,
    };

    if (typeof params.userId === 'number') {
      queryParams.userId = params.userId;
    }

    if (typeof params.companyId === 'number') {
      queryParams.companyId = params.companyId;
    }

    const { data } = await api.get<MonthlyReport>('/usage/report/', {
      params: queryParams,
    });
    return data;
  },

  async getAvailableMonths(params?: { userId?: number; companyId?: number }) {
    const queryParams: Record<string, number> = {};
    if (typeof params?.userId === 'number') {
      queryParams.userId = params.userId;
    }
    if (typeof params?.companyId === 'number') {
      queryParams.companyId = params.companyId;
    }

    const { data } = await api.get<UsageMonthOption[]>('/usage/months/', {
      params: queryParams,
    });
    return data;
  },
};
