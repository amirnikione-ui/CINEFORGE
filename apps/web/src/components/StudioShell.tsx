'use client';

// CINEFORGE studio shell: chat (director) + preview + timeline + media + jobs.
import { useMemo, useState } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { useProject } from '@/lib/useProject';
import ChatPanel from './ChatPanel';
import Timeline from './Timeline';
import PreviewPane from './PreviewPane';
import MediaPanel from './MediaPanel';
export default function StudioShell({ pid }: { pid: string }) {
  const { detail, error, refresh } = useProject(pid);
  const [tab, setTab] = useState<'media' | 'jobs'>('media');

  const latestVideo = useMemo(() => {
    if (!detail) return null;
    const renderJobs = detail.jobs.filter((j) => j.kind === 'render' && j.status === 'done'
      && j.result?.asset_id);
    if (renderJobs.length === 0) return null;
    const last = renderJobs[renderJobs.length - 1];
    return detail.assets.find((a) => a.id === last.result.asset_id) ?? null;
  }, [detail]);

  const runningJob = detail?.jobs.find((j) => j.status === 'running' || j.status === 'pending');

  if (error) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-20 text-center">
        <p className="text-red-400">API error: {error}</p>
        <p className="mt-2 text-sm text-slate-500">
          Is the backend running? <code className="text-slate-400">docker compose up</code>
        </p>
        <Link href="/" className="btn-ghost mt-6">← Back to projects</Link>
      </main>
    );
  }
  if (!detail) {
    return <main className="grid min-h-screen place-items-center text-slate-500">Loading studio…</main>;
  }

  const { project } = detail;

  return (
    <main className="flex h-screen flex-col overflow-hidden">
      {/* top bar */}
      <header className="flex items-center gap-4 border-b border-ink-700 bg-ink-900 px-5 py-3">
        <Link href="/" className="text-lg font-black text-white">
          CINE<span className="text-forge-400">FORGE</span>
        </Link>
        <div className="h-5 w-px bg-ink-600" />
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-sm font-bold text-white">{project.title}</h1>
          <p className="truncate text-[11px] text-slate-500">{project.brief}</p>
        </div>
        <span className="pill">{project.platform}</span>
        <span className="pill">{project.style}</span>
        {runningJob && (
          <span className="pill border-amber-500/40 text-amber-400">
            render {Math.round((runningJob.progress ?? 0) * 100)}%
          </span>
        )}
        <span className={`pill ${project.status === 'ready' ? 'border-emerald-500/40 text-emerald-400'
          : project.status === 'failed' ? 'border-red-500/40 text-red-400' : ''}`}>
          {project.status}
        </span>
      </header>

      {/* main grid */}
      <div className="grid min-h-0 flex-1 grid-cols-[380px_1fr]">
        <ChatPanel pid={pid} detail={detail} onRefresh={refresh} />

        <section className="flex min-h-0 flex-col gap-3 overflow-hidden p-4">
          <PreviewPane assetId={latestVideo?.id ?? null} job={runningJob ?? null} />
          <Timeline detail={detail} />
          <div className="flex items-center gap-2">
            {(['media', 'jobs'] as const).map((t) => (
              <button key={t} onClick={() => setTab(t)}
                      className={`pill ${tab === t ? 'border-forge-500 text-forge-300' : ''}`}>
                {t}
              </button>
            ))}
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto">
            {tab === 'media'
              ? <MediaPanel detail={detail} />
              : <JobsPanel detail={detail} />}
          </div>
        </section>
      </div>
    </main>
  );
}

function JobsPanel({ detail }: { detail: NonNullable<ReturnType<typeof useProject>['detail']> }) {
  return (
    <div className="space-y-2">
      {detail.jobs.length === 0 && <p className="p-4 text-xs text-slate-500">No jobs yet.</p>}
      {detail.jobs.map((j) => (
        <div key={j.id} className="panel p-3">
          <div className="flex items-center justify-between text-xs">
            <span className="font-mono text-slate-400">{j.kind} · {j.id.slice(0, 8)}</span>
            <span className={`pill ${j.status === 'done' ? 'border-emerald-500/40 text-emerald-400'
              : j.status === 'failed' ? 'border-red-500/40 text-red-400' : 'border-amber-500/40 text-amber-400'}`}>
              {j.status}
            </span>
          </div>
          <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-ink-700">
            <div className="h-full rounded-full bg-forge-500 transition-all"
                 style={{ width: `${Math.round((j.progress ?? 0) * 100)}%` }} />
          </div>
          {j.error && <p className="mt-2 text-[11px] text-red-400">{j.error}</p>}
        </div>
      ))}
    </div>
  );
}
