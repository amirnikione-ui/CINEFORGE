"use client";

import { useMemo } from "react";
import type { ReactNode } from "react";
import { assetUrl, formatDuration } from "@/lib/api";
import type { Asset, Storyboard } from "@/types/api";

function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

function latestOfKind(assets: Asset[], kind: Asset["kind"]): Asset | null {
  let latest: Asset | null = null;
  for (const a of assets) {
    if (a.kind !== kind) continue;
    if (!latest || (a.created_at ?? "") > (latest.created_at ?? "")) latest = a;
  }
  return latest;
}

interface PreviewPaneProps {
  assets: Asset[];
  storyboard: Storyboard | null;
  storyboardLoading: boolean;
  storyboardError: string | null;
  onRetryStoryboard: () => void;
  className?: string;
}

/**
 * Priority: latest rendered video (HTML5 player) → storyboard pre-vis (scene cards
 * built from the storyboard JSON) → honest empty state.
 */
export default function PreviewPane({
  assets,
  storyboard,
  storyboardLoading,
  storyboardError,
  onRetryStoryboard,
  className,
}: PreviewPaneProps) {
  const video = useMemo(() => latestOfKind(assets, "video"), [assets]);
  const poster = useMemo(() => assets.find((a) => a.meta?.poster === true) ?? null, [assets]);

  return (
    <section className={cx("flex min-h-0 flex-col bg-ink", className)} aria-label="Preview">
      <header className="flex h-9 shrink-0 items-center justify-between border-b border-ink-line bg-ink-panel/50 px-3">
        <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">Preview</span>
        {video && <span className="truncate font-mono text-[10px] text-zinc-600">{video.filename}</span>}
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {video ? (
          <VideoView video={video} posterUrl={poster ? assetUrl(poster.id) : undefined} />
        ) : storyboard ? (
          <StoryboardView storyboard={storyboard} />
        ) : storyboardLoading ? (
          <LoadingView />
        ) : storyboardError ? (
          <ErrorView message={storyboardError} onRetry={onRetryStoryboard} />
        ) : (
          <EmptyView />
        )}
      </div>
    </section>
  );
}

function VideoView({ video, posterUrl }: { video: Asset; posterUrl?: string }) {
  const meta = video.meta ?? {};
  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex min-h-0 flex-1 items-center justify-center bg-black/50 p-4">
        <video
          key={video.id}
          src={assetUrl(video.id)}
          poster={posterUrl}
          controls
          preload="metadata"
          className="max-h-full max-w-full rounded-lg shadow-panel"
        />
      </div>
      <div className="flex flex-wrap items-center gap-2 border-t border-ink-line px-3 py-2 font-mono text-[10px] text-zinc-500">
        {typeof meta.duration_s === "number" && <Chip>{formatDuration(meta.duration_s)}</Chip>}
        {typeof meta.width === "number" && typeof meta.height === "number" && (
          <Chip>
            {meta.width}×{meta.height}
          </Chip>
        )}
        {typeof meta.fps === "number" && <Chip>{meta.fps} fps</Chip>}
        {typeof meta.provider === "string" && <Chip accent>{meta.provider}</Chip>}
      </div>
    </div>
  );
}

function StoryboardView({ storyboard: sb }: { storyboard: Storyboard }) {
  return (
    <div className="p-4">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <h3 className="text-sm font-semibold tracking-tight text-zinc-100">{sb.title}</h3>
        <Chip>{sb.aspect}</Chip>
        <Chip>{sb.fps} fps</Chip>
        <Chip>{sb.scenes.length} scenes</Chip>
        <Chip>{sb.duration_target_s}s target</Chip>
        <Chip accent>{sb.music_mood}</Chip>
        <div className="ml-auto flex items-center gap-1" title="Palette">
          {Object.entries(sb.palette ?? {}).map(([name, hex]) => (
            <span
              key={name}
              className="h-4 w-4 rounded border border-white/10"
              style={{ backgroundColor: hex }}
              title={`${name}: ${hex}`}
            />
          ))}
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 2xl:grid-cols-3">
        {sb.scenes.map((sc, i) => (
          <article key={sc.id} className="panel p-3 transition hover:border-accent-violet/30">
            <div className="flex items-center justify-between font-mono text-[9px] uppercase tracking-widest">
              <span className="text-accent-cyan/80">
                {String(i + 1).padStart(2, "0")} · {sc.kind}
              </span>
              <span className="text-zinc-500">
                {sc.duration_s}s · {sc.motion?.style ?? "—"}
              </span>
            </div>
            <h4 className="mt-1.5 text-sm font-semibold tracking-tight text-zinc-100">{sc.headline}</h4>
            {sc.body && <p className="mt-1 text-xs leading-relaxed text-zinc-400">{sc.body}</p>}
            {sc.narration && (
              <p className="mt-1 border-l-2 border-accent-cyan/40 pl-2 text-[11px] italic leading-relaxed text-zinc-500">
                🎙 {sc.narration}
              </p>
            )}
            <p className="mt-2 line-clamp-2 text-[11px] leading-snug text-zinc-600">
              <span className="text-zinc-500">prompt:</span> {sc.visual_prompt}
            </p>
          </article>
        ))}
      </div>
    </div>
  );
}

function Chip({ children, accent = false }: { children: ReactNode; accent?: boolean }) {
  return (
    <span
      className={cx(
        "rounded border px-1.5 py-0.5",
        accent ? "border-accent-violet/40 bg-accent-violet/10 text-accent-violet" : "border-ink-line bg-ink-raised",
      )}
    >
      {children}
    </span>
  );
}

function LoadingView() {
  return (
    <div className="grid gap-3 p-4 sm:grid-cols-2">
      {[0, 1, 2, 3].map((i) => (
        <div key={i} className="shimmer h-24 rounded-xl border border-ink-line" />
      ))}
    </div>
  );
}

function ErrorView({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 p-6 text-center">
      <p className="text-sm text-red-400">Could not load the storyboard: {message}</p>
      <button
        type="button"
        onClick={onRetry}
        className="rounded-lg border border-ink-line px-3 py-1.5 text-xs text-zinc-300 transition hover:border-accent-cyan/50 hover:text-accent-cyan"
      >
        Retry
      </button>
    </div>
  );
}

function EmptyView() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 p-6 text-center">
      <span className="text-3xl opacity-30">🎬</span>
      <p className="text-sm text-zinc-500">No render yet — send a brief to the director.</p>
      <p className="max-w-xs text-xs leading-relaxed text-zinc-600">
        The finished .mp4 shows up here automatically; until then the storyboard pre-vis is displayed.
      </p>
    </div>
  );
}
