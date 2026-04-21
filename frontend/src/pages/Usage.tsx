
import React, { useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { ChevronDown, CreditCard, ExternalLink } from 'lucide-react';

import ConsumptionTable from '../components/UsagePage/ConsumptionTable';
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
    loadBillingStatus();
  }, [loadBillingStatus]);

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
    if (!period) {
      setBillingSummary(null);
      setBillingSummaryError(null);
      setBillingSummaryLoading(false);
      return;
    }
    loadBillingSummary(period);
  }, [period, loadBillingSummary]);

  const { data: report, loading: reportLoading, error } = useUsageReport({ month: period ?? undefined });

  const subtotalWithMarkupDisplay = billingSummary
    ? formatEuro(billingSummary.subtotalWithMarkupEur)
    : billingSummaryLoading
      ? 'Caricamento...'
      : '—';

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
    <div className="min-h-screen p-8 lg:p-12 max-w-[1200px] mx-auto space-y-10 relative font-sans">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
        <div>
          <h1 className="text-3xl font-bold text-[#172554] tracking-tight">Consumo AI</h1>
          <p className="text-sm text-gray-400 font-normal mt-1">
            Monitoraggio attività — {report?.monthLabel || selectedPeriodLabel}
          </p>
        </div>

        <div className="flex items-center gap-4">
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

      <div className="bg-white border border-gray-100 rounded-2xl px-6 py-5 shadow-sm">
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_1.2fr] gap-6 lg:gap-8 items-start">
          <div>
            <div className="flex items-start justify-between gap-6">
              <p className="text-sm font-normal text-gray-400 whitespace-nowrap">Totale periodo</p>
              <p className="text-[26px] font-bold text-[#1F3A8B] leading-none text-right">{subtotalWithMarkupDisplay}</p>
            </div>
            <div className="mt-4 pt-4 border-t border-gray-100 space-y-3">
              <div className="flex items-center justify-between gap-6">
                <p className="text-sm font-normal text-gray-400 whitespace-nowrap">Totale con IVA</p>
                <p className="text-sm font-bold text-[#172554] leading-none text-right">{totalWithVatDisplay}</p>
              </div>
              <div className="flex items-center justify-between gap-6">
                <p className="text-sm font-normal text-gray-400 whitespace-nowrap">Addebito previsto</p>
                <p className="text-sm font-semibold text-[#172554] leading-none text-right">{chargeDateDisplay}</p>
              </div>
              {billingSummaryError && (
                <p className="text-xs text-amber-600 truncate">{billingSummaryError}</p>
              )}
            </div>
          </div>

          <div className="lg:border-l lg:border-gray-100 lg:pl-8">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-3 min-w-0">
                <div className="w-10 h-10 rounded-xl bg-[#1F3A8B]/10 text-[#1F3A8B] flex items-center justify-center shrink-0">
                  <CreditCard className="w-5 h-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-xs text-gray-400 font-semibold uppercase">Metodo di pagamento</p>
                  <p className="text-base font-bold text-[#172554] mt-1 truncate">{billingLoading ? 'Caricamento...' : cardLabel}</p>
                  <p className="text-xs text-gray-500 mt-1">{cardExpiry}</p>
                  {billingStatus?.latestInvoice && (
                    <p className="text-xs text-gray-400 mt-2 truncate">
                      Ultima fattura {billingStatus.latestInvoice.periodMonth}: {formatEuro(billingStatus.latestInvoice.amountEur)} - {billingStatus.latestInvoice.status}
                    </p>
                  )}
                  {billingError && (
                    <p className="text-xs text-red-600 mt-2">{billingError}</p>
                  )}
                </div>
              </div>

              <div className="flex flex-col gap-2 shrink-0 items-end">
                {isAdmin && (
                  <button
                    onClick={handleSetupPaymentMethod}
                    disabled={billingActionLoading}
                    className="inline-flex items-center justify-center gap-2 bg-[#1F3A8B] text-white hover:bg-[#172554] disabled:bg-gray-300 px-3 py-2 rounded-lg text-xs font-semibold transition-colors whitespace-nowrap"
                  >
                    <CreditCard className="w-4 h-4" />
                    {billingStatus?.paymentMethodReady ? 'Aggiorna carta' : 'Registra carta'}
                  </button>
                )}
                {billingStatus?.latestInvoice?.hostedInvoiceUrl && (
                  <a
                    href={billingStatus.latestInvoice.hostedInvoiceUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center justify-center gap-2 border border-gray-200 text-[#172554] bg-white hover:bg-gray-50 px-3 py-2 rounded-lg text-xs font-semibold transition-colors whitespace-nowrap"
                  >
                    <ExternalLink className="w-4 h-4" />
                    Apri fattura
                  </a>
                )}
              </div>
            </div>
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
