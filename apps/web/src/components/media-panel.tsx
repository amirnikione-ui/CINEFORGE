'use client';

import { assetDownloadUrl, assetFileUrl } from '@/lib/api';
import type { Asset, AssetKind } from '@/types/api';
import { dims, secs } from '@/lib/format';
import { EmptyState, KindIcon } from '@/components/ui';

const GROUPS: Array<{ kind: AssetKind; label: string }> = [
  { kind: 'video', label: 'Video' },
  { kind: 'frame', label: 'Frames' },
  { kind: 'audio', label: 'Audio' },
  { kind: 'storyboard', label: 'Storyboards' },
  { kind: 'project', label: 'Projects' },
  { kind: 'analysis', label: 'Analysis' },
];

export function MediaPanel({ assets, onOpenPreview }: { assets: Asset[]; onOpenPreview: () => void }) {
  if (assets.length === 0) {
    return (
      <EmptyState
        title="Media library is empty"
        hint="Everything the agent produces — storyboards, frames, narration, music, final cuts — lands here."
      />
    );
  }

  return (
    <div className="h-full space-y-5 overflow-y-auto pr-1">
      {GROUPS.map(({ kind, label }) => {
        const group = assets.filter((a) => a.kind === kind);
        if (group.length === 0) return null;
        return (
          <div key={kind}>
            <h3 className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-muted">
              {label}
              <span className="rounded-full bg-white/10 px-1.5 text-[10px] text-ivory/70">{group.length}</span>
            </h3>
            <div className="space-y-2">
              {group.map((a) => (
                <div
                  key={a.id}
                  className="flex items-center gap-3 rounded-lg border border-line bg-ink/40 px-3 py-2.5 transition hover:border-forge/30"
                >
                  <span className="text-forge">
                    <KindIcon kind={a.kind} />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-xs font-semibold text-ivory/90">{a.filename}</p>
                    <div className="mt-0.5 flex flex-wrap gap-1">
                      {a.meta?.provider ? (
                        <span className="chip !px-1.5 !py-0 !text-[9px]">{a.meta.provider}</span>
                      ) : null}
                      {a.meta?.duration_s !== undefined ? (
                        <span className="chip !px-1.5 !py-0 !text-[9px]">{secs(a.meta.duration_s)}</span>
                      ) : null}
                      {a.meta?.width ? (
                        <span className="chip !px-1.5 !py-0 !text-[9px]">
                          {dims(a.meta as { width?: number; height?: number })}
                        </span>
                      ) : null}
                      {a.meta?.scenes ? (
                        <span className="chip !px-1.5 !py-0 !text-[9px]">{a.meta.scenes} scenes</span>
                      ) : null}
                    </div>
                  </div>
                  <div className="flex shrink-0 gap-1.5">
                    {a.kind === 'video' ? (
                      <button className="btn-ghost !px-2 !py-1 text-[10px]" onClick={onOpenPreview}>
                        Watch
                      </button>
                    ) : null}
                    {a.kind === 'storyboard' || a.kind === 'project' ? (
                      <a className="btn-ghost !px-2 !py-1 text-[10px]" href={assetFileUrl(a)} target="_blank" rel="noreferrer">
                        Open
                      </a>
                    ) : null}
                    <a className="btn-ghost !px-2 !py-1 text-[10px]" href={assetDownloadUrl(a)}>
                      Save
                    </a>
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
