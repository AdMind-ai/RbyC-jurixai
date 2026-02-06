import { useCallback, useEffect, useState } from 'react';

import { MonthlyReport } from '../types/types';
import { usageService } from '../services/usageService';

interface UseUsageReportParams {
  month?: string;
  userId?: number;
  companyId?: number;
}

interface UseUsageReportResult {
  data: MonthlyReport | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

export const useUsageReport = (
  params: UseUsageReportParams
): UseUsageReportResult => {
  const { month, userId, companyId } = params;
  const [data, setData] = useState<MonthlyReport | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchReport = useCallback(async (options?: { signal?: { cancelled: boolean } }) => {
    if (!month) {
      setData(null);
      setError(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const report = await usageService.getMonthlyReport({ month, userId, companyId });
      if (options?.signal?.cancelled) {
        return;
      }
      setData(report);
    } catch (err) {
      const fallbackError = err instanceof Error
        ? err
        : new Error('Erro ao carregar o relatório de uso.');
      if (!options?.signal?.cancelled) {
        setError(fallbackError);
      }
    } finally {
      if (!options?.signal?.cancelled) {
        setLoading(false);
      }
    }
  }, [month, userId, companyId]);

  useEffect(() => {
    const signal = { cancelled: false };
    fetchReport({ signal });
    return () => {
      signal.cancelled = true;
    };
  }, [fetchReport]);

  return {
    data,
    loading,
    error,
    refetch: fetchReport,
  };
};
