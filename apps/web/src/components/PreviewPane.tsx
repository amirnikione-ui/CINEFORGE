'use client';

import { api } from '@/lib/api';
import type { Job } from '@/types/api';

export default function PreviewPane({ assetId, job }: { assetId: string | null; job: Job | null }) {
  const url = assetId ? api.assetUrl(assetId) : null;
  return (
    <div className="panel relative flex min-h-[260px] flex-1 items-center justify-center overflow-hidden bg-black/60">
      {url ? (
        <video key={url} src={url} controls autoPlay loop className="max-h-full max-w-full" />
      ) : (
        <div className="p-10 text-center text-sm text-slate-500">
          {job ? (
            <>
              <div className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-2 border-forge-500 border-t-transparent" />
              Rendering… {Math.round((job.progress ?? 0) * 100)}%
            </>
          ) : (
            <>🎬 Your final cut will appear here after the first render.</>
          )}
        </div>
      )}
      {url && (
        <div className="pointer-events-none absolute left-3 top-3 pill border-neon/40 text-neon">
          final cut
        </div>
      )}
    </div>
  );
}
