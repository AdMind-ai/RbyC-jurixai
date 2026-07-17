import React, { useEffect, useState } from 'react';
import { api } from '../api/api';
import {
  RefreshCw,
  ExternalLink,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Building2,
  Calendar,
  Tag,
  FileText,
  Link2,
} from 'lucide-react';

// ─── Types ────────────────────────────────────────────────────────────────────

interface ComplianceLogEntry {
  id: string;
  tipo_evento: string;
  normativa: string;
  autorita: string;
  data_rilevazione: string | null;
  versione_precedente: { riferimento?: string; [k: string]: unknown };
  versione_nuova: { riferimento?: string; fonte_url?: string; [k: string]: unknown };
  riassunto_modifica: string;
  tag: string;
  created_at: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const fmtDate = (iso: string | null) => {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('it-IT', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const tipoLabel: Record<string, { label: string; color: string }> = {
  aggiornamento_normativa: { label: 'Aggiornamento', color: 'bg-blue-50 text-blue-700' },
  nuova_normativa:         { label: 'Nuova normativa', color: 'bg-green-50 text-green-700' },
  abrogazione:             { label: 'Abrogazione', color: 'bg-red-50 text-red-600' },
  modifica:                { label: 'Modifica', color: 'bg-amber-50 text-amber-700' },
};

const TipoBadge: React.FC<{ tipo: string }> = ({ tipo }) => {
  const meta = tipoLabel[tipo] ?? { label: tipo, color: 'bg-slate-100 text-slate-600' };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium ${meta.color}`}>
      {meta.label}
    </span>
  );
};

// ─── Row detail expand ────────────────────────────────────────────────────────

const LogRow: React.FC<{ entry: ComplianceLogEntry }> = ({ entry }) => {
  const [open, setOpen] = useState(false);

  return (
    <div className="border border-slate-100 rounded-2xl overflow-hidden bg-white transition-shadow hover:shadow-sm">
      {/* Summary row */}
      <button
        className="w-full text-left px-5 py-4 flex items-start gap-4 group"
        onClick={() => setOpen((v) => !v)}
      >
        {/* Date column */}
        <div className="shrink-0 w-32 flex flex-col items-start gap-0.5 pt-0.5">
          <span className="text-[11px] text-slate-400">Rilevato</span>
          <span className="text-[12px] font-medium text-slate-700 leading-tight">
            {fmtDate(entry.data_rilevazione)}
          </span>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <TipoBadge tipo={entry.tipo_evento} />
            {entry.autorita && (
              <span className="flex items-center gap-1 text-[11px] text-slate-500">
                <Building2 size={11} />
                {entry.autorita}
              </span>
            )}
            <span className="flex items-center gap-1 text-[11px] text-slate-400">
              <Tag size={10} />
              {entry.tag}
            </span>
          </div>
          <p className="text-[13px] font-medium text-slate-800 leading-snug truncate">
            {entry.normativa}
          </p>
          {entry.riassunto_modifica && (
            <p className="text-[12px] text-slate-500 mt-0.5 line-clamp-1">
              {entry.riassunto_modifica}
            </p>
          )}
        </div>

        {/* Chevron */}
        <div className="shrink-0 pt-1 text-slate-400 group-hover:text-slate-600 transition-colors">
          {open ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
        </div>
      </button>

      {/* Expanded detail */}
      {open && (
        <div className="px-5 pb-5 pt-0 border-t border-slate-50 bg-slate-50/50">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4">

            {/* Normativa completa */}
            <div className="md:col-span-2">
              <p className="text-[11px] text-slate-400 uppercase tracking-wide font-medium mb-1 flex items-center gap-1.5">
                <FileText size={11} /> Normativa
              </p>
              <p className="text-[13px] text-slate-700">{entry.normativa}</p>
            </div>

            {/* Riassunto */}
            {entry.riassunto_modifica && (
              <div className="md:col-span-2">
                <p className="text-[11px] text-slate-400 uppercase tracking-wide font-medium mb-1">
                  Riassunto modifica
                </p>
                <p className="text-[13px] text-slate-700 leading-relaxed">
                  {entry.riassunto_modifica}
                </p>
              </div>
            )}

            {/* Versione precedente */}
            {entry.versione_precedente?.riferimento && (
              <div>
                <p className="text-[11px] text-slate-400 uppercase tracking-wide font-medium mb-1.5">
                  Versione precedente
                </p>
                <div className="bg-white rounded-xl border border-slate-200 px-3.5 py-3">
                  <p className="text-[12px] text-slate-500 font-mono break-all leading-relaxed">
                    {entry.versione_precedente.riferimento}
                  </p>
                </div>
              </div>
            )}

            {/* Versione nuova */}
            {(entry.versione_nuova?.riferimento || entry.versione_nuova?.fonte_url) && (
              <div>
                <p className="text-[11px] text-slate-400 uppercase tracking-wide font-medium mb-1.5">
                  Versione aggiornata
                </p>
                <div className="bg-white rounded-xl border border-[#1b9162]/20 px-3.5 py-3 space-y-1.5">
                  {entry.versione_nuova.riferimento && (
                    <p className="text-[12px] text-slate-500 font-mono break-all leading-relaxed">
                      {entry.versione_nuova.riferimento}
                    </p>
                  )}
                  {entry.versione_nuova.fonte_url && (
                    <a
                      href={entry.versione_nuova.fonte_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 text-[12px] text-[#1b9162] hover:underline font-medium"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <Link2 size={11} />
                      Fonte ufficiale
                      <ExternalLink size={10} />
                    </a>
                  )}
                </div>
              </div>
            )}

            {/* Meta */}
            <div className="md:col-span-2 flex flex-wrap gap-4 pt-1 border-t border-slate-100">
              <span className="flex items-center gap-1.5 text-[11px] text-slate-400">
                <Calendar size={11} />
                Ricevuto il {fmtDate(entry.created_at)}
              </span>
              <span className="text-[11px] text-slate-300 font-mono">{entry.id}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// ─── Empty state ──────────────────────────────────────────────────────────────

const EmptyState: React.FC = () => (
  <div className="flex flex-col items-center justify-center py-24 gap-4 text-center">
    <div className="w-14 h-14 rounded-2xl bg-slate-100 flex items-center justify-center">
      <FileText size={26} className="text-slate-300" />
    </div>
    <div>
      <p className="text-slate-600 font-medium">Nessun log disponibile</p>
      <p className="text-slate-400 text-[13px] mt-1 max-w-[280px] leading-relaxed">
        Agente Vera invierà qui i log degli aggiornamenti normativi rilevati automaticamente.
      </p>
    </div>
  </div>
);

// ─── Main page ────────────────────────────────────────────────────────────────

const CheckComplianceLogs: React.FC = () => {
  const [logs, setLogs] = useState<ComplianceLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [filter, setFilter] = useState('');

  const fetchLogs = async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    setError(null);
    try {
      const { data } = await api.get<ComplianceLogEntry[]>('/check-compliance/logs/');
      setLogs(data);
    } catch (e: any) {
      setError('Impossibile caricare i log. Riprova.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => { fetchLogs(); }, []);

  const filtered = logs.filter((l) => {
    if (!filter) return true;
    const q = filter.toLowerCase();
    return (
      l.normativa.toLowerCase().includes(q) ||
      l.autorita.toLowerCase().includes(q) ||
      l.riassunto_modifica.toLowerCase().includes(q) ||
      l.tipo_evento.toLowerCase().includes(q)
    );
  });

  return (
    <div className="page-root">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Log aggiornamenti normativi</h1>
          <p className="text-[13px] text-slate-500 mt-0.5">
            Tracciamento automatico degli aggiornamenti rilevati da Agente Vera
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Search */}
          <input
            type="text"
            placeholder="Filtra per normativa, autorità…"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="apple-input w-60 text-sm py-2"
          />
          {/* Refresh */}
          <button
            onClick={() => fetchLogs(true)}
            disabled={refreshing}
            className="btn-secondary py-2 px-3.5 gap-1.5 text-sm"
          >
            <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
            Aggiorna
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="page-body">
        {loading ? (
          <div className="flex items-center justify-center py-24 gap-3 text-slate-400">
            <RefreshCw size={18} className="animate-spin" />
            <span className="text-[14px]">Caricamento log…</span>
          </div>
        ) : error ? (
          <div className="flex items-center gap-3 bg-red-50 border border-red-100 rounded-2xl px-5 py-4 text-red-600">
            <AlertCircle size={16} />
            <span className="text-[13px]">{error}</span>
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="flex flex-col gap-3">
            {/* Count */}
            <div className="flex items-center justify-between">
              <p className="text-[12px] text-slate-400">
                {filtered.length} {filtered.length === 1 ? 'voce' : 'voci'}
                {filter && ` · filtrando "${filter}"`}
              </p>
            </div>
            {/* Rows */}
            {filtered.map((entry) => (
              <LogRow key={entry.id} entry={entry} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default CheckComplianceLogs;
