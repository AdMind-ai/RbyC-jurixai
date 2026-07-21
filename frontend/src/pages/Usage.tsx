import React, { useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { ChevronDown, Clock3, TrendingUp } from 'lucide-react';

import ConsumptionTable from '../components/UsagePage/ConsumptionTable';
import VevaUsageChart from '../components/UsagePage/VevaUsageChart';
import { formatEuro } from '../constants/usage';
import { AuthContext } from '../context/AuthContext';
import { useUsageReport } from '../hooks/useUsageReport';
import { billingService, BillingMonthlySummary } from '../services/billingService';
import { usageService, UsageMonthOption } from '../services/usageService';

const formatUsageDate = (value?: string | null) => {
  if (!value) return '-';
  return new Date(value).toLocaleDateString('it-IT', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
  });
};

const UsagePage: React.FC = () => {
  const auth = useContext(AuthContext);
  const [monthOptions, setMonthOptions] = useState<UsageMonthOption[]>([]);
  const [monthsLoading, setMonthsLoading] = useState<boolean>(true);
  const [monthsError, setMonthsError] = useState<string | null>(null);
  const [period, setPeriod] = useState<string | null>(null);
  const [billingSummary, setBillingSummary] = useState<BillingMonthlySummary | null>(null);
  const [billingSummaryLoading, setBillingSummaryLoading] = useState<boolean>(false);
  const [billingSummaryError, setBillingSummaryError] = useState<string | null>(null);

  const isAdmin = auth?.user?.is_admin === true;
  const canViewFinancials = isAdmin;

  const loadMonths = useCallback(async () => {
    setMonthsLoading(true);
    try {
      const months = await usageService.getAvailableMonths();
      setMonthOptions(months);
      setPeriod((current) => {
        if (current && months.some((option) => option.value === current)) {
          return current;
        }
        return months[0]?.value ?? null;
      });
      setMonthsError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Errore nel recupero dei periodi disponibili.';
      setMonthsError(message);
      setMonthOptions([]);
      setPeriod(null);
    } finally {
      setMonthsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMonths();
  }, [loadMonths]);

  const loadBillingSummary = useCallback(async (selectedMonth: string) => {
    setBillingSummaryLoading(true);
    setBillingSummary(null);
    setBillingSummaryError(null);
    try {
      const summary = await billingService.getMonthlySummary(selectedMonth);
      setBillingSummary(summary);
      setBillingSummaryError(summary.refreshError);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Errore nel recupero del totale di fatturazione.';
      setBillingSummary(null);
      setBillingSummaryError(message);
    } finally {
      setBillingSummaryLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!period || !canViewFinancials) {
      setBillingSummary(null);
      setBillingSummaryError(null);
      setBillingSummaryLoading(false);
      return;
    }
    loadBillingSummary(period);
  }, [period, canViewFinancials, loadBillingSummary]);

  const { data: report, loading: reportLoading, error } = useUsageReport({ month: period ?? undefined });

  const subtotalDisplay = billingSummary
    ? formatEuro(billingSummary.amountEur)
    : billingSummaryLoading
      ? 'Caricamento...'
      : '-';
  const totalWithVatDisplay = billingSummary
    ? formatEuro(billingSummary.totalWithVatEur)
    : '-';
  const vatAmountDisplay = billingSummary
    ? formatEuro(Math.max(billingSummary.totalWithVatEur - billingSummary.amountEur, 0))
    : '-';
  const vatPercentage = billingSummary && typeof billingSummary.costBreakdown.ivaPercentage === 'number'
    ? billingSummary.costBreakdown.ivaPercentage
    : 22;

  const selectedPeriodLabel = useMemo(() => {
    if (!period) {
      return 'Nessun periodo disponibile';
    }
    return monthOptions.find((option) => option.value === period)?.label || 'Periodo selezionato';
  }, [period, monthOptions]);

  const lastUsageDate = formatUsageDate(report?.lastUsage?.occurredAt);
  const lastUsageText = report?.lastUsage
    ? `${report.lastUsage.totalRequests} ${report.lastUsage.totalRequests === 1 ? 'interazione' : 'interazioni'} quel giorno`
    : 'Nessun utilizzo registrato nel periodo';

  return (
    <div className="page-root">
      <div className="page-header">
        <div>
          <h3 className="page-title">Utilizzo</h3>
          <p className="text-sm text-slate-500 mt-1">Utilizzo dell'IA nell'applicazione web Rbyc</p>
        </div>
        <div className="relative max-w-[220px] w-full">
          <select
            value={period ?? ''}
            onChange={(e) => setPeriod(e.target.value || null)}
            disabled={monthsLoading || monthOptions.length === 0}
            className="apple-select"
          >
            {monthOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
        </div>
      </div>

      <div className="page-divider" />

      <div className="page-body space-y-6">
        {canViewFinancials && (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 w-full">
            <div className="apple-card relative overflow-hidden min-h-[150px] py-6 px-7 border-blue-100 bg-[#f4f7ff]">
              <div className="absolute left-0 top-0 h-full w-1 bg-[#3b559c]" />
              <div className="flex items-start justify-between gap-6">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 text-[13px] font-medium text-slate-500">
                    <span className="h-9 w-9 rounded-xl bg-[#3b559c]/10 text-[#3b559c] flex items-center justify-center shrink-0">
                      <TrendingUp size={18} />
                    </span>
                    <span>Consumo totale</span>
                  </div>
                  <div className="text-[34px] leading-tight font-semibold text-slate-900 mt-4">{subtotalDisplay}</div>
                  <p className="text-xs text-slate-500 mt-2">{selectedPeriodLabel}</p>
                  <div className="mt-4 pt-3 border-t border-blue-100/80 space-y-1.5 text-sm">
                    <div className="flex items-center justify-between gap-8 text-slate-500">
                      <span>IVA ({vatPercentage}%)</span>
                      <span>{vatAmountDisplay}</span>
                    </div>
                    <div className="flex items-center justify-between gap-8 font-semibold text-slate-900">
                      <span>Totale</span>
                      <span>{totalWithVatDisplay}</span>
                    </div>
                  </div>
                </div>
              </div>
              {billingSummaryError && (
                <p className="text-xs text-red-500 mt-2 truncate">{billingSummaryError}</p>
              )}
            </div>
            <div className="apple-card relative overflow-hidden min-h-[150px] py-6 px-7">
              <div className="flex items-start gap-5">
                <div className="h-12 w-12 rounded-xl bg-slate-100 text-slate-600 flex items-center justify-center shrink-0">
                  <Clock3 size={21} />
                </div>
                <div className="min-w-0">
                  <div className="text-[13px] font-medium text-slate-500">Ultimo utilizzo</div>
                  <div className="text-[30px] leading-tight font-semibold text-slate-900 mt-4">{lastUsageDate}</div>
                  <p className="text-xs text-slate-500 mt-2">{lastUsageText}</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {canViewFinancials && <VevaUsageChart />}

        <div className="space-y-4">
          {monthsError && (
            <div className="p-4 bg-red-50 text-red-700 rounded-xl text-sm border border-red-100">
              Errore nel caricamento dei periodi: {monthsError}
            </div>
          )}

          {monthsLoading && (
            <div className="p-4 bg-slate-50 text-slate-500 rounded-xl text-sm border border-slate-100">
              Caricamento periodi disponibili...
            </div>
          )}

          {!monthsLoading && !monthsError && monthOptions.length === 0 && (
            <div className="p-4 bg-slate-50 text-slate-500 rounded-xl text-sm border border-slate-100">
              Nessun consumo registrato finora. Torna quando avrai almeno un evento di utilizzo.
            </div>
          )}

          {error && (
            <div className="p-4 bg-red-50 text-red-700 rounded-xl text-sm border border-red-100">
              Errore nel caricamento del report: {error.message}
            </div>
          )}

          {reportLoading && !report && period && (
            <div className="p-4 bg-slate-50 text-slate-500 rounded-xl text-sm border border-slate-100">
              Caricamento dati per {selectedPeriodLabel}...
            </div>
          )}

          {report && (
            <div className="apple-card p-0 overflow-hidden">
              <div className="px-6 py-4 border-b border-slate-100 text-sm font-semibold text-slate-700">
                Dettaglio consumi
              </div>
              <ConsumptionTable report={report} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default UsagePage;
