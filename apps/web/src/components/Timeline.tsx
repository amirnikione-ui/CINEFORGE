'use client';

// Timeline v1 — storyboard scenes as proportional blocks.
// Interactive multi-track editing (drag/trim/split) is CF-051 / M4 (owner agent-02+04).
import { useEffect, useMemo, useRef, useState } from 'react';
import { api } from '@/lib/api';
import type { ProjectDetail, Storyboard } from '@/types/api';

const KIND_COLORS: Record<string, string> = {
  hook: 'from-forge-600/70 to-forge-500/40 border-forge-500/50',
  reveal: 'from-neon/40 to-forge-500/30 border-neon/40',
  typography: 'from-ink-600 to-ink-700 border-ink-600',
  outro: 'from-emerald-600/50 to-ink-700 border-emerald-500/30',
};

export default function Timeline({ detail }: { detail: ProjectDetail }) {
  const sbAsset = useMemo(
    () => detail.assets.find((a) => a.kind === 'storyboard'),
    [detail.assets],
  );
  const [sb, setSb] = useState<Storyboard | null>(null);
  const lastSb = useRef<string | null>(null);

  useEffect(() => {
    if (!sbAsset) return;
    if (lastSb.current === sbAsset.id) return;
    lastSb.current = sbAsset.id;
    void fetch(api.assetUrl(sbAsset.id))
      .then((r) => r.json())
      .then((data: Storyboard) => setSb(data.schema_version === 1 ? data : null))
      .catch(() => setSb(null));
  }, [sbAsset]);

  if (!sb) {
    return (
      <div className="panel p-4 text-xs text-slate-500">
        Timeline appears once the storyboard is written.
      </div>
    );
  }

  const total = sb.scenes.reduce((a, s) => a + s.duration_s, 0) || 1;
  return (
    <div className="panel p-3">
      <div className="mb-2 flex items-center justify-between text-[10px] uppercase tracking-wider text-slate-500">
        <span>Timeline · {sb.title}</span>
        <span>{sb.scenes.length} scenes · {total.toFixed(1)}s · {sb.aspect} · {sb.music_mood}</span>
      </div>
      <div className="flex h-14 gap-0.5 overflow-hidden rounded-lg">
        {sb.scenes.map((s) => (
          <div key={s.id}
               title={`${s.kind}: ${s.headline ?? ''} (${s.duration_s}s, ${s.motion.style})`}
               style={{ flexGrow: s.duration_s }}
               className={`relative flex min-w-0 flex-col justify-center border bg-gradient-to-br px-2 ${KIND_COLORS[s.kind] ?? KIND_COLORS.typography}`}>
            <span className="truncate text-[10px] font-bold text-white/90">{s.headline || s.kind}</span>
            <span className="truncate text-[9px] text-white/60">
              {s.duration_s}s · {s.motion.style} · {s.transition_in}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
