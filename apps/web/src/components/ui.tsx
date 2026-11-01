'use client';

import { STATUS_STYLES } from '@/lib/format';

/* ---------------- primitives (hand-rolled, ADR-0002) ---------------- */

export function Brand({ size = 'md' }: { size?: 'md' | 'lg' }) {
  const t = size === 'lg' ? 'text-3xl' : 'text-xl';
  return (
    <span className={`${t} font-black tracking-tight`}>
      <span className="text-ivory">CINE</span>
      <span className="bg-gradient-to-r from-forge to-accent bg-clip-text text-transparent">FORGE</span>
    </span>
  );
}

export function Spinner({ className = 'h-4 w-4' }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-90" d="M22 12a10 10 0 0 1-10 10" stroke="currentColor" strokeWidth="4" strokeLinecap="round" />
    </svg>
  );
}

export function StatusChip({ status }: { status: string }) {
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wide ${STATUS_STYLES[status] ?? 'bg-white/10 text-ivory/70'}`}>
      {status}
    </span>
  );
}

export function Chip({ children, title }: { children: React.ReactNode; title?: string }) {
  return (
    <span className="chip" title={title}>
      {children}
    </span>
  );
}

export function EmptyState({
  title,
  hint,
  icon,
}: {
  title: string;
  hint?: string;
  icon?: React.ReactNode;
}) {
  return (
    <div className="flex h-full min-h-[180px] flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-line p-8 text-center">
      {icon ?? <div className="text-2xl opacity-30">▢</div>}
      <p className="text-sm font-semibold text-ivory/80">{title}</p>
      {hint ? <p className="max-w-sm text-xs leading-relaxed text-muted">{hint}</p> : null}
    </div>
  );
}

export function ErrorNote({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-rose-500/25 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
      <span>{message}</span>
      {onRetry ? (
        <button className="btn-ghost !py-1 !px-2.5 text-xs" onClick={onRetry}>
          Retry
        </button>
      ) : null}
    </div>
  );
}

export function Modal({
  open,
  onClose,
  title,
  children,
  width = 'max-w-lg',
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  width?: string;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} aria-hidden />
      <div className={`panel relative w-full ${width} animate-rise p-6 shadow-glow`} role="dialog" aria-modal>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-bold">{title}</h2>
          <button onClick={onClose} className="rounded-md p-1 text-muted hover:bg-white/10 hover:text-ivory" aria-label="Close">
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function Tabs<T extends string>({
  tabs,
  active,
  onChange,
}: {
  tabs: Array<{ id: T; label: string; badge?: number }>;
  active: T;
  onChange: (id: T) => void;
}) {
  return (
    <div className="flex gap-1 rounded-lg border border-line bg-ink/50 p-1">
      {tabs.map((t) => (
        <button
          key={t.id}
          onClick={() => onChange(t.id)}
          className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold transition ${
            active === t.id ? 'bg-forge/20 text-ivory shadow-glow' : 'text-muted hover:bg-white/5 hover:text-ivory/80'
          }`}
        >
          {t.label}
          {t.badge ? (
            <span className="rounded-full bg-white/10 px-1.5 text-[10px] text-ivory/80">{t.badge}</span>
          ) : null}
        </button>
      ))}
    </div>
  );
}

export function ProgressBar({ value, className = '' }: { value: number; className?: string }) {
  const pct = Math.round(Math.min(1, Math.max(0, value)) * 100);
  return (
    <div className={`h-1.5 w-full overflow-hidden rounded-full bg-white/10 ${className}`}>
      <div
        className="h-full rounded-full bg-gradient-to-r from-forge to-accent transition-all"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

export function KindIcon({ kind }: { kind: string }) {
  const common = 'h-4 w-4 shrink-0';
  switch (kind) {
    case 'video':
      return (
        <svg className={common} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden>
          <rect x="2" y="6" width="14" height="12" rx="2" />
          <path d="M16 10.5 22 7v10l-6-3.5" />
        </svg>
      );
    case 'frame':
      return (
        <svg className={common} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden>
          <rect x="3" y="4" width="18" height="16" rx="2" />
          <circle cx="9" cy="10" r="1.6" />
          <path d="m4 19 6-6 4 4 3-3 3 3" />
        </svg>
      );
    case 'audio':
      return (
        <svg className={common} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden>
          <path d="M4 12v3M8 8v10M12 5v14M16 9v7M20 11v3" strokeLinecap="round" />
        </svg>
      );
    case 'storyboard':
      return (
        <svg className={common} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden>
          <rect x="3" y="4" width="7" height="6" rx="1" />
          <rect x="14" y="4" width="7" height="6" rx="1" />
          <rect x="3" y="14" width="7" height="6" rx="1" />
          <rect x="14" y="14" width="7" height="6" rx="1" />
        </svg>
      );
    case 'project':
      return (
        <svg className={common} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden>
          <path d="M4 6a2 2 0 0 1 2-2h4l2 2h6a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6Z" />
        </svg>
      );
    default:
      return (
        <svg className={common} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden>
          <rect x="4" y="4" width="16" height="16" rx="2" />
        </svg>
      );
  }
}
