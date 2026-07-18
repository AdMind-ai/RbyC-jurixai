import React, { useEffect, useState } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { api } from '../../api/api';
import { RefreshCw, AlertCircle, Zap } from 'lucide-react';

// ─── Types ────────────────────────────────────────────────────────────────────

interface DailyEntry {
  date: string;
  openai_cost_eur: number | null;
  anthropic_cost_eur: number | null;
  total_cost_eur: number | null;
  total_cost_with_markup_eur: number | null;
}

interface VeraDailyResponse {
  days: number;
  series: DailyEntry[];
}

interface ChartPoint {
  date: string;
  /** Costo finale al cliente, calcolato dal backend con margine + IVA. */
  cost: number | null;
}

// ─── Costanti ─────────────────────────────────────────────────────────────────

const fmtEur = (n: number | null, maximumFractionDigits = 2) =>
  n == null
    ? '-'
    : n.toLocaleString('it-IT', {
        style: 'currency',
        currency: 'EUR',
        minimumFractionDigits: Math.min(2, maximumFractionDigits),
        maximumFractionDigits,
      });

const fmtDate = (iso: string) => {
  const [, m, d] = iso.split('-');
  return `${d}/${m}`;
};

// ─── Custom Tooltip ───────────────────────────────────────────────────────────

const CustomTooltip: React.FC<{ active?: boolean; payload?: any[]; label?: string }> = ({
  active, payload, label,
}) => {
  if (!active || !payload?.length) return null;
  const [y, m, d] = (label ?? '').split('-');
  return (
    <div className="bg-white border border-slate-100 shadow-lg rounded-xl px-4 py-3 min-w-[140px]">
      <p className="text-[11px] text-slate-400 font-medium mb-1.5">{`${d}/${m}/${y}`}</p>
      <p className="text-sm font-semibold text-slate-800">
        {payload[0].value != null ? fmtEur(payload[0].value as number) : '-'}
      </p>
      <p className="text-[10px] text-slate-400 mt-0.5">IVA inclusa</p>
    </div>
  );
};

// ─── Durations ────────────────────────────────────────────────────────────────

const DAYS_OPTIONS = [7, 14, 30, 90];

// ─── Main component ───────────────────────────────────────────────────────────

const VevaUsageChart: React.FC = () => {
  const [points, setPoints] = useState<ChartPoint[]>([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState<string | null>(null);
  const [days, setDays]         = useState(30);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = async (d: number, silent = false) => {
    silent ? setRefreshing(true) : setLoading(true);
    setError(null);
    try {
      const { data: resp } = await api.get<VeraDailyResponse>('/vera/usage/daily/', {
        params: {
          days: d,
        },
      });
      const pts: ChartPoint[] = resp.series.map((r) => ({
        date: r.date,
        cost: r.total_cost_with_markup_eur,
      }));
      setPoints(pts);
    } catch {
      setError('Impossibile caricare i dati di consumo Vera.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => { fetchData(days); }, [days]);

  const totalCost = points.reduce((s, r) => s + (r.cost ?? 0), 0);
  const totalCostLabel = fmtEur(totalCost);
  const hasData   = points.some(r => r.cost != null && r.cost > 0);
  const hasCost   = points.some(r => r.cost != null);

  return (
    <div className="apple-card space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div
            className="w-8 h-8 rounded-xl flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, #1e3a8a 0%, #1b9162 100%)' }}
          >
            <Zap size={15} className="text-white" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-slate-800">Consumo Agente Vera</h2>
            <p className="text-[11px] text-slate-400">Costo giornaliero (IVA 22% inclusa)</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Days selector */}
          <div className="flex bg-slate-100 rounded-xl p-1 gap-0.5">
            {DAYS_OPTIONS.map((d) => (
              <button
                key={d}
                onClick={() => setDays(d)}
                className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all duration-150 ${
                  days === d
                    ? 'bg-white shadow-sm text-[#1e3a8a]'
                    : 'text-slate-400 hover:text-slate-600'
                }`}
              >
                {d}g
              </button>
            ))}
          </div>
          <button
            onClick={() => fetchData(days, true)}
            disabled={refreshing}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
          >
            <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* KPI unico */}
      <div className="flex items-end gap-1.5 pb-4 border-b border-slate-100">
        <span className="text-2xl font-semibold text-slate-800">
          {hasCost ? totalCostLabel : '—'}
        </span>
        <span className="text-[12px] text-slate-400 pb-1">ultimi {days} giorni</span>
      </div>

      {/* Chart */}
      <div className="h-52">
        {loading ? (
          <div className="h-full flex items-center justify-center gap-2 text-slate-400">
            <RefreshCw size={16} className="animate-spin" />
            <span className="text-[13px]">Caricamento…</span>
          </div>
        ) : error ? (
          <div className="h-full flex items-center justify-center gap-2 text-red-500">
            <AlertCircle size={16} />
            <span className="text-[13px]">{error}</span>
          </div>
        ) : !hasData ? (
          <div className="h-full flex flex-col items-center justify-center gap-2 text-center">
            <div className="w-10 h-10 rounded-2xl bg-slate-100 flex items-center justify-center">
              <Zap size={20} className="text-slate-300" />
            </div>
            <p className="text-[13px] text-slate-500 font-medium">Nessun dato disponibile</p>
            <p className="text-[12px] text-slate-400 max-w-[280px] leading-relaxed">
              I dati appariranno dopo la sincronizzazione dei costi Vera dai provider.
            </p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={points} margin={{ top: 4, right: 4, left: -10, bottom: 0 }}>
              <defs>
                <linearGradient id="gradVera" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#1e3a8a" stopOpacity={0.18} />
                  <stop offset="95%" stopColor="#1e3a8a" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
              <XAxis
                dataKey="date"
                tickFormatter={fmtDate}
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 10, fill: '#94A3B8', fontWeight: 500 }}
                dy={8}
                interval={days <= 14 ? 0 : Math.floor(days / 10)}
              />
              <YAxis
                tickFormatter={(v) => fmtEur(v as number, 0)}
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 10, fill: '#94A3B8', fontWeight: 500 }}
                width={54}
              />
              <Tooltip content={<CustomTooltip />} />
              <Area
                type="monotone"
                dataKey="cost"
                name="Costo"
                stroke="#1e3a8a"
                strokeWidth={2}
                fill="url(#gradVera)"
                dot={false}
                activeDot={{ r: 4, strokeWidth: 0, fill: '#1e3a8a' }}
                connectNulls
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
};

export default VevaUsageChart;

