'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { API_URL, deleteProject, getHealth, getProject, isJobActive } from '@/lib/api';
import type { Health, ProjectDetail } from '@/types/api';
import { Brand, ErrorNote, Spinner, StatusChip, Tabs } from '@/components/ui';
import { ChatPanel } from '@/components/chat-panel';
import { PreviewPane } from '@/components/preview-pane';
import { TimelineView } from '@/components/timeline-view';
import { MediaPanel } from '@/components/media-panel';
import { ProviderStatus } from '@/components/provider-status';
import { relTime } from '@/lib/format';

type Tab = 'preview' | 'timeline' | 'media' | 'providers';

export default function StudioPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const pid = params.id;

  const [detail, setDetail] = useState<ProjectDetail | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>('preview');
  const [confirmDelete, setConfirmDelete] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(async () => {
    try {
      const d = await getProject(pid);
      setDetail(d);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load project');
    }
  }, [pid]);

  // initial load + health
  useEffect(() => {
    refresh();
    getHealth().then(setHealth).catch(() => setHealth(null));
  }, [refresh, pid]);

  // Poll while the backend is busy on this project (ADR-0008: UI polls jobs).
  const busy = useMemo(
    () => (detail?.jobs ?? []).some(isJobActive) || detail?.project.status === 'generating',
    [detail],
  );

  useEffect(() => {
    if (busy) {
      pollRef.current = setInterval(refresh, 3500);
      return () => {
        if (pollRef.current) clearInterval(pollRef.current);
      };
    }
  }, [busy, refresh]);

  async function remove() {
    if (!confirmDelete) {
      setConfirmDelete(true);
      setTimeout(() => setConfirmDelete(false), 4000);
      return;
    }
    try {
      await deleteProject(pid);
      router.push('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed');
    }
  }

  if (error && !detail) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-16">
        <ErrorNote message={error} onRetry={refresh} />
        <Link href="/" className="btn-ghost mt-4">
          ← Back to productions
        </Link>
      </main>
    );
  }

  if (!detail) {
    return (
      <main className="flex h-screen items-center justify-center text-muted">
        <Spinner className="h-6 w-6" />
      </main>
    );
  }

  const { project, messages, assets, jobs } = detail;
  const doneJobs = jobs.filter((j) => j.status === 'done').length;

  return (
    <main className="flex h-screen flex-col overflow-hidden">
      {/* Top bar */}
      <header className="flex items-center gap-4 border-b border-line bg-panel/60 px-5 py-3 backdrop-blur">
        <Link href="/" className="shrink-0">
          <Brand />
        </Link>
        <div className="mx-1 h-6 w-px bg-line" />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h1 className="truncate text-sm font-bold">{project.title}</h1>
            <StatusChip status={project.status} />
          </div>
          <p className="truncate text-[11px] text-muted">
            {project.platform ?? 'web'} · {project.style ?? 'default style'} ·{' '}
            {project.duration_hint_s ? `${project.duration_hint_s}s target` : 'duration free'} ·{' '}
            created {relTime(project.created_at)} · {assets.length} assets · {doneJobs}/{jobs.length} jobs done
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <button className="btn-ghost !py-1.5 text-xs" onClick={refresh} title="Refresh from backend">
            Refresh
          </button>
          <button
            className={`!py-1.5 text-xs ${confirmDelete ? 'btn-danger' : 'btn-ghost'}`}
            onClick={remove}
            title={confirmDelete ? 'Click again to confirm' : 'Delete project'}
          >
            {confirmDelete ? 'Confirm delete' : 'Delete'}
          </button>
        </div>
      </header>

      {/* Studio body */}
      <div className="grid min-h-0 flex-1 gap-4 p-4 lg:grid-cols-[400px_1fr]">
        <div className="min-h-0 max-lg:h-[46vh]">
          <ChatPanel project={project} messages={messages} assets={assets} jobs={jobs} onActivity={refresh} />
        </div>

        <div className="flex min-h-0 flex-col gap-3">
          <div className="flex items-center justify-between gap-3">
            <Tabs<Tab>
              active={tab}
              onChange={setTab}
              tabs={[
                { id: 'preview', label: 'Preview' },
                { id: 'timeline', label: 'Timeline' },
                { id: 'media', label: 'Media', badge: assets.length },
                { id: 'providers', label: 'Providers' },
              ]}
            />
            <span className="hidden font-mono text-[10px] text-muted/70 md:block">{API_URL}</span>
          </div>
          <div className="min-h-0 flex-1 overflow-hidden">
            {error ? <ErrorNote message={error} onRetry={refresh} /> : null}
            <div className="h-full pt-2">
              {tab === 'preview' ? (
                <PreviewPane assets={assets} />
              ) : tab === 'timeline' ? (
                <TimelineView assets={assets} onOpenPreview={() => setTab('preview')} />
              ) : tab === 'media' ? (
                <MediaPanel assets={assets} onOpenPreview={() => setTab('preview')} />
              ) : (
                <ProviderStatus health={health} />
              )}
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
