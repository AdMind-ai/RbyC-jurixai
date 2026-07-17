import React, { useEffect, useState } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { api } from '../../api/api';
import { RefreshCw, AlertCircle, Zap } from 'lucide-react';

// ─── Types ────────────────────────────────────────────────────────────────────

interface DailyEntry {
  date: string;
  openai_tokens: number;
  anthropic_tokens: number;
  openai_cost_eur: number | null;
  anthropic_cost_eur: number | null;
  openai_requests: number;
  anthropic_requests: number;
  total_tokens: number;
  total_cost_eur: number | null;
}

interface VeraDailyResponse {
  days: number;
  series: DailyEntry[];
}

type Metric = 'tokens' | 'cost' | 'requests';

// ─── Helpers ──────────────────────────────────────────────────────────────────

const fmtDate = (iso: string) => {
  const [, m, d] = iso.split('-');
  return `${d}/${m}`;
};

const fmtTokens = (n: number) =>
  n >= 1_000_000
    ? `${(n / 1_000_000).toFixed(1)}M`
    : n >= 1_000
    ? `${(n / 1_000).toFixed(1)}K`
    : String(n);

const fmtCost = (n: number | null) =>
  n == null ? '—' : `€${n.toFixed(4)}`;

// ─── Custom Tooltip ───────────────────────────────────────────────────────────

const CustomTooltip: React.FC<{
  active?: boolean;
  payload?: any[];
  label?: string;
  metric: Metric;
}> = ({ active, payload, label, metric }) => {
  if (!active || !payload || !payload.length) return null;
  const [y, m, d] = (label ?? '').split('-');
  const dateLabel = `${d}/${m}/${y}`;

  return (
    <div className="bg-white border border-slate-100 shadow-lg rounded-xl px-4 py-3 min-w-[160px]">
      <p className="text-[11px] text-slate-400 font-medium mb-2">{dateLabel}</p>
      {payload.map((p: any) => (
        <div key={p.dataKey} className="flex items-center justify-between gap-4 mb-0.5">
          <div className="flex items-center gap-1.5">
            <span className="block w-2 h-2 rounded-full" style={{ background: p.color }} />
            <span className="text-[12px] text-slate-600">{p.name}</span>
          </div>
          <span className="text-[12px] font-semibold text-slate-800">
            {metric === 'tokens'
              ? fmtTokens(p.value ?? 0)
              : metric === 'cost'
              ? fmtCost(p.value)
              : `${p.value ?? 0} req`}
          </span>
        </div>
      ))}
    </div>
  );
};

// ─── Summary KPIs ─────────────────────────────────────────────────────────────

const KPI: React.FC<{ label: string; value: string; sub?: string; color: string }> = ({
  label, value, sub, color,
}) => (
  <div className="flex flex-col gap-0.5">
    <div className="flex items-center gap-1.5">
      <span className="block w-2 h-2 rounded-full" style={{ background: color }} />
      <span className="text-[11px] text-slate-400 uppercase tracking-wide font-medium">{label}</span>
    </div>
    <p className="text-lg font-semibold text-slate-800 pl-3.5">{value}</p>
    {sub && <p className="text-[11px] text-slate-400 pl-3.5">{sub}</p>}
  </div>
);

// ─── Main component ───────────────────────────────────────────────────────────

const DAYS_OPTIONS = [7, 14, 30, 90];

const VevaUsageChart: React.FC = () => {
  const [data, setData] = useState<DailyEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [days, setDays] = useState(30);
  const [metric, setMetric] = useState<Metric>('tokens');
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = async (d: number, silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    setError(null);
    try {
      const { data: resp } = await api.get<VeraDailyResponse>(`/vera/usage/daily/?days=${d}`);
      setData(resp.series);
    } catch {
      setError('Impossibile caricare i dati di consumo Vera.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => { fetchData(days); }, [days]);

  // Summary totals
  const totalOpenaiTokens    = data.reduce((s, r) => s + (r.openai_tokens ?? 0), 0);
  const totalAnthropicTokens = data.reduce((s, r) => s + (r.anthropic_tokens ?? 0), 0);
  const totalOpenaiCost      = data.reduce((s, r) => s + (r.openai_cost_eur ?? 0), 0);
  const totalAnthropicCost   = data.reduce((s, r) => s + (r.anthropic_cost_eur ?? 0), 0);
  const hasCost = data.some(r => r.openai_cost_eur != null || r.anthropic_cost_eur != null);

  // Map metric to dataKey
  const metricKeys: Record<Metric, { openai: string; anthropic: string }> = {
    tokens:   { openai: 'openai_tokens',   anthropic: 'anthropic_tokens' },
    cost:     { openai: 'openai_cost_eur', anthropic: 'anthropic_cost_eur' },
    requests: { openai: 'openai_requests', anthropic: 'anthropic_requests' },
  };
  const keys = metricKeys[metric];

  const yTickFmt = (v: number) =>
    metric === 'tokens'   ? fmtTokens(v) :
    metric === 'cost'     ? `€${v.toFixed(3)}` :
    String(v);

  const hasData = data.some(r => r.total_tokens > 0);

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
            <p className="text-[11px] text-slate-400">Token giornalieri per provider</p>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Metric toggle */}
          <div className="flex bg-slate-100 rounded-xl p-1 gap-0.5">
            {(['tokens', 'cost', 'requests'] as Metric[]).map((m) => (
              <button
                key={m}
                onClick={() => setMetric(m)}
                disabled={m === 'cost' && !hasCost}
                className={`px-3 py-1 rounded-lg text-[11px] font-medium transition-all duration-150 disabled:opacity-40 disabled:cursor-not-allowed ${
                  metric === m
                    ? 'bg-white shadow-sm text-[#1e3a8a]'
                    : 'text-slate-400 hover:text-slate-600'
                }`}
              >
                {m === 'tokens' ? 'Token' : m === 'cost' ? 'Costo (€)' : 'Richieste'}
              </button>
            ))}
          </div>

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

      {/* Summary KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pb-1 border-b border-slate-100">
        <KPI
          label="OpenAI token"
          value={fmtTokens(totalOpenaiTokens)}
          sub={`ultimi ${days} gg`}
          color="#1e3a8a"
        />
        <KPI
          label="Anthropic token"
          value={fmtTokens(totalAnthropicTokens)}
          sub={`ultimi ${days} gg`}
          color="#1b9162"
        />
        {hasCost && (
          <>
            <KPI
              label="OpenAI costo"
              value={`€${totalOpenaiCost.toFixed(4)}`}
              color="#1e3a8a"
            />
            <KPI
              label="Anthropic costo"
              value={`€${totalAnthropicCost.toFixed(4)}`}
              color="#1b9162"
            />
          </>
        )}
      </div>

      {/* Chart area */}
      <div className="h-64">
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
            <p className="text-[12px] text-slate-400 max-w-[260px] leading-relaxed">
              I dati appariranno qui non appena il backend inizierà a inviare le tracce di consumo via <code className="bg-slate-100 px-1 rounded text-[11px]">POST /api/vera/usage/</code>
            </p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 4, right: 4, left: -10, bottom: 0 }}>
              <defs>
                <linearGradient id="gradOpenai" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#1e3a8a" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#1e3a8a" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gradAnthropic" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#1b9162" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#1b9162" stopOpacity={0} />
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
                tickFormatter={yTickFmt}
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 10, fill: '#94A3B8', fontWeight: 500 }}
                width={48}
              />
              <Tooltip content={<CustomTooltip metric={metric} />} />
              <Legend
                formatter={(v) => (
                  <span className="text-[11px] text-slate-500 font-medium">{v}</span>
                )}
                wrapperStyle={{ paddingTop: 8 }}
              />
              <Area
                type="monotone"
                dataKey={keys.openai}
                name="OpenAI"
                stroke="#1e3a8a"
                strokeWidth={2}
                fill="url(#gradOpenai)"
                dot={false}
                activeDot={{ r: 4, strokeWidth: 0 }}
              />
              <Area
                type="monotone"
                dataKey={keys.anthropic}
                name="Anthropic"
                stroke="#1b9162"
                strokeWidth={2}
                fill="url(#gradAnthropic)"
                dot={false}
                activeDot={{ r: 4, strokeWidth: 0 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
};

export default VevaUsageChart;
