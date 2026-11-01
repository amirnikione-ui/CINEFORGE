"use client";

import { assetUrl } from "@/lib/api";
import type { Asset, AssetKind, Job, JobStatus } from "@/types/api";

function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

const KIND_ORDER: AssetKind[] = ["storyboard", "frame", "audio", "video", "project", "analysis"];

const KIND_META: Record<AssetKind, { icon: string; label: string }> = {
  storyboard: { icon: "🎬", label: "Storyboards" },
  frame: { icon: "🖼️", label: "Frames" },
  audio: { icon: "🔊", label: "Audio" },
  video: { icon: "🎞️", label: "Video" },
  project: { icon: "📦", label: "Projects" },
  analysis: { icon: "🔍", label: "Analysis" },
};

const JOB_STATUS_STYLES: Record<JobStatus, { text: string; bar: string }> = {
  pending: { text: "text-zinc-500", bar: "bg-zinc-500" },
  running: { text: "text-accent-cyan", bar: "bg-gradient-to-r from-accent-violet to-accent-cyan" },
  done: { text: "text-emerald-400", bar: "bg-emerald-500" },
  failed: { text: "text-red-400", bar: "bg-red-500" },
};

const JOB_STATUS_ORDER: Record<JobStatus, number> = { running: 0, pending: 1, failed: 2, done: 3 };

interface AssetsPanelProps {
  assets: Asset[];
  jobs: Job[];
  className?: string;
}

/** Right-hand column: live job progress on top, media library grouped by kind below. */
export default function AssetsPanel({ assets, jobs, className }: AssetsPanelProps) {
  const sortedJobs = [...jobs].sort((a, b) => JOB_STATUS_ORDER[a.status] - JOB_STATUS_ORDER[b.status]);

  const groups = KIND_ORDER.map((kind) => ({
    kind,
    items: assets
      .filter((a) => a.kind === kind)
      .sort((a, b) => (b.created_at ?? "").localeCompare(a.created_at ?? "")),
  })).filter((g) => g.items.length > 0);

  return (
    <aside className={cx("flex min-h-0 flex-col", className)} aria-label="Media library">
      <header className="flex h-9 shrink-0 items-center justify-between border-b border-ink-line px-3">
        <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">Media</span>
        <span className="font-mono text-[10px] text-zinc-600">
          {assets.length} asset{assets.length === 1 ? "" : "s"} · {jobs.length} job{jobs.length === 1 ? "" : "s"}
        </span>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {/* Jobs */}
        <section className="border-b border-ink-line p-3">
          <h2 className="mb-2 font-mono text-[9px] uppercase tracking-widest text-zinc-600">Jobs</h2>
          {jobs.length === 0 ? (
            <p className="text-[11px] text-zinc-600">No background jobs.</p>
          ) : (
            sortedJobs.map((job) => {
              const style = JOB_STATUS_STYLES[job.status];
              const pct = Math.round(Math.min(Math.max(job.progress, 0), 1) * 100);
              return (
                <div key={job.id} className="mb-2.5 last:mb-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-[10px] uppercase tracking-wider text-zinc-400">{job.kind}</span>
                    <span className={cx("font-mono text-[10px]", style.text)}>
                      {job.status}
                      {job.status === "running" || job.status === "pending" ? ` ${pct}%` : ""}
                    </span>
                  </div>
                  <div className="mt-1 h-1 overflow-hidden rounded-full bg-ink-line">
                    <div
                      className={cx("h-full rounded-full transition-all duration-500", style.bar)}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  {job.error && <p className="mt-1 break-words text-[10px] leading-snug text-red-400">{job.error}</p>}
                </div>
              );
            })
          )}
        </section>

        {/* Assets grouped by kind */}
        <div className="p-3">
          {groups.length === 0 ? (
            <p className="text-[11px] leading-relaxed text-zinc-600">
              No assets yet — they appear here as the director works.
            </p>
          ) : (
            groups.map(({ kind, items }) => (
              <section key={kind} className="mb-4 last:mb-0">
                <h2 className="mb-1.5 flex items-center gap-1.5 font-mono text-[9px] uppercase tracking-widest text-zinc-600">
                  <span className="text-xs">{KIND_META[kind].icon}</span>
                  {KIND_META[kind].label}
                  <span className="rounded bg-ink-raised px-1.5 py-px text-[9px] text-zinc-500">{items.length}</span>
                </h2>
                <ul className="space-y-1">
                  {items.map((a) => (
                    <AssetRow key={a.id} asset={a} />
                  ))}
                </ul>
              </section>
            ))
          )}
        </div>
      </div>
    </aside>
  );
}

function AssetRow({ asset: a }: { asset: Asset }) {
  const meta = a.meta ?? {};
  const isFile = a.kind !== "project";
  return (
    <li className="group flex items-start gap-2 rounded-lg border border-transparent px-2 py-1.5 transition hover:border-ink-line hover:bg-ink-raised/60">
      <span className="pt-px text-sm leading-5">{KIND_META[a.kind].icon}</span>
      <div className="min-w-0 flex-1">
        <div className="truncate font-mono text-[11px] text-zinc-300" title={a.filename}>
          {a.filename || a.id}
        </div>
        <div className="mt-0.5 flex flex-wrap gap-1">
          {typeof meta.provider === "string" && (
            <span className="chip border-accent-violet/30 bg-accent-violet/10 text-accent-violet/90">{meta.provider}</span>
          )}
          {typeof meta.duration_s === "number" && (
            <span className="chip border-ink-line bg-ink-raised font-mono text-zinc-500">
              {meta.duration_s.toFixed(1)}s
            </span>
          )}
          {typeof meta.width === "number" && typeof meta.height === "number" && (
            <span className="chip border-ink-line bg-ink-raised font-mono text-zinc-500">
              {meta.width}×{meta.height}
            </span>
          )}
        </div>
        {a.kind === "project" && (
          <p className="mt-1 text-[10px] italic leading-snug text-zinc-600">editable Remotion project (on server)</p>
        )}
      </div>
      {isFile && (
        <a
          href={assetUrl(a.id)}
          target="_blank"
          rel="noreferrer"
          className="shrink-0 rounded border border-ink-line px-1.5 py-0.5 font-mono text-[10px] text-zinc-500 transition hover:border-accent-cyan/50 hover:text-accent-cyan"
          title="Open file in a new tab"
        >
          ↗
        </a>
      )}
    </li>
  );
}
