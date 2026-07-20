
import React, { useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { ChevronDown, CreditCard } from 'lucide-react';

import ConsumptionTable from '../components/UsagePage/ConsumptionTable';
import VevaUsageChart from '../components/UsagePage/VevaUsageChart';
import { formatEuro } from '../constants/usage';
import { AuthContext } from '../context/AuthContext';
import { useUsageReport } from '../hooks/useUsageReport';
import { billingService, BillingMonthlySummary, BillingStatus } from '../services/billingService';
import { usageService, UsageMonthOption } from '../services/usageService';

const UsagePage: React.FC = () => {
  const auth = useContext(AuthContext);
  const [monthOptions, setMonthOptions] = useState<UsageMonthOption[]>([]);
  const [monthsLoading, setMonthsLoading] = useState<boolean>(true);
  const [monthsError, setMonthsError] = useState<string | null>(null);
  const [period, setPeriod] = useState<string | null>(null);
  const [billingStatus, setBillingStatus] = useState<BillingStatus | null>(null);
  const [billingSummary, setBillingSummary] = useState<BillingMonthlySummary | null>(null);
  const [billingSummaryLoading, setBillingSummaryLoading] = useState<boolean>(false);
  const [billingSummaryError, setBillingSummaryError] = useState<string | null>(null);
  const [billingLoading, setBillingLoading] = useState<boolean>(true);
  const [billingActionLoading, setBillingActionLoading] = useState<boolean>(false);
  const [billingError, setBillingError] = useState<string | null>(null);

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

  const loadBillingStatus = useCallback(async () => {
    setBillingLoading(true);
    try {
      const status = await billingService.getStatus();
      setBillingStatus(status);
      setBillingError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Errore nel recupero dei dati di pagamento.';
      setBillingError(message);
      setBillingStatus(null);
    } finally {
      setBillingLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!canViewFinancials) {
      setBillingStatus(null);
      setBillingLoading(false);
      return;
    }
    loadBillingStatus();
  }, [canViewFinancials, loadBillingStatus]);

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


  const totalWithVatDisplay = billingSummary
    ? formatEuro(billingSummary.totalWithVatEur)
    : billingSummaryLoading
      ? 'Caricamento...'
      : '-';

  const chargeDateDisplay = billingSummary
    ? new Date(`${billingSummary.chargeDate}T00:00:00`).toLocaleDateString('it-IT', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    })
    : billingSummaryLoading
      ? 'Caricamento...'
      : '-';

  const selectedPeriodLabel = useMemo(() => {
    if (!period) {
      return 'Nessun periodo disponibile';
    }
    return monthOptions.find((option) => option.value === period)?.label || 'Periodo selezionato';
  }, [period, monthOptions]);

  const cardLabel = billingStatus?.paymentMethodReady && billingStatus.card
    ? `${(billingStatus.card.brand || 'Carta').toUpperCase()} **** ${billingStatus.card.last4 || '----'}`
    : 'Nessuna carta registrata';

  const cardExpiry = billingStatus?.paymentMethodReady && billingStatus.card?.expMonth && billingStatus.card?.expYear
    ? `Scadenza ${String(billingStatus.card.expMonth).padStart(2, '0')}/${billingStatus.card.expYear}`
    : 'La carta verra usata per la fattura mensile automatica.';

  const handleSetupPaymentMethod = async () => {
    setBillingActionLoading(true);
    setBillingError(null);
    try {
      const session = await billingService.createSetupSession();
      window.location.assign(session.checkoutUrl);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Errore durante la creazione della sessione Stripe.';
      setBillingError(message);
      setBillingActionLoading(false);
    }
  };

  return (
    <div className="page-root">
      <div className="page-header">
        <h1 className="page-title">Consumo AI</h1>
        <div className="relative max-w-[200px] w-full">
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
        {/* KPI Cards */}
        {canViewFinancials && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="apple-card">
              <div className="text-[13px] text-slate-400">Totale con IVA</div>
              <div className="text-2xl font-semibold text-slate-800 mt-1">{totalWithVatDisplay}</div>
              <p className="text-xs text-slate-400 mt-2">Addebito previsto: {chargeDateDisplay}</p>
              {billingSummaryError && (
                <p className="text-xs text-red-500 mt-2 truncate">{billingSummaryError}</p>
              )}
            </div>
            <div className="apple-card">
              <div className="flex items-center gap-2 text-[13px] text-slate-400">
                Data addebito
              </div>
              <div className="text-2xl font-semibold text-slate-800 mt-1">{chargeDateDisplay}</div>
            </div>
          </div>
        )}

        {/* Metodo di pagamento */}
        {canViewFinancials && (
          <div className="apple-card flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <CreditCard className="text-slate-400 w-6 h-6" />
              <div>
                <div className="text-sm font-medium text-slate-800">Metodo di pagamento</div>
                <div className="text-[13px] text-slate-500">
                  {billingLoading ? 'Caricamento...' : cardLabel}
                  {!billingLoading && cardExpiry !== 'La carta verra usata per la fattura mensile automatica.' && ` • ${cardExpiry}`}
                </div>
                {billingError && (
                  <p className="text-xs text-red-500 mt-1">{billingError}</p>
                )}
              </div>
            </div>
            <button
              onClick={handleSetupPaymentMethod}
              disabled={billingActionLoading}
              className="btn-secondary whitespace-nowrap"
            >
              {billingStatus?.paymentMethodReady ? 'Aggiorna carta' : 'Aggiungi carta'}
            </button>
          </div>
        )}

        {/* Grafico consumo Vera */}
        {canViewFinancials && <VevaUsageChart />}

        {/* Tabella consumo */}
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
