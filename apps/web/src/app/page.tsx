'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { getHealth, listProjects, ApiError } from '@/lib/api';
import type { Health, Project, ProviderCapability } from '@/types/api';
import { Brand, Chip, EmptyState, ErrorNote, Spinner } from '@/components/ui';
import { ProjectCard } from '@/components/project-card';
import { NewProjectDialog } from '@/components/new-project-dialog';

type Filter = 'all' | 'draft' | 'generating' | 'ready' | 'failed';

const FILTERS: Array<{ id: Filter; label: string }> = [
  { id: 'all', label: 'All' },
  { id: 'draft', label: 'Draft' },
  { id: 'generating', label: 'Generating' },
  { id: 'ready', label: 'Ready' },
  { id: 'failed', label: 'Failed' },
];

const CAPABILITIES: ProviderCapability[] = ['llm', 'image', 'tts', 'stt', 'music', 'video'];

export default function DashboardPage() {
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<Filter>('all');
  const [dialogOpen, setDialogOpen] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [p, h] = await Promise.all([
        listProjects(),
        getHealth().catch(() => null), // projects list matters most; health is decorative
      ]);
      setProjects(p);
      setHealth(h);
    } catch (err) {
      if (err instanceof ApiError && err.status === 0) {
        setError(err.message);
      } else {
        setError(err instanceof Error ? err.message : 'Failed to load projects');
      }
      setProjects([]);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const filtered = useMemo(() => {
    if (!projects) return [];
    return filter === 'all' ? projects : projects.filter((p) => p.status === filter);
  }, [projects, filter]);

  const activeProvider = (cap: ProviderCapability): string | null =>
    health?.providers?.[cap]?.[0] ?? null;

  const providersOnline = CAPABILITIES.filter((c) => activeProvider(c) !== null).length;

  return (
    <main className="mx-auto min-h-screen w-full max-w-6xl px-6 py-8">
      {/* Header */}
      <header className="mb-10 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <Brand size="lg" />
          <span className="chip font-mono">v{health?.version ?? '0.1'}</span>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={`chip ${health ? '!border-emerald-400/30 !text-emerald-300' : '!border-rose-400/30 !text-rose-300'}`}
            title={health ? `storage: ${health.storage_root}` : 'backend offline'}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${health ? 'bg-emerald-400' : 'bg-rose-400 animate-breathe'}`} />
            {health ? `${providersOnline}/6 providers` : 'backend offline'}
          </span>
          <button className="btn-primary" onClick={() => setDialogOpen(true)}>
            + New production
          </button>
        </div>
      </header>

      {/* Hero */}
      <section className="mb-8">
        <h1 className="max-w-2xl text-2xl font-black leading-tight text-ivory/95 md:text-3xl">
          The AI-native video studio.{' '}
          <span className="bg-gradient-to-r from-forge to-accent bg-clip-text text-transparent">
            From prompt to premiere.
          </span>
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">
          Brief the director agent in plain language. It plans, storyboards, generates, edits with
          code and renders — you watch it work in the studio.
        </p>
      </section>

      {/* Error */}
      {error ? (
        <div className="mb-6">
          <ErrorNote message={error} onRetry={load} />
        </div>
      ) : null}

      {/* Stats + filters */}
      <section className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-1.5">
          {FILTERS.map((f) => {
            const count =
              f.id === 'all' ? projects?.length ?? 0 : projects?.filter((p) => p.status === f.id).length ?? 0;
            return (
              <button
                key={f.id}
                onClick={() => setFilter(f.id)}
                className={`rounded-full border px-3 py-1 text-xs font-semibold transition ${
                  filter === f.id
                    ? 'border-forge/50 bg-forge/15 text-ivory'
                    : 'border-line bg-white/5 text-muted hover:text-ivory/80'
                }`}
              >
                {f.label}
                <span className="ml-1.5 text-[10px] opacity-60">{count}</span>
              </button>
            );
          })}
        </div>
        {health ? (
          <div className="flex flex-wrap items-center gap-1.5">
            {CAPABILITIES.map((c) => {
              const p = activeProvider(c);
              return (
                <Chip key={c} title={p ? `${c}: active provider = ${p}` : `${c}: no provider available`}>
                  <span className={`h-1.5 w-1.5 rounded-full ${p ? 'bg-emerald-400' : 'bg-white/20'}`} />
                  {c}
                  {p ? <span className="font-mono text-[10px] text-accent">{p}</span> : null}
                </Chip>
              );
            })}
          </div>
        ) : null}
      </section>

      {/* Grid */}
      <section>
        {projects === null ? (
          <div className="flex h-48 items-center justify-center text-muted">
            <Spinner className="h-6 w-6" />
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState
            title={filter === 'all' ? 'No productions yet' : `No ${filter} productions`}
            hint="Create your first production and brief the director agent — it will handle scripting, storyboard, media, motion and the final cut."
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {filtered.map((p) => (
              <ProjectCard key={p.id} project={p} />
            ))}
          </div>
        )}
      </section>

      <NewProjectDialog open={dialogOpen} onClose={() => setDialogOpen(false)} />
    </main>
  );
}
