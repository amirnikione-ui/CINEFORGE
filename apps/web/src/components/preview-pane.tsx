'use client';

import { assetFileUrl, latestAsset } from '@/lib/api';
import type { Asset } from '@/types/api';
import { dims, secs } from '@/lib/format';
import { EmptyState } from '@/components/ui';

export function PreviewPane({ assets }: { assets: Asset[] }) {
  const video = latestAsset(assets, 'video');

  if (!video) {
    return (
      <EmptyState
        title="No render yet"
        hint="Once the director renders a cut, the live preview appears here. Ask the agent in chat to produce the first version."
      />
    );
  }

  const meta = video.meta ?? {};
  return (
    <div className="flex h-full flex-col gap-4">
      <div className="flex flex-1 items-center justify-center overflow-hidden rounded-xl border border-line bg-black/60">
        <video
          key={video.id}
          src={assetFileUrl(video)}
          controls
          autoPlay
          loop
          playsInline
          className="max-h-full max-w-full"
        />
      </div>
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="chip">▢ {video.filename}</span>
        {meta.provider ? <span className="chip">provider: {meta.provider}</span> : null}
        {meta.duration_s !== undefined ? <span className="chip">⏱ {secs(meta.duration_s)}</span> : null}
        <span className="chip">
          {dims(meta as { width?: number; height?: number })}
        </span>
        {meta.fps ? <span className="chip">{meta.fps} fps</span> : null}
      </div>
    </div>
  );
}
