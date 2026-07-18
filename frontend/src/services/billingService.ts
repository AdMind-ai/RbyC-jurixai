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
  subtotalWithMarkupEur: number;
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
};
