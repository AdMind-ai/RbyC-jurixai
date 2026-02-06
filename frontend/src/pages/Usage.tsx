
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { ChevronDown } from 'lucide-react';

import ConsumptionTable from '../components/UsagePage/ConsumptionTable';
import { formatEuro } from '../constants/usage';
import { useUsageReport } from '../hooks/useUsageReport';
import { usageService, UsageMonthOption } from '../services/usageService';

const UsagePage: React.FC = () => {
  const [monthOptions, setMonthOptions] = useState<UsageMonthOption[]>([]);
  const [monthsLoading, setMonthsLoading] = useState<boolean>(true);
  const [monthsError, setMonthsError] = useState<string | null>(null);
  const [period, setPeriod] = useState<string | null>(null);

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

  const { data: report, loading: reportLoading, error } = useUsageReport({ month: period ?? undefined });

  const totalCostDisplay = report
    ? formatEuro(report.totalCost)
    : reportLoading
      ? 'Caricamento...'
      : '—';

  const selectedPeriodLabel = useMemo(() => {
    if (!period) {
      return 'Nessun periodo disponibile';
    }
    return monthOptions.find((option) => option.value === period)?.label || 'Periodo selezionato';
  }, [period, monthOptions]);

  return (
    <div className="min-h-screen p-8 lg:p-12 max-w-[1200px] mx-auto space-y-12 relative font-sans">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
        <div>
          <h1 className="text-3xl font-bold text-[#172554] tracking-tight">Consumo AI</h1>
          <p className="text-sm text-gray-400 font-normal mt-1">
            Monitoraggio costi e attività — {report?.monthLabel || selectedPeriodLabel}
          </p>
        </div>

        <div className="flex items-center gap-4">
          {/* Mini Card Totale */}
          <div className="bg-white border border-gray-100 rounded-2xl px-6 py-4 shadow-sm flex items-center justify-between gap-10 min-w-[320px]">
            <p className="text-sm font-normal text-gray-400 whitespace-nowrap">Totale periodo</p>
            <p className="text-[22px] font-bold text-[#1F3A8B] leading-none">{totalCostDisplay}</p>
          </div>

          {/* Selezione Periodo */}
          <div className="relative group h-full">
            <select
              value={period ?? ''}
              onChange={(e) => setPeriod(e.target.value || null)}
              disabled={monthsLoading || monthOptions.length === 0}
              className="appearance-none bg-white border border-gray-200 rounded-2xl py-4 pl-6 pr-14 text-base font-normal text-[#172554] focus:outline-none focus:ring-4 focus:ring-[#1F3A8B]/5 focus:border-[#1F3A8B] cursor-pointer transition-all shadow-sm group-hover:border-gray-300 h-full disabled:bg-gray-50 disabled:text-gray-400"
            >
              {monthOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none group-hover:text-[#172554] transition-colors" />
          </div>
        </div>
      </div>

      {/* Sezione Tabella */}
      <div className="space-y-6">
        {monthsError && (
          <div className="rounded-2xl border border-red-100 bg-red-50 text-red-700 px-5 py-4 text-sm">
            Errore nel caricamento dei periodi: {monthsError}
          </div>
        )}

        {monthsLoading && (
          <div className="rounded-2xl border border-dashed border-[#1F3A8B]/20 bg-white px-5 py-4 text-sm text-[#1F3A8B]">
            Caricamento periodi disponibili...
          </div>
        )}

        {!monthsLoading && !monthsError && monthOptions.length === 0 && (
          <div className="rounded-2xl border border-gray-100 bg-white px-5 py-4 text-sm text-gray-500">
            Nessun consumo registrato finora. Torna quando avrai almeno un evento di utilizzo.
          </div>
        )}

        {error && (
          <div className="rounded-2xl border border-red-100 bg-red-50 text-red-700 px-5 py-4 text-sm">
            Errore nel caricamento del report: {error.message}
          </div>
        )}

        {reportLoading && !report && period && (
          <div className="rounded-2xl border border-dashed border-[#1F3A8B]/20 bg-white px-5 py-4 text-sm text-[#1F3A8B]">
            Caricamento dati per {selectedPeriodLabel}...
          </div>
        )}

        {report && <ConsumptionTable report={report} />}
      </div>
    </div>
  );
};

export default UsagePage;
