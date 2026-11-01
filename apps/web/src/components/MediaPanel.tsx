'use client';

import { api } from '@/lib/api';
import type { ProjectDetail } from '@/types/api';

const GROUPS: { kind: string; label: string }[] = [
  { kind: 'video', label: 'Video' },
  { kind: 'frame', label: 'Concept frames' },
  { kind: 'audio', label: 'Audio' },
  { kind: 'storyboard', label: 'Storyboard' },
  { kind: 'project', label: 'Editable projects' },
  { kind: 'analysis', label: 'Analysis' },
];

export default function MediaPanel({ detail }: { detail: ProjectDetail }) {
  const groups = GROUPS.map((g) => ({
    ...g,
    assets: detail.assets.filter((a) => a.kind === g.kind),
  })).filter((g) => g.assets.length > 0);

  if (groups.length === 0) {
    return <p className="p-4 text-xs text-slate-500">Media appears here as the director works.</p>;
  }

  return (
    <div className="space-y-5 pb-4">
      {groups.map((g) => (
        <div key={g.kind}>
          <h3 className="mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">
            {g.label} · {g.assets.length}
          </h3>
          {g.kind === 'frame' ? (
            <div className="grid grid-cols-3 gap-2 sm:grid-cols-5">
              {g.assets.map((a) => (
                <figure key={a.id} className="panel overflow-hidden">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={api.assetUrl(a.id)} alt={a.meta.prompt as string ?? a.filename}
                       className="aspect-[9/16] w-full object-cover" loading="lazy" />
                  <figcaption className="truncate px-1.5 py-1 text-[9px] text-slate-500">
                    {String(a.meta.scene_id ?? a.filename)} · {String(a.meta.provider ?? '')}
                  </figcaption>
                </figure>
              ))}
            </div>
          ) : (
            <div className="space-y-1.5">
              {g.assets.map((a) => (
                <div key={a.id} className="panel flex items-center justify-between px-3 py-2 text-xs">
                  <div className="min-w-0">
                    <p className="truncate font-medium text-slate-300">{a.filename}</p>
                    <p className="text-[10px] text-slate-500">
                      {typeof a.meta.duration_s === 'number' ? `${a.meta.duration_s.toFixed?.(1) ?? a.meta.duration_s}s · ` : ''}
                      {String(a.meta.provider ?? a.meta.template ?? 'artifact')}
                    </p>
                  </div>
                  <a href={api.assetUrl(a.id)} target="_blank" rel="noreferrer"
                     className="btn-ghost !px-2 !py-1 text-[11px]">open</a>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
