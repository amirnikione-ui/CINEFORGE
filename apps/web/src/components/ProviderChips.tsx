import type { Health } from "@/types/api";

interface ProviderChipsProps {
  health: Health | null;
  /** null = still checking, true = online, false = offline */
  online: boolean | null;
}

/**
 * One chip per capability from `GET /health`, showing the first (preferred) provider,
 * e.g. `llm: mock`. When the API is unreachable a single amber chip is shown instead.
 */
export default function ProviderChips({ health, online }: ProviderChipsProps) {
  if (online === false) {
    return (
      <span className="chip border-amber-500/40 bg-amber-500/10 text-amber-300" title="Backend API unreachable">
        <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
        API OFFLINE
      </span>
    );
  }

  if (online === null || !health) {
    return (
      <span className="chip border-ink-line bg-ink-raised text-zinc-500" title="Checking API health…">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-zinc-500" />
        API…
      </span>
    );
  }

  return (
    <div className="flex flex-wrap items-center justify-end gap-1.5">
      {Object.entries(health.providers).map(([capability, providers]) => (
        <span
          key={capability}
          className="chip border-emerald-500/25 bg-emerald-500/[0.07] font-mono text-emerald-300/90"
          title={`${capability} providers: ${providers.join(", ")}`}
        >
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
          {capability}: {providers[0] ?? "—"}
        </span>
      ))}
    </div>
  );
}
