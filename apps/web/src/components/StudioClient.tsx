"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import AssetsPanel from "@/components/AssetsPanel";
import ChatPanel from "@/components/ChatPanel";
import PreviewPane from "@/components/PreviewPane";
import Timeline from "@/components/Timeline";
import TopBar from "@/components/TopBar";
import { API_BASE, ApiError, apiDown, getAssetJson, getHealth, getProjectDetail, sendChat } from "@/lib/api";
import type { Asset, AssetKind, Health, Job, Message, ProjectDetail, Storyboard } from "@/types/api";

function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

function latestAssetOfKind(assets: Asset[], kind: AssetKind): Asset | null {
  let latest: Asset | null = null;
  for (const a of assets) {
    if (a.kind !== kind) continue;
    if (!latest || (a.created_at ?? "") > (latest.created_at ?? "")) latest = a;
  }
  return latest;
}

function mergeAssets(current: Asset[], incoming: Asset[]): Asset[] {
  const seen = new Set(current.map((x) => x.id));
  return [...current, ...incoming.filter((x) => !seen.has(x.id))];
}

function mergeJobs(current: Job[], incoming: Job[]): Job[] {
  const byId = new Map(current.map((j) => [j.id, j]));
  for (const j of incoming) byId.set(j.id, j);
  return [...byId.values()];
}

/**
 * The storyboard JSON lives behind the asset file endpoint — fetch it once here and
 * share it with PreviewPane (pre-vis) and Timeline so we don't double-fetch.
 */
function useStoryboard(assets: Asset[]) {
  const storyboardAsset = useMemo(() => latestAssetOfKind(assets, "storyboard"), [assets]);
  const [storyboard, setStoryboard] = useState<Storyboard | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);
  const reload = useCallback(() => setNonce((n) => n + 1), []);

  useEffect(() => {
    if (!storyboardAsset) {
      setStoryboard(null);
      setError(null);
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    getAssetJson<Storyboard>(storyboardAsset.id)
      .then((sb) => {
        if (!sb || !Array.isArray(sb.scenes)) throw new Error("unexpected storyboard JSON shape");
        if (!cancelled) setStoryboard(sb);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setStoryboard(null);
          setError(err instanceof Error ? err.message : "unknown error");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [storyboardAsset, nonce]);

  return { storyboardAsset, storyboard, loading, error, reload };
}

type DetailPhase = "loading" | "ready" | "notfound" | "error";

/**
 * Project data plumbing: initial load + adaptive polling (2.5s while the pipeline is
 * hot — pending/running jobs or a generating project — 8s when idle; paused while the
 * tab is hidden) + optimistic chat sends + provider health.
 */
function useProjectDetail(projectId: string) {
  const [detail, setDetail] = useState<ProjectDetail | null>(null);
  const [phase, setPhase] = useState<DetailPhase>("loading");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);

  const detailRef = useRef<ProjectDetail | null>(null);
  const busyRef = useRef(false);

  const refresh = useCallback(async (): Promise<boolean> => {
    if (busyRef.current) return true; // a fetch is already in flight
    busyRef.current = true;
    try {
      const d = await getProjectDetail(projectId);
      detailRef.current = d;
      setDetail(d);
      setPhase("ready");
      setLoadError(null);
      setApiOnline(true);
      return true;
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setPhase("notfound");
      } else if (apiDown(err)) {
        setApiOnline(false);
        setLoadError(`Cannot reach API at ${API_BASE}`);
        setPhase((p) => (p === "loading" ? "error" : p));
      } else {
        setLoadError(
          err instanceof ApiError ? `API ${err.status}: ${err.detail}` : "Unexpected error while loading the project.",
        );
        setPhase((p) => (p === "loading" ? "error" : p));
      }
      return false;
    } finally {
      busyRef.current = false;
    }
  }, [projectId]);

  // Initial load.
  useEffect(() => {
    void refresh();
  }, [refresh]);

  // Adaptive polling.
  useEffect(() => {
    if (phase === "notfound") return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const tick = async () => {
      if (cancelled) return;
      if (!document.hidden) await refresh();
      if (cancelled) return;
      const d = detailRef.current;
      const hot =
        !!d && (d.project.status === "generating" || d.jobs.some((j) => j.status === "pending" || j.status === "running"));
      timer = setTimeout(tick, hot ? 2500 : 8000);
    };
    timer = setTimeout(tick, 2500);
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [refresh, phase]);

  // Provider status for the top bar (kept honest afterwards by refresh()/send() results).
  useEffect(() => {
    let cancelled = false;
    getHealth()
      .then((h) => {
        if (!cancelled) {
          setHealth(h);
          setApiOnline(true);
        }
      })
      .catch(() => {
        if (!cancelled) setApiOnline(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const send = useCallback(
    async (text: string): Promise<boolean> => {
      const trimmed = text.trim();
      if (!trimmed || sending) return false;

      const tempId = `local-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      const optimistic: Message = {
        id: tempId,
        project_id: projectId,
        role: "user",
        content: trimmed,
        meta: null,
        created_at: new Date().toISOString(),
      };

      setSendError(null);
      setDetail((d) => (d ? { ...d, messages: [...d.messages, optimistic] } : d));
      setSending(true);
      try {
        const resp = await sendChat(projectId, trimmed);
        setDetail((d) =>
          d
            ? {
                ...d,
                messages: [...d.messages.filter((m) => m.id !== tempId), resp.user_message, resp.assistant_message],
                assets: mergeAssets(d.assets, resp.assets),
                jobs: mergeJobs(d.jobs, resp.jobs),
              }
            : d,
        );
        setApiOnline(true);
        return true;
      } catch (err) {
        // Roll back the optimistic message — honest error notice in the chat instead.
        setDetail((d) => (d ? { ...d, messages: d.messages.filter((m) => m.id !== tempId) } : d));
        if (apiDown(err)) setApiOnline(false);
        setSendError(
          err instanceof ApiError
            ? `The director could not process that (API ${err.status}): ${err.detail}`
            : `Could not reach the API at ${API_BASE} — your message was not delivered. Is the backend running? (make api)`,
        );
        return false;
      } finally {
        setSending(false);
      }
    },
    [projectId, sending],
  );

  return { detail, phase, loadError, apiOnline, health, sending, sendError, send, refresh };
}

export default function StudioClient({ projectId }: { projectId: string }) {
  const { detail, phase, loadError, apiOnline, health, sending, sendError, send, refresh } = useProjectDetail(projectId);
  const [mobileChatOpen, setMobileChatOpen] = useState(false);
  /** null = default (visible on xl+), true = forced open, false = hidden */
  const [assetsOpen, setAssetsOpen] = useState<boolean | null>(null);

  const assets = detail?.assets ?? [];
  const jobs = detail?.jobs ?? [];
  const messages = detail?.messages ?? [];
  const { storyboard, loading: storyboardLoading, error: storyboardError, reload: reloadStoryboard } = useStoryboard(assets);

  if (phase === "loading") {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-3 bg-ink text-zinc-400">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-ink-line border-t-accent-violet" />
        <p className="text-sm">Loading project…</p>
      </div>
    );
  }

  if (phase === "notfound") {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-2 bg-ink text-center">
        <span className="text-3xl opacity-40">🎞️</span>
        <h1 className="mt-2 text-lg font-semibold text-zinc-200">Project not found</h1>
        <p className="max-w-sm text-sm leading-relaxed text-zinc-500">
          It may have been deleted, or the id is wrong.
        </p>
        <Link href="/" className="btn-accent mt-3">
          ← Back to projects
        </Link>
      </div>
    );
  }

  if (phase === "error" || !detail) {
    return (
      <div className="flex h-screen flex-col bg-ink">
        <TopBar variant="studio" health={health} apiOnline={apiOnline} project={null} />
        {apiOnline === false && <OfflineBanner />}
        <div className="flex flex-1 flex-col items-center justify-center gap-2 px-6 text-center">
          <span className="text-3xl opacity-40">📡</span>
          <h1 className="mt-2 text-lg font-semibold text-zinc-200">Cannot load this project</h1>
          <p className="max-w-md text-sm leading-relaxed text-zinc-500">{loadError ?? "Unknown error."}</p>
          <button type="button" onClick={() => void refresh()} className="btn-accent mt-3">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col bg-ink text-zinc-200">
      <TopBar variant="studio" health={health} apiOnline={apiOnline} project={detail.project} />

      {apiOnline === false && <OfflineBanner />}
      {apiOnline !== false && loadError && (
        <div className="shrink-0 border-b border-red-500/30 bg-red-500/10 px-4 py-1 text-center text-[11px] text-red-300">
          Last refresh failed ({loadError}) — retrying automatically.
        </div>
      )}

      {/* Panel toggles for narrow screens */}
      <div className="flex shrink-0 items-center gap-2 border-b border-ink-line bg-ink-panel/60 px-3 py-1.5 xl:hidden">
        <button
          type="button"
          onClick={() => setMobileChatOpen(true)}
          className="rounded-lg border border-ink-line px-2.5 py-1 text-xs text-zinc-300 transition hover:border-accent-violet/50 lg:hidden"
        >
          💬 Chat
        </button>
        <button
          type="button"
          onClick={() => setAssetsOpen((o) => (o === null ? true : !o))}
          className={cx(
            "rounded-lg border px-2.5 py-1 text-xs transition",
            assetsOpen ?? false
              ? "border-accent-violet/60 bg-accent-violet/10 text-accent-violet"
              : "border-ink-line text-zinc-300 hover:border-accent-violet/50",
          )}
        >
          {assetsOpen ?? false ? "✕ Media" : "🗂 Media"}
        </button>
        <span className="ml-auto truncate font-mono text-[9px] text-zinc-600">
          {detail.project.platform ? String(detail.project.platform) : ""}
        </span>
      </div>

      <div className="flex min-h-0 flex-1">
        {mobileChatOpen && (
          <div className="fixed inset-0 z-30 bg-black/60 lg:hidden" onClick={() => setMobileChatOpen(false)} />
        )}

        <ChatPanel
          messages={messages}
          sending={sending}
          sendError={sendError}
          onSend={send}
          onClose={() => setMobileChatOpen(false)}
          className={cx(
            "w-[380px] shrink-0 border-r border-ink-line bg-ink-panel",
            mobileChatOpen
              ? "fixed inset-y-0 left-0 z-40 flex shadow-panel lg:static lg:z-auto lg:shadow-none"
              : "hidden lg:flex",
          )}
        />

        <main className="flex min-w-0 flex-1 flex-col">
          <PreviewPane
            assets={assets}
            storyboard={storyboard}
            storyboardLoading={storyboardLoading}
            storyboardError={storyboardError}
            onRetryStoryboard={reloadStoryboard}
            className="min-h-0 flex-1"
          />
          <Timeline
            assets={assets}
            storyboard={storyboard}
            storyboardLoading={storyboardLoading}
            storyboardError={storyboardError}
            onRetryStoryboard={reloadStoryboard}
            className="h-[200px] shrink-0"
          />
        </main>

        <AssetsPanel
          assets={assets}
          jobs={jobs}
          className={cx(
            "w-[300px] shrink-0 border-l border-ink-line bg-ink-panel",
            assetsOpen === true ? "flex" : assetsOpen === false ? "hidden" : "hidden xl:flex",
          )}
        />
      </div>
    </div>
  );
}

function OfflineBanner() {
  return (
    <div className="shrink-0 border-b border-amber-500/30 bg-amber-500/10 px-4 py-1.5 text-center text-xs text-amber-300">
      Cannot reach API at {API_BASE} — start the backend (<span className="font-mono">make api</span>). Retrying
      automatically…
    </div>
  );
}
