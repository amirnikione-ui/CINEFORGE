/** Small display helpers shared by studio components. */

export function relTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return iso;
  const s = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export function secs(n: number | undefined): string {
  if (n === undefined || n === null || Number.isNaN(n)) return '—';
  return `${n.toFixed(1)}s`;
}

export function dims(a: { width?: number; height?: number } | undefined): string {
  if (!a?.width || !a?.height) return '—';
  return `${a.width}×${a.height}`;
}

export function truncate(s: string, n = 140): string {
  return s.length > n ? `${s.slice(0, n - 1)}…` : s;
}

export const SCENE_KIND_COLORS: Record<string, { bar: string; dot: string; label: string }> = {
  hook: { bar: 'bg-forge/70', dot: 'bg-forge', label: 'Hook' },
  reveal: { bar: 'bg-accent/60', dot: 'bg-accent', label: 'Reveal' },
  typography: { bar: 'bg-amber-400/60', dot: 'bg-amber-400', label: 'Typography' },
  outro: { bar: 'bg-slate-400/50', dot: 'bg-slate-300', label: 'Outro' },
};

export const STATUS_STYLES: Record<string, string> = {
  draft: 'bg-white/10 text-ivory/80',
  generating: 'bg-forge/20 text-forge animate-breathe',
  ready: 'bg-emerald-500/15 text-emerald-300',
  failed: 'bg-rose-500/15 text-rose-300',
  pending: 'bg-white/10 text-ivory/70',
  running: 'bg-forge/20 text-forge animate-breathe',
  done: 'bg-emerald-500/15 text-emerald-300',
};
