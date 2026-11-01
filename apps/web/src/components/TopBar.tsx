import Link from "next/link";
import ProviderChips from "@/components/ProviderChips";
import type { Health, Project, ProjectStatus } from "@/types/api";

function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

const STATUS_STYLES: Record<ProjectStatus, string> = {
  draft: "border-zinc-600/50 bg-zinc-500/10 text-zinc-400",
  generating: "border-accent-violet/40 bg-accent-violet/10 text-accent-violet",
  ready: "border-emerald-500/40 bg-emerald-500/10 text-emerald-400",
  failed: "border-red-500/40 bg-red-500/10 text-red-400",
};

/** Colored status pill (draft / generating / ready / failed). */
export function StatusPill({ status }: { status: ProjectStatus }) {
  return (
    <span
      className={cx(
        "inline-flex shrink-0 items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider",
        STATUS_STYLES[status],
      )}
    >
      {status === "generating" && <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent-violet" />}
      {status}
    </span>
  );
}

interface TopBarProps {
  variant: "dashboard" | "studio";
  health: Health | null;
  /** null = still checking, true = online, false = offline (amber chip) */
  apiOnline: boolean | null;
  project?: Project | null;
}

export default function TopBar({ variant, health, apiOnline, project = null }: TopBarProps) {
  return (
    <header className="grain relative z-20 shrink-0 border-b border-ink-line bg-ink-panel/90 backdrop-blur">
      <div className="mx-auto flex h-14 w-full max-w-7xl items-center gap-3 px-4">
        {variant === "studio" && (
          <>
            <Link
              href="/"
              className="shrink-0 rounded-md px-1 py-0.5 text-sm text-zinc-400 transition hover:text-white"
              title="Back to projects"
            >
              ← Projects
            </Link>
            <span className="h-5 w-px shrink-0 bg-ink-line" />
          </>
        )}

        <Link href="/" className="flex shrink-0 items-baseline gap-1.5" title="CINEFORGE home">
          <span className="text-lg leading-none">🎬</span>
          <span
            className={cx(
              "gradient-text font-semibold tracking-tight",
              variant === "studio" ? "text-base" : "text-lg",
            )}
          >
            CINEFORGE
          </span>
        </Link>

        {variant === "dashboard" && <span className="hidden text-xs text-zinc-500 sm:block">AI Video Studio</span>}

        {variant === "studio" && (
          <div className="ml-1 flex min-w-0 items-center gap-2">
            <span className="truncate text-sm font-medium text-zinc-100">{project ? project.title : "…"}</span>
            {project && <StatusPill status={project.status} />}
          </div>
        )}

        <div className="ml-auto hidden min-w-0 justify-end md:flex">
          <ProviderChips health={health} online={apiOnline} />
        </div>
      </div>
    </header>
  );
}
