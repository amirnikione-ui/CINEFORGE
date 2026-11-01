"use client";

import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import type { Asset, Storyboard } from "@/types/api";

function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

const ZOOM_STEPS = [12, 24, 48];
const RULER_H = "h-6";
const ROW_VIDEO_H = "h-12";
const ROW_AUDIO_H = "h-8";
const ROW_MUSIC_H = "h-8";
const ROW_OVERLAY_H = "h-6";

interface TimelineProps {
  assets: Asset[];
  storyboard: Storyboard | null;
  storyboardLoading: boolean;
  storyboardError: string | null;
  onRetryStoryboard: () => void;
  className?: string;
}

/**
 * Timeline v1 — real data, honest limits.
 * Rows: VIDEO (scene blocks), AUDIO (narration per scene), MUSIC (full-width bed),
 * OVERLAY (transition diamonds at scene boundaries). Ruler ticks every 5s, zoom
 * 12/24/48 px/s, static playhead at t=0 (scrubbing lands in M4 — stated in the UI).
 */
export default function Timeline({
  assets,
  storyboard,
  storyboardLoading,
  storyboardError,
  onRetryStoryboard,
  className,
}: TimelineProps) {
  const [pxPerSec, setPxPerSec] = useState(24);

  const scenes = useMemo(() => storyboard?.scenes ?? [], [storyboard]);
  const { offsets, total } = useMemo(() => {
    let t = 0;
    const offs = scenes.map((sc) => {
      const o = t;
      t += sc.duration_s;
      return o;
    });
    return { offsets: offs, total: t };
  }, [scenes]);

  const music = useMemo(() => {
    let latest: Asset | null = null;
    for (const a of assets) {
      if (a.kind !== "audio" || a.meta?.music !== true) continue;
      if (!latest || (a.created_at ?? "") > (latest.created_at ?? "")) latest = a;
    }
    return latest;
  }, [assets]);

  const palette = {
    bg: storyboard?.palette?.bg ?? "#0a0a12",
    primary: storyboard?.palette?.primary ?? "#7c5cff",
    accent: storyboard?.palette?.accent ?? "#00e5ff",
    text: storyboard?.palette?.text ?? "#f5f5ff",
  };

  const contentWidth = Math.max(total * pxPerSec + 8, 320);
  const ticks: number[] = [];
  for (let s = 0; s <= Math.ceil(total); s += 5) ticks.push(s);

  return (
    <section className={cx("flex shrink-0 flex-col border-t border-ink-line bg-ink-panel/40", className)} aria-label="Timeline">
      <header className="flex h-8 shrink-0 items-center gap-3 border-b border-ink-line px-3">
        <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">Timeline</span>
        {storyboard && (
          <span className="hidden font-mono text-[10px] text-zinc-600 sm:block">
            {total.toFixed(1)}s · {scenes.length} scene{scenes.length === 1 ? "" : "s"} · {storyboard.aspect}
          </span>
        )}
        <div className="ml-auto flex items-center gap-3">
          <span className="hidden font-mono text-[9px] text-zinc-600 md:block">v1 — playback scrubbing lands in M4</span>
          <div className="flex items-center gap-1">
            {ZOOM_STEPS.map((z) => (
              <button
                key={z}
                type="button"
                onClick={() => setPxPerSec(z)}
                className={cx(
                  "rounded border px-1.5 py-0.5 font-mono text-[9px] transition",
                  pxPerSec === z
                    ? "border-accent-violet/60 bg-accent-violet/15 text-accent-violet"
                    : "border-ink-line text-zinc-500 hover:text-zinc-300",
                )}
              >
                {z}px/s
              </button>
            ))}
          </div>
        </div>
      </header>

      <div className="min-h-0 flex-1">
        {!storyboard ? (
          storyboardLoading ? (
            <div className="m-3 shimmer h-16 rounded-lg border border-ink-line" />
          ) : storyboardError ? (
            <div className="flex h-full items-center justify-center gap-3 px-4 text-center">
              <p className="text-xs text-red-400">Storyboard failed to load: {storyboardError}</p>
              <button
                type="button"
                onClick={onRetryStoryboard}
                className="rounded border border-ink-line px-2 py-1 text-[10px] text-zinc-300 transition hover:border-accent-cyan/50 hover:text-accent-cyan"
              >
                Retry
              </button>
            </div>
          ) : (
            <div className="flex h-full items-center justify-center px-4 text-center">
              <p className="text-xs text-zinc-600">Timeline appears after the director plans your video.</p>
            </div>
          )
        ) : (
          <div className="flex h-full min-h-0">
            {/* Row labels (fixed column) */}
            <div className="w-[72px] shrink-0 border-r border-ink-line">
              <div className={cx("flex items-end justify-end border-b border-ink-line px-1.5 pb-1", RULER_H)}>
                <span className="font-mono text-[8px] text-zinc-700">{pxPerSec}px/s</span>
              </div>
              <RowLabel className={ROW_VIDEO_H}>Video</RowLabel>
              <RowLabel className={ROW_AUDIO_H}>Audio</RowLabel>
              <RowLabel className={ROW_MUSIC_H}>Music</RowLabel>
              <RowLabel className={cx(ROW_OVERLAY_H, "border-b-0")}>Overlay</RowLabel>
            </div>

            {/* Scrollable lanes */}
            <div className="min-w-0 flex-1 overflow-x-auto overflow-y-hidden">
              <div className="relative" style={{ width: contentWidth }}>
                {/* Ruler */}
                <div className={cx("relative border-b border-ink-line", RULER_H)}>
                  {ticks.map((s) => (
                    <div key={s} className="absolute bottom-0 top-0" style={{ left: s * pxPerSec }}>
                      <div className="absolute bottom-0 h-2 w-px bg-zinc-700" />
                      <span className="absolute left-1 top-0.5 font-mono text-[9px] text-zinc-600">{s}s</span>
                    </div>
                  ))}
                </div>

                {/* VIDEO — scene blocks, palette-derived gradient */}
                <div className={cx("relative border-b border-ink-line/60", ROW_VIDEO_H)}>
                  {scenes.map((sc, i) => (
                    <div
                      key={sc.id}
                      title={`${sc.id} — ${sc.headline} (${sc.duration_s}s, ${sc.motion?.style ?? "—"} ${
                        Math.round(((sc.motion?.intensity ?? 0) as number) * 100) || 0
                      }%)`}
                      className="absolute inset-y-1 overflow-hidden rounded-md border px-1.5"
                      style={{
                        left: offsets[i] * pxPerSec + 1,
                        width: Math.max(sc.duration_s * pxPerSec - 2, 8),
                        background: `linear-gradient(135deg, ${palette.primary}55, ${palette.accent}30)`,
                        borderColor: `${palette.primary}77`,
                      }}
                    >
                      <div className="truncate pt-0.5 text-[10px] font-medium leading-tight text-zinc-100">
                        {sc.headline}
                      </div>
                      <div className="truncate font-mono text-[9px] text-zinc-300/70">{sc.duration_s.toFixed(1)}s</div>
                    </div>
                  ))}
                </div>

                {/* AUDIO — narration blocks (muted cyan) */}
                <div className={cx("relative border-b border-ink-line/60", ROW_AUDIO_H)}>
                  {scenes.map((sc, i) =>
                    sc.narration ? (
                      <div
                        key={sc.id}
                        title={sc.narration}
                        className="absolute inset-y-1 overflow-hidden rounded-md border border-cyan-300/25 bg-cyan-400/10 px-1.5"
                        style={{ left: offsets[i] * pxPerSec + 1, width: Math.max(sc.duration_s * pxPerSec - 2, 8) }}
                      >
                        <div className="truncate text-[9px] leading-5 text-cyan-100/70">🎙 {sc.narration}</div>
                      </div>
                    ) : null,
                  )}
                  {scenes.length > 0 && !scenes.some((sc) => sc.narration) && (
                    <span className="absolute left-2 top-1/2 -translate-y-1/2 font-mono text-[9px] text-zinc-700">
                      no narration lines yet
                    </span>
                  )}
                </div>

                {/* MUSIC — single full-width bed */}
                <div className={cx("relative border-b border-ink-line/60", ROW_MUSIC_H)}>
                  {music ? (
                    <div
                      title={`${music.filename} — ${typeof music.meta?.provider === "string" ? music.meta.provider : "unknown provider"}`}
                      className="absolute inset-y-1 left-1 overflow-hidden rounded-md border border-violet-300/25 bg-violet-400/10 px-1.5"
                      style={{ width: Math.max(total * pxPerSec - 2, 8) }}
                    >
                      <div className="truncate text-[9px] leading-5 text-violet-200/80">
                        🎵 {music.filename}
                        {typeof music.meta?.provider === "string" ? ` · ${music.meta.provider}` : ""}
                      </div>
                    </div>
                  ) : (
                    <span className="absolute left-2 top-1/2 -translate-y-1/2 font-mono text-[9px] text-zinc-700">
                      no music asset yet
                    </span>
                  )}
                </div>

                {/* OVERLAY — transition markers at scene boundaries */}
                <div className={cx("relative", ROW_OVERLAY_H)}>
                  {scenes.map((sc, i) =>
                    sc.transition_in && sc.transition_in !== "cut" ? (
                      <div
                        key={sc.id}
                        title={`${sc.transition_in} @ ${offsets[i].toFixed(1)}s`}
                        className="absolute top-1/2 h-2 w-2 -translate-y-1/2 rotate-45 rounded-[2px] border border-accent-cyan/60 bg-accent-cyan/30"
                        style={{ left: offsets[i] * pxPerSec - 4 }}
                      />
                    ) : null,
                  )}
                </div>

                {/* Playhead — static accent line at t=0 (v1) */}
                <div
                  className="pointer-events-none absolute bottom-0 top-0 z-10 w-px bg-accent-cyan shadow-glow"
                  style={{ left: 0 }}
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

function RowLabel({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cx("flex items-center border-b border-ink-line/60 px-2", className)}>
      <span className="font-mono text-[9px] uppercase tracking-widest text-zinc-600">{children}</span>
    </div>
  );
}
