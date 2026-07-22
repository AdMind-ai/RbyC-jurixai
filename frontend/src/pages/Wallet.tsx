import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  CreditCard,
  RefreshCw,
  RotateCw,
  WalletCards,
} from 'lucide-react';

import { formatEuro } from '../constants/usage';
import {
  billingService,
  WalletStatus,
  WalletTransaction,
} from '../services/billingService';

const TRANSACTIONS_PAGE_SIZE = 25;

const formatDateTime = (value: string) =>
  new Date(value).toLocaleDateString('it-IT', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

const transactionLabel: Record<string, string> = {
  credit: 'Credito',
  usage_debit: 'Consumo',
  auto_recharge: 'Auto-ricarica',
  manual_recharge: 'Ricarica',
  admin_adjustment: 'Admind',
  payment_failed: 'Pagamento fallito',
};

const WalletPage: React.FC = () => {
  const [wallet, setWallet] = useState<WalletStatus | null>(null);
  const [transactions, setTransactions] = useState<WalletTransaction[]>([]);
  const [transactionCount, setTransactionCount] = useState(0);
  const [transactionPage, setTransactionPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadWallet = useCallback(async (silent = false, page = transactionPage) => {
    if (silent) setRefreshing(true);
    else setLoading(true);
    setError(null);
    try {
      const offset = page * TRANSACTIONS_PAGE_SIZE;
      const [walletData, transactionData] = await Promise.all([
        billingService.getWallet(),
        billingService.getWalletTransactions(TRANSACTIONS_PAGE_SIZE, offset),
      ]);
      setWallet(walletData);
      setTransactions(transactionData.results ?? []);
      setTransactionCount(transactionData.count ?? 0);
      setTransactionPage(page);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Errore nel recupero della wallet.';
      setError(message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [transactionPage]);

  useEffect(() => {
    loadWallet(false, 0);
  }, []);

  const cardLabel = wallet?.paymentMethodReady && wallet.card
    ? `${(wallet.card.brand || 'Carta').toUpperCase()} **** ${wallet.card.last4 || '----'}`
    : 'Nessun metodo di pagamento registrato';

  const cardExpiry = wallet?.paymentMethodReady && wallet.card?.expMonth && wallet.card?.expYear
    ? `Scadenza ${String(wallet.card.expMonth).padStart(2, '0')}/${wallet.card.expYear}`
    : null;

  const autoRechargeLabel = useMemo(() => {
    if (!wallet?.autoRechargeEnabled) return 'Auto-ricarica disattivata';
    return `Auto-ricarica attiva - ${formatEuro(wallet.rechargeAmountEur)} quando scende a ${formatEuro(wallet.thresholdEur)}`;
  }, [wallet]);

  const handleSetupPaymentMethod = async () => {
    setActionLoading(true);
    setError(null);
    try {
      const session = await billingService.createSetupSession();
      window.location.assign(session.checkoutUrl);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Errore durante la creazione della sessione Stripe.';
      setError(message);
      setActionLoading(false);
    }
  };

  const handleRecharge = async () => {
    setActionLoading(true);
    setError(null);
    try {
      const result = await billingService.rechargeWallet();
      setWallet(result.wallet);
      await loadWallet(true, 0);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Errore durante la ricarica wallet.';
      setError(message);
    } finally {
      setActionLoading(false);
    }
  };

  const totalTransactionPages = Math.max(1, Math.ceil(transactionCount / TRANSACTIONS_PAGE_SIZE));
  const visibleTransactions = transactions ?? [];
  const hasPreviousTransactions = transactionPage > 0;
  const hasNextTransactions = transactionPage + 1 < totalTransactionPages;
  const transactionRangeStart = transactionCount === 0 ? 0 : transactionPage * TRANSACTIONS_PAGE_SIZE + 1;
  const transactionRangeEnd = Math.min((transactionPage + 1) * TRANSACTIONS_PAGE_SIZE, transactionCount);

  const changeTransactionPage = (nextPage: number) => {
    if (nextPage < 0 || nextPage >= totalTransactionPages) return;
    loadWallet(true, nextPage);
  };

  return (
    <div className="page-root">
      <div className="page-header">
        <div>
          <h1 className="page-title">Wallet</h1>
          <p className="text-[13px] text-slate-500 mt-0.5">
            Saldo, metodo di pagamento e storico transazioni
          </p>
        </div>
        <button
          onClick={() => loadWallet(true, transactionPage)}
          disabled={refreshing}
          className="btn-secondary py-2 px-3.5 gap-1.5 text-sm"
        >
          <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
          Aggiorna
        </button>
      </div>

      <div className="page-divider" />

      <div className="page-body space-y-8">
        {error && (
          <div className="flex items-center gap-3 bg-red-50 border border-red-100 rounded-xl px-5 py-4 text-red-600">
            <AlertCircle size={16} />
            <span className="text-[13px]">{error}</span>
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-24 gap-3 text-slate-400">
            <RefreshCw size={18} className="animate-spin" />
            <span className="text-[14px]">Caricamento wallet...</span>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
              <div className="apple-card min-h-[220px] border-orange-100 bg-orange-50/20">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-[12px] font-semibold uppercase text-slate-500">
                      Saldo disponibile
                    </p>
                    <p className="mt-4 text-5xl font-semibold text-slate-900">
                      {formatEuro(wallet?.balanceEur ?? 0)}
                    </p>
                  </div>
                  <WalletCards size={58} className="text-orange-200" />
                </div>
                <div className="mt-7 inline-flex items-center gap-2 rounded-full border border-emerald-100 bg-emerald-50 px-3 py-1.5 text-[12px] font-medium text-emerald-700">
                  <RotateCw size={13} />
                  {autoRechargeLabel}
                </div>
                {wallet?.lastError && (
                  <p className="mt-4 text-xs text-red-500">{wallet.lastError}</p>
                )}
              </div>

              <div className="apple-card min-h-[220px]">
                <h2 className="text-lg font-semibold text-slate-900">Metodo di pagamento</h2>
                <div className="mt-8 rounded-xl border border-dashed border-slate-200 px-6 py-8 text-center">
                  <CreditCard className="mx-auto h-9 w-9 text-slate-400" />
                  <p className="mt-4 text-sm font-medium text-slate-700">{cardLabel}</p>
                  {cardExpiry && <p className="mt-1 text-xs text-slate-400">{cardExpiry}</p>}
                  <div className="mt-6 flex flex-col sm:flex-row justify-center gap-3">
                    <button
                      onClick={handleSetupPaymentMethod}
                      disabled={actionLoading}
                      className="btn-primary"
                    >
                      <CreditCard size={15} />
                      {wallet?.paymentMethodReady ? 'Aggiorna carta' : 'Aggiungi carta'}
                    </button>
                    <button
                      onClick={handleRecharge}
                      disabled={actionLoading || !wallet?.paymentMethodReady}
                      className="btn-secondary"
                    >
                      <RotateCw size={15} />
                      Ricarica ora
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <section>
              <h2 className="text-lg font-semibold text-slate-900 mb-4">
                Cronologia transazioni
              </h2>
              <div className="apple-card p-0 overflow-hidden">
                <div className="hidden md:grid md:grid-cols-[150px_1fr_160px] gap-4 px-6 py-4 border-b border-slate-100 text-[11px] uppercase font-semibold text-slate-400">
                  <span>Data</span>
                  <span>Descrizione</span>
                  <span className="text-right">Importo</span>
                </div>
                {visibleTransactions.length === 0 ? (
                  <div className="px-6 py-12 text-center text-sm text-slate-400">
                    Nessuna transazione registrata.
                  </div>
                ) : (
                  visibleTransactions.map((item) => (
                    <div
                      key={item.id}
                      className="grid grid-cols-1 md:grid-cols-[150px_1fr_160px] gap-2 md:gap-4 px-6 py-4 border-b border-slate-50 last:border-b-0 md:items-center"
                    >
                      <span className="text-[13px] text-slate-500">
                        {formatDateTime(item.createdAt)}
                      </span>
                      <div className="min-w-0">
                        <p className="text-[13px] font-semibold text-slate-800">
                          {transactionLabel[item.transactionType] || item.transactionType}
                        </p>
                        <p className="text-[13px] text-slate-500 truncate">
                          {item.description}
                        </p>
                      </div>
                      <span
                        className={`md:text-right text-sm font-semibold ${
                          item.amountEur >= 0 ? 'text-emerald-600' : 'text-slate-900'
                        }`}
                      >
                        {item.amountEur >= 0 ? '+' : ''}
                        {formatEuro(item.amountEur)}
                      </span>
                    </div>
                  ))
                )}
                {transactionCount > TRANSACTIONS_PAGE_SIZE && (
                  <div className="flex flex-col gap-3 border-t border-slate-100 px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
                    <p className="text-xs text-slate-400">
                      {transactionRangeStart}-{transactionRangeEnd} di {transactionCount}
                    </p>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => changeTransactionPage(transactionPage - 1)}
                        disabled={!hasPreviousTransactions || refreshing}
                        className="btn-secondary py-1.5 px-3 text-xs disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        <ChevronLeft size={14} />
                        Indietro
                      </button>
                      <span className="text-xs font-medium text-slate-500">
                        {transactionPage + 1} / {totalTransactionPages}
                      </span>
                      <button
                        onClick={() => changeTransactionPage(transactionPage + 1)}
                        disabled={!hasNextTransactions || refreshing}
                        className="btn-secondary py-1.5 px-3 text-xs disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        Avanti
                        <ChevronRight size={14} />
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </section>
          </>
        )}
      </div>
    </div>
  );
};

export default WalletPage;
