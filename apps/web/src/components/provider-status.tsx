'use client';

import type { Health, ProviderCapability } from '@/types/api';

const CAP_META: Record<ProviderCapability, { label: string; hint: string }> = {
  llm: { label: 'Language models', hint: 'Planning, scripting, brief parsing' },
  image: { label: 'Image generation', hint: 'Concept frames & scene visuals' },
  tts: { label: 'Text-to-speech', hint: 'Narration voice-overs' },
  stt: { label: 'Speech-to-text', hint: 'Transcription & subtitles' },
  music: { label: 'Music', hint: 'Score & mood beds' },
  video: { label: 'Video', hint: 'Direct video generation providers' },
};

/**
 * Provider/panel per the v0.1 contract: /health returns per-capability provider
 * chains "ordered by availability" — the first entry is the active provider,
 * the rest are configured fallbacks.
 */
export function ProviderStatus({ health }: { health: Health | null }) {
  if (!health) {
    return (
      <div className="rounded-lg border border-rose-500/25 bg-rose-500/10 p-4 text-xs text-rose-200">
        Provider status unavailable — the backend is offline.
      </div>
    );
  }

  const caps = Object.keys(CAP_META) as ProviderCapability[];

  return (
    <div className="h-full space-y-3 overflow-y-auto pr-1">
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="chip !border-emerald-400/30 !text-emerald-300">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" /> backend {health.status}
        </span>
        <span className="chip font-mono">v{health.version}</span>
        <span className="chip font-mono" title="server-side storage root">
          storage: {health.storage_root}
        </span>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {caps.map((cap) => {
          const chain = health.providers?.[cap] ?? [];
          const active = chain[0];
          const meta = CAP_META[cap];
          return (
            <div key={cap} className="panel p-4">
              <div className="mb-1 flex items-center justify-between">
                <h3 className="text-sm font-bold">{meta.label}</h3>
                <span
                  className={`h-2 w-2 rounded-full ${active ? 'bg-emerald-400' : 'bg-white/20'}`}
                  title={active ? 'active' : 'no provider available'}
                />
              </div>
              <p className="mb-2 text-[11px] text-muted">{meta.hint}</p>
              <div className="flex flex-wrap gap-1.5">
                {chain.length === 0 ? (
                  <span className="chip !text-[10px] !text-muted/70">no providers configured</span>
                ) : (
                  chain.map((p, i) => (
                    <span
                      key={p}
                      className={`chip !text-[10px] font-mono ${
                        i === 0 ? '!border-accent/40 !text-accent' : '!text-ivory/50'
                      }`}
                      title={i === 0 ? 'active provider' : 'standby (fallback chain)'}
                    >
                      {i === 0 ? '▶' : '·'} {p}
                    </span>
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>

      <p className="text-[11px] leading-relaxed text-muted">
        Chains are environment-driven (ADR-0004): the first available provider serves each
        capability and failures fall through to the next — the pipeline never depends on a single
        vendor.
      </p>
    </div>
  );
}
