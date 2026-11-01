'use client';

import { useEffect, useMemo, useState } from 'react';
import { assetFileUrl, latestAsset } from '@/lib/api';
import type { Asset, Scene, Storyboard } from '@/types/api';
import { SCENE_KIND_COLORS } from '@/lib/format';
import { aspectDimensions, parseStoryboard, storyboardDurationOk, storyboardLanes } from '@/lib/storyboard';
import { EmptyState } from '@/components/ui';

function Ruler({ total }: { total: number }) {
  const step = total > 60 ? 10 : total > 30 ? 5 : 2;
  const ticks: number[] = [];
  for (let t = 0; t <= total + 1e-6; t += step) ticks.push(t);
  return (
    <div className="relative h-5 border-b border-line">
      {ticks.map((t) => (
        <span
          key={t}
          className="absolute top-0 border-l border-line pl-1 font-mono text-[9px] text-muted"
          style={{ left: `${(t / total) * 100}%` }}
        >
          {t}s
        </span>
      ))}
    </div>
  );
}

function SceneInspector({
  scene,
  durationOk,
  dims,
}: {
  scene: Scene;
  durationOk: boolean;
  dims: { width: number; height: number };
}) {
  const color = SCENE_KIND_COLORS[scene.kind];
  return (
    <div className="panel space-y-3 p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`h-2.5 w-2.5 rounded-full ${color?.dot ?? 'bg-white/30'}`} />
          <h3 className="font-mono text-sm font-bold">{scene.id}</h3>
          <span className="chip">{color?.label ?? scene.kind}</span>
        </div>
        <span className="chip">
          {scene.duration_s.toFixed(1)}s · {dims.width}×{dims.height}
        </span>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-2 text-xs">
          {scene.headline ? (
            <p>
              <span className="label !mb-0.5">Headline</span>
              <span className="text-sm font-bold text-ivory">{scene.headline}</span>
            </p>
          ) : null}
          {scene.body ? (
            <p>
              <span className="label !mb-0.5">Body</span>
              <span className="text-ivory/80">{scene.body}</span>
            </p>
          ) : null}
          {scene.narration ? (
            <p>
              <span className="label !mb-0.5">Narration</span>
              <span className="italic text-ivory/75">“{scene.narration}”</span>
            </p>
          ) : null}
        </div>
        <div className="space-y-2 text-xs">
          {scene.visual_prompt ? (
            <p>
              <span className="label !mb-0.5">Visual prompt</span>
              <span className="font-mono text-[11px] leading-relaxed text-accent/90">
                {scene.visual_prompt}
              </span>
            </p>
          ) : null}
          <div className="flex flex-wrap gap-1.5 pt-1">
            <span className="chip font-mono">
              motion: {scene.motion.style} @ {scene.motion.intensity.toFixed(2)}
            </span>
            <span className="chip font-mono">in: {scene.transition_in}</span>
          </div>
        </div>
      </div>

      {!durationOk ? (
        <p className="text-[11px] text-amber-300">
          Note: scene durations deviate more than ±10% from the target — the contract expects them close.
        </p>
      ) : null}
    </div>
  );
}

export function TimelineView({ assets, onOpenPreview }: { assets: Asset[]; onOpenPreview: () => void }) {
  const sbAsset = latestAsset(assets, 'storyboard');
  const [sb, setSb] = useState<Storyboard | null>(null);
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      if (!sbAsset) {
        setSb(null);
        return;
      }
      // Inline storyboard JSON takes precedence (no extra fetch); else fetch the file.
      if (sbAsset.meta?.storyboard) {
        setSb(parseStoryboard(sbAsset.meta.storyboard));
        return;
      }
      try {
        const res = await fetch(assetFileUrl(sbAsset));
        const raw: unknown = await res.json();
        if (!cancelled) setSb(parseStoryboard(raw));
      } catch {
        if (!cancelled) setSb(null);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [sbAsset]);

  const lanes = useMemo(() => (sb ? storyboardLanes(sb) : []), [sb]);
  const total = useMemo(() => (sb ? sb.scenes.reduce((a, s) => a + s.duration_s, 0) : 0), [sb]);
  const selectedScene = sb?.scenes.find((s) => s.id === selected) ?? null;
  const outDims = sb ? aspectDimensions(sb.aspect) : { width: 0, height: 0 };

  if (!sb) {
    return (
      <EmptyState
        title="No storyboard yet"
        hint="The director writes the storyboard (the program's blueprint) in chat. It shows up here as scene tracks."
      />
    );
  }

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto pr-1">
      {/* Program meta */}
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="chip !border-forge/30 !text-ivory">▸ {sb.title}</span>
        <span className="chip font-mono">{sb.aspect}</span>
        <span className="chip">{sb.fps} fps</span>
        <span className="chip">{total.toFixed(1)}s / target {sb.duration_target_s}s</span>
        <span className="chip font-mono !text-accent/90">mood: {sb.music_mood}</span>
        <span className="chip">{sb.scenes.length} scenes</span>
      </div>

      {/* Track area */}
      <div className="panel overflow-hidden p-0">
        <div className="px-4 pt-3">
          <Ruler total={total} />
        </div>
        <div className="space-y-2.5 p-4">
          {lanes.map((lane) => (
            <div key={lane.id} className="flex items-center gap-3">
              <span className="w-20 shrink-0 text-right text-[10px] font-bold uppercase tracking-wider text-muted">
                {lane.label}
              </span>
              <div className="relative h-8 flex-1 overflow-hidden rounded-md bg-ink/70">
                {lane.clips.length === 0 ? (
                  <span className="absolute inset-0 flex items-center justify-center text-[10px] text-muted/60">
                    —
                  </span>
                ) : (
                  lane.clips.map((clip) => {
                    const color = SCENE_KIND_COLORS[clip.scene.kind];
                    const active = selected === clip.scene.id;
                    return (
                      <button
                        key={`${lane.id}-${clip.scene.id}`}
                        onClick={() => {
                          setSelected(clip.scene.id);
                          if (lane.id === 'video') onOpenPreview();
                        }}
                        title={`${clip.scene.id} · ${clip.scene.duration_s.toFixed(1)}s`}
                        className={`absolute top-0 h-full overflow-hidden border border-black/40 px-1.5 text-left transition
                          ${color?.bar ?? 'bg-white/20'} ${active ? 'ring-2 ring-accent' : 'hover:brightness-125'}
                          ${lane.id === 'narration' ? 'top-2 h-4 rounded-sm bg-emerald-400/40' : ''}
                          ${lane.id === 'captions' ? 'top-2 h-4 rounded-sm bg-amber-300/30' : ''}`}
                        style={{
                          left: `${(clip.startS / total) * 100}%`,
                          width: `${(clip.scene.duration_s / total) * 100}%`,
                        }}
                      >
                        <span className="block truncate text-[9px] font-bold text-black/80">
                          {lane.id === 'video' ? clip.scene.kind : lane.id === 'captions' ? clip.scene.headline : 'voice'}
                        </span>
                      </button>
                    );
                  })
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Inspector */}
      {selectedScene ? (
        <SceneInspector scene={selectedScene} durationOk={storyboardDurationOk(sb)} dims={outDims} />
      ) : (
        <p className="text-center text-[11px] text-muted">
          Select a clip to inspect the scene (headline, narration, visual prompt, motion, transition).
        </p>
      )}
    </div>
  );
}
