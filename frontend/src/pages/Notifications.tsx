import React, { useCallback, useEffect, useState } from 'react';
import {
  Bell,
  CheckCheck,
  ShieldCheck,
  Newspaper,
  BarChart3,
  Wallet,
  ChevronRight,
  Inbox,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import {
  notificationService,
  Notification,
  NotificationType,
} from '../services/notificationService';

// ─── Config ───────────────────────────────────────────────────────────────────

type FilterKey = 'all' | 'unread' | 'compliance_log' | 'newsletter_auto' | 'consumption';

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: 'all', label: 'Tutte' },
  { key: 'unread', label: 'Non lette' },
  { key: 'compliance_log', label: 'Log Compliance' },
  { key: 'newsletter_auto', label: 'Newsletter' },
  { key: 'consumption', label: 'Consumo AI' },
];

const CONSUMPTION_TYPES: NotificationType[] = [
  'consumption_report',
  'consumption_low_balance',
  'consumption_threshold',
];

const typeIcon = (type: NotificationType) => {
  if (type === 'compliance_log') return <ShieldCheck size={16} className="text-blue-600" />;
  if (type === 'newsletter_auto') return <Newspaper size={16} className="text-green-600" />;
  if (type === 'consumption_low_balance') return <Wallet size={16} className="text-red-500" />;
  return <BarChart3 size={16} className="text-amber-500" />;
};

const typeBorderColor = (type: NotificationType) => {
  if (type === 'compliance_log') return 'border-l-blue-500';
  if (type === 'newsletter_auto') return 'border-l-green-500';
  if (type === 'consumption_low_balance') return 'border-l-red-500';
  return 'border-l-amber-500';
};

const typeNavTarget = (n: Notification): string => {
  if (n.notification_type === 'compliance_log') return '/compliance/logs';
  if (n.notification_type === 'newsletter_auto') return '/newsletter?tab=archive';
  return '/usage/utilizzo';
};

const formatDate = (iso: string) => {
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffH = diffMs / (1000 * 60 * 60);
  if (diffH < 1) return `${Math.max(1, Math.round(diffMs / 60000))} min fa`;
  if (diffH < 24) return `${Math.round(diffH)} ore fa`;
  if (diffH < 48) return 'Ieri';
  return d.toLocaleDateString('it-IT', { day: '2-digit', month: 'short', year: 'numeric' });
};

// ─── Main page ────────────────────────────────────────────────────────────────

const Notifications: React.FC = () => {
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [activeFilter, setActiveFilter] = useState<FilterKey>('all');
  const [loading, setLoading] = useState(true);
  const [markingAll, setMarkingAll] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await notificationService.list();
      setNotifications(res.results);
      setUnreadCount(res.unread_count);
    } catch (e) {
      console.error('Failed to load notifications', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleMarkRead = async (n: Notification) => {
    if (!n.is_read) {
      await notificationService.markRead(n.id);
      setNotifications((prev) =>
        prev.map((x) => (x.id === n.id ? { ...x, is_read: true } : x))
      );
      setUnreadCount((c) => Math.max(0, c - 1));
    }
    navigate(typeNavTarget(n));
  };

  const handleMarkAllRead = async () => {
    setMarkingAll(true);
    try {
      await notificationService.markAllRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } finally {
      setMarkingAll(false);
    }
  };

  const filtered = notifications.filter((n) => {
    if (activeFilter === 'all') return true;
    if (activeFilter === 'unread') return !n.is_read;
    if (activeFilter === 'consumption') return CONSUMPTION_TYPES.includes(n.notification_type);
    return n.notification_type === activeFilter;
  });

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-[#f8fafc]">
      {/* Header */}
      <div className="bg-white border-b border-slate-100 px-8 py-5 shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-[#1e3a8a]/8 flex items-center justify-center">
              <Bell size={17} className="text-[#1e3a8a]" />
            </div>
            <div>
              <h1 className="text-base font-semibold text-slate-800">Notifiche</h1>
              {unreadCount > 0 && (
                <p className="text-[11px] text-slate-400">
                  {unreadCount} non {unreadCount === 1 ? 'letta' : 'lette'}
                </p>
              )}
            </div>
          </div>
          {unreadCount > 0 && (
            <button
              onClick={handleMarkAllRead}
              disabled={markingAll}
              className="flex items-center gap-1.5 text-[12px] font-medium text-[#1e3a8a] hover:text-[#172554] transition-colors disabled:opacity-50"
            >
              <CheckCheck size={14} />
              Segna tutte come lette
            </button>
          )}
        </div>

        {/* Filters */}
        <div className="flex items-center gap-1 mt-4 overflow-x-auto [scrollbar-width:none]">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setActiveFilter(f.key)}
              className={`shrink-0 px-3.5 py-1.5 rounded-lg text-[12px] font-medium transition-all duration-150 ${
                activeFilter === f.key
                  ? 'bg-[#1e3a8a] text-white shadow-sm'
                  : 'bg-slate-100 text-slate-500 hover:bg-slate-200 hover:text-slate-700'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto px-8 py-6 [scrollbar-width:thin]">
        {loading ? (
          <div className="flex items-center justify-center h-48 text-slate-400 text-sm">
            Caricamento…
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 gap-3">
            <div className="w-14 h-14 rounded-2xl bg-slate-100 flex items-center justify-center">
              <Inbox size={24} className="text-slate-300" />
            </div>
            <p className="text-slate-500 text-sm font-medium">Nessuna notifica</p>
            <p className="text-slate-400 text-[12px]">
              {activeFilter === 'unread' ? 'Tutto letto — ottimo!' : 'Non ci sono notifiche in questa categoria.'}
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-2 max-w-3xl">
            {filtered.map((n) => (
              <button
                key={n.id}
                onClick={() => handleMarkRead(n)}
                className={`w-full text-left rounded-xl border transition-all duration-150 group
                  ${n.is_read
                    ? 'bg-white border-slate-100 hover:border-slate-200 hover:shadow-sm'
                    : `bg-white border-l-4 border-slate-100 ${typeBorderColor(n.notification_type)} shadow-sm hover:shadow-md`
                  }`}
              >
                <div className="px-5 py-4 flex items-start gap-4">
                  {/* Icon */}
                  <div className={`shrink-0 w-8 h-8 rounded-xl flex items-center justify-center mt-0.5
                    ${n.is_read ? 'bg-slate-50' : 'bg-white shadow-sm border border-slate-100'}`}>
                    {typeIcon(n.notification_type)}
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-3">
                      <p className={`text-sm leading-snug ${n.is_read ? 'text-slate-600 font-normal' : 'text-slate-800 font-semibold'}`}>
                        {n.title}
                      </p>
                      <span className="shrink-0 text-[11px] text-slate-400 mt-0.5 whitespace-nowrap">
                        {formatDate(n.created_at)}
                      </span>
                    </div>
                    {n.body && (
                      <p className="text-[12px] text-slate-500 mt-1 leading-relaxed line-clamp-2">
                        {n.body}
                      </p>
                    )}
                    <div className="flex items-center gap-2 mt-2">
                      <span className={`text-[10px] font-medium uppercase tracking-wide px-2 py-0.5 rounded-full
                        ${n.is_read ? 'bg-slate-100 text-slate-400' : 'bg-slate-100 text-slate-500'}`}>
                        {n.notification_type_display}
                      </span>
                      {!n.is_read && (
                        <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#1e3a8a]" />
                      )}
                    </div>
                  </div>

                  {/* Chevron */}
                  <ChevronRight size={15} className="shrink-0 text-slate-300 group-hover:text-slate-400 mt-1 transition-colors" />
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Notifications;
