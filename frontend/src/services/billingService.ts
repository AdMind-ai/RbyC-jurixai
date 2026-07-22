import { api } from '../api/api';

export interface BillingCard {
  brand: string | null;
  last4: string | null;
  expMonth: number | null;
  expYear: number | null;
}

export interface BillingInvoice {
  periodMonth: string;
  amountEur: number;
  currency: string;
  status: string;
  paidAt: string | null;
  hostedInvoiceUrl: string | null;
  invoicePdf: string | null;
  lastError: string | null;
}

export interface BillingStatus {
  paymentMethodReady: boolean;
  stripeCustomerReady: boolean;
  card: BillingCard | null;
  latestInvoice: BillingInvoice | null;
}

export interface WalletStatus {
  balanceEur: number;
  currency: string;
  autoRechargeEnabled: boolean;
  rechargeAmountEur: number;
  thresholdEur: number;
  paymentMethodReady: boolean;
  stripeCustomerReady: boolean;
  card: BillingCard | null;
  lastError: string | null;
  needsRecharge: boolean;
}

export interface WalletTransaction {
  id: number;
  transactionType: string;
  status: string;
  amountEur: number;
  balanceAfterEur: number;
  description: string;
  stripePaymentIntentId: string | null;
  stripeInvoiceId: string | null;
  periodStart: string | null;
  periodEnd: string | null;
  metadata: Record<string, unknown>;
  createdAt: string;
}

export interface WalletTransactionPage {
  count: number;
  limit: number;
  offset: number;
  results: WalletTransaction[];
}

export interface WalletRechargeResponse {
  transaction: WalletTransaction;
  wallet: WalletStatus;
}

export interface ProviderMonthlyCost {
  provider: string;
  providerAmount: number;
  amountWithMarkup: number;
  totalWithVat: number;
  currency: string;
  source: string;
  fetchedAt: string | null;
  metadata: Record<string, unknown>;
}

export interface BillingMonthlySummary {
  periodMonth: string;
  amountEur: number;
  totalWithVatEur: number;
  veraTotalWithVatEur: number;
  currency: string;
  chargeDate: string;
  isFresh: boolean;
  refreshError: string | null;
  invoice: BillingInvoice | null;
  providerCosts: ProviderMonthlyCost[];
  costBreakdown: Record<string, unknown>;
}

export const billingService = {
  async getStatus() {
    const { data } = await api.get<BillingStatus>('/billing/status/');
    return data;
  },

  async getMonthlySummary(month: string) {
    const { data } = await api.get<BillingMonthlySummary>('/billing/monthly-summary/', {
      params: { month },
    });
    return data;
  },

  async createSetupSession() {
    const { data } = await api.post<{ checkoutUrl: string; sessionId: string }>(
      '/billing/setup-session/'
    );
    return data;
  },

  async getWallet() {
    const { data } = await api.get<WalletStatus>('/billing/wallet/');
    return data;
  },

  async getWalletTransactions(limit = 25, offset = 0) {
    const { data } = await api.get<WalletTransactionPage | WalletTransaction[]>('/billing/wallet/transactions/', {
      params: { limit, offset },
    });
    if (Array.isArray(data)) {
      return {
        count: data.length,
        limit,
        offset,
        results: data,
      };
    }
    return {
      count: data.count ?? 0,
      limit: data.limit ?? limit,
      offset: data.offset ?? offset,
      results: Array.isArray(data.results) ? data.results : [],
    };
  },

  async rechargeWallet() {
    const { data } = await api.post<WalletRechargeResponse>('/billing/wallet/recharge/');
    return data;
  },
};
