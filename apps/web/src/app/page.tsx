'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { api } from '@/lib/api';
import type { Health, Project } from '@/types/api';

const PLATFORMS = ['instagram', 'youtube', 'tiktok', 'web'] as const;

export default function Dashboard() {
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  const [title, setTitle] = useState('');
  const [brief, setBrief] = useState('');
  const [platform, setPlatform] = useState<string>('instagram');
  const [duration, setDuration] = useState(30);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    void api.listProjects().then(setProjects).catch(() => setProjects([]));
    void api.health().then(setHealth).catch(() => setHealth(null));
  }, []);

  const create = async () => {
    if (!title.trim() || !brief.trim() || busy) return;
    setBusy(true);
    setErr(null);
    try {
      const p = await api.createProject({ title, brief, platform, duration_hint_s: duration });
      router.push(`/studio/${p.id}`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
      setBusy(false);
    }
  };

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <header className="mb-10 flex items-end justify-between">
        <div>
          <h1 className="text-3xl font-black tracking-tight text-white">
            CINE<span className="text-forge-400">FORGE</span>
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Chat with a director-agent — script, motion, edit, final cut.
          </p>
        </div>
        <div className="text-right text-xs text-slate-500">
          {health ? (
            <>
              <div className="pill border-emerald-500/30 text-emerald-400">API v{health.version}</div>
              <div className="mt-1">
                providers: {Object.entries(health.providers).map(([k, v]) => `${k}:${v.join('/')}`).join(' · ')}
              </div>
            </>
          ) : (
            <div className="pill border-red-500/40 text-red-400">API offline</div>
          )}
        </div>
      </header>

      <section className="panel mb-10 p-6">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">
          New production
        </h2>
        <div className="grid gap-4 md:grid-cols-[1fr_2fr_auto_auto_auto]">
          <input className="field" placeholder="Title — e.g. NOVA promo"
                 value={title} onChange={(e) => setTitle(e.target.value)} />
          <input className="field" placeholder="Brief — “30s cinematic teaser, dark mood, English narration…”"
                 value={brief} onChange={(e) => setBrief(e.target.value)} />
          <select className="field" value={platform} onChange={(e) => setPlatform(e.target.value)}>
            {PLATFORMS.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
          <input className="field w-24" type="number" min={5} max={180} value={duration}
                 onChange={(e) => setDuration(Number(e.target.value))} />
          <button className="btn-forge" onClick={create} disabled={busy || !title || !brief}>
            {busy ? 'Creating…' : '🎬 Start'}
          </button>
        </div>
        {err && <p className="mt-3 text-sm text-red-400">{err}</p>}
      </section>

      <section>
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">Projects</h2>
        {projects.length === 0 ? (
          <div className="panel p-10 text-center text-sm text-slate-500">
            No projects yet — brief the director above.
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {projects.map((p) => (
              <Link key={p.id} href={`/studio/${p.id}`}
                    className="panel group p-5 transition hover:border-forge-500/50 hover:shadow-glow">
                <div className="flex items-center justify-between">
                  <span className="pill">{p.platform}</span>
                  <StatusDot status={p.status} />
                </div>
                <h3 className="mt-3 font-bold text-white group-hover:text-forge-300">{p.title}</h3>
                <p className="mt-1 line-clamp-2 text-xs text-slate-400">{p.brief}</p>
                <div className="mt-3 text-[11px] text-slate-500">
                  {p.duration_hint_s}s · {new Date(p.created_at).toLocaleDateString()}
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}

function StatusDot({ status }: { status: Project['status'] }) {
  const map: Record<Project['status'], string> = {
    draft: 'border-slate-500/40 text-slate-400',
    generating: 'border-amber-500/40 text-amber-400',
    ready: 'border-emerald-500/40 text-emerald-400',
    failed: 'border-red-500/40 text-red-400',
  };
  return <span className={`pill ${map[status]}`}>{status}</span>;
}
