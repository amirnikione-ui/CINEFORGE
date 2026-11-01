"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import NewProjectDialog from "@/components/NewProjectDialog";
import TopBar, { StatusPill } from "@/components/TopBar";
import { API_BASE, ApiError, apiDown, formatTimestamp, getHealth, getProjectDetail, listProjects } from "@/lib/api";
import type { Health, Project } from "@/types/api";

export default function DashboardPage() {
  const router = useRouter();
  /** null = still loading (skeleton); [] = genuinely no projects yet */
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  /** null = checking, true = online, false = offline */
  const [online, setOnline] = useState<boolean | null>(null);
  const [listError, setListError] = useState<string | null>(null);
  const [assetCounts, setAssetCounts] = useState<Record<string, number>>({});
  const [dialogOpen, setDialogOpen] = useState(false);

  const projectsRef = useRef<Project[]>([]);
  projectsRef.current = projects ?? [];

  const loadAll = useCallback(async () => {
    try {
      const h = await getHealth();
      setHealth(h);
      setOnline(true);
    } catch {
      setOnline(false);
    }
    try {
      const list = await listProjects();
      setProjects(list);
      setListError(null);
    } catch (err) {
      setListError(
        apiDown(err)
          ? `Cannot reach API at ${API_BASE} — start the backend (make api).`
          : err instanceof ApiError
            ? `API ${err.status}: ${err.detail}`
            : "Failed to load projects.",
      );
    }
  }, []);

  // Initial load + poll every 5s, only while the tab is visible.
  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const tick = async () => {
      if (cancelled) return;
      if (!document.hidden) await loadAll();
      if (!cancelled) timer = setTimeout(tick, 5000);
    };
    void tick();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [loadAll]);

  // Refresh immediately when the tab becomes visible again.
  useEffect(() => {
    const onVisibility = () => {
      if (!document.hidden) void loadAll();
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, [loadAll]);

  // Real asset counts from the detail endpoint — refreshed only when the roster or statuses change.
  const rosterSignature = useMemo(
    () => (projects ?? []).map((p) => `${p.id}:${p.status}`).join("|"),
    [projects],
  );
  useEffect(() => {
    const current = projectsRef.current;
    if (current.length === 0) {
      setAssetCounts({});
      return;
    }
    let cancelled = false;
    void (async () => {
      const settled = await Promise.allSettled(current.slice(0, 24).map((p) => getProjectDetail(p.id)));
      if (cancelled) return;
      const next: Record<string, number> = {};
      settled.forEach((r, i) => {
        if (r.status === "fulfilled") next[current[i].id] = r.value.assets.length;
      });
      setAssetCounts(next);
    })();
    return () => {
      cancelled = true;
    };
  }, [rosterSignature]);

  const openStudio = useCallback((p: Project) => router.push(`/studio/${p.id}`), [router]);

  return (
    <div className="flex min-h-screen flex-col bg-ink">
      <TopBar variant="dashboard" health={health} apiOnline={online} />

      {/* Hero */}
      <section className="border-b border-ink-line bg-gradient-to-b from-ink-raised/50 to-transparent">
        <div className="mx-auto w-full max-w-6xl px-4 py-10">
          <h1 className="max-w-3xl text-3xl font-semibold leading-tight tracking-tight text-white sm:text-4xl">
            Describe the video. <span className="gradient-text">The agent directs, codes, and renders it.</span>
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-zinc-400">
            One brief in — storyboard, concept frames, narration, music, motion graphics and a finished cut out.
            Real files, real code, every artifact yours.
          </p>
          <div className="mt-6">
            <NewProjectDialog variant="inline" onCreated={openStudio} />
          </div>
        </div>
      </section>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-zinc-500">
            Projects{projects ? ` · ${projects.length}` : ""}
          </h2>
          <button type="button" onClick={() => setDialogOpen(true)} className="btn-accent">
            + New project
          </button>
        </div>

        {listError && projects !== null && (
          <div className="mb-4 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-300">
            Refresh failed — {listError} Showing the last known list.
          </div>
        )}

        {projects === null && !listError ? (
          // Loading — skeleton shimmer only.
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="shimmer h-[128px] rounded-xl border border-ink-line" />
            ))}
          </div>
        ) : projects !== null && projects.length === 0 ? (
          // Honest empty state.
          <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-ink-line py-14 text-center">
            <span className="text-3xl opacity-30">🎬</span>
            <p className="text-sm text-zinc-400">No projects yet — create your first brief.</p>
            <p className="text-xs text-zinc-600">
              The director replies in the studio chat and starts producing immediately.
            </p>
          </div>
        ) : projects === null && listError ? (
          // API unreachable / error before any data arrived.
          <div className="flex flex-col items-center gap-3 rounded-xl border border-amber-500/30 bg-amber-500/5 py-14 text-center">
            <span className="text-2xl opacity-50">📡</span>
            <p className="max-w-md text-sm text-amber-300">{listError}</p>
            <button
              type="button"
              onClick={() => void loadAll()}
              className="rounded-lg border border-ink-line px-3 py-1.5 text-xs text-zinc-300 transition hover:border-accent-cyan/50 hover:text-accent-cyan"
            >
              Retry
            </button>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {(projects ?? []).map((p) => (
              <ProjectCard key={p.id} project={p} assetCount={assetCounts[p.id]} onOpen={() => openStudio(p)} />
            ))}
          </div>
        )}
      </main>

      <footer className="border-t border-ink-line py-4">
        <p className="text-center font-mono text-[10px] text-zinc-700">
          CINEFORGE · API{" "}
          {online === null
            ? "checking…"
            : online
              ? `v${health?.version ?? "?"} @ ${API_BASE}`
              : `offline @ ${API_BASE}`}
        </p>
      </footer>

      <NewProjectDialog variant="modal" open={dialogOpen} onClose={() => setDialogOpen(false)} onCreated={openStudio} />
    </div>
  );
}

function ProjectCard({
  project: p,
  assetCount,
  onOpen,
}: {
  project: Project;
  assetCount?: number;
  onOpen: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onOpen}
      className="group flex flex-col rounded-xl border border-ink-line bg-ink-panel p-4 text-left shadow-panel transition duration-150 hover:-translate-y-0.5 hover:border-accent-violet/40 hover:bg-ink-raised active:scale-[0.99]"
    >
      <div className="flex items-start justify-between gap-2">
        <h3 className="min-w-0 flex-1 truncate text-sm font-semibold tracking-tight text-zinc-100">{p.title}</h3>
        <StatusPill status={p.status} />
      </div>
      <p className="mt-2 line-clamp-2 min-h-[2rem] text-xs leading-relaxed text-zinc-400">{p.brief}</p>
      <div className="mt-auto flex items-center gap-2 border-t border-ink-line/70 pt-2.5 font-mono text-[10px] text-zinc-500">
        {p.platform && <span className="rounded border border-ink-line px-1.5 py-0.5">{p.platform}</span>}
        <span>{formatTimestamp(p.created_at)}</span>
        {assetCount !== undefined && (
          <span className="ml-auto text-zinc-400">
            🎞 {assetCount} asset{assetCount === 1 ? "" : "s"}
          </span>
        )}
      </div>
    </button>
  );
}
