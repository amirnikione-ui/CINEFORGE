'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { createProject, API_URL } from '@/lib/api';
import type { Platform } from '@/types/api';
import { Modal, Spinner } from '@/components/ui';

const STYLES = ['cinematic-dark', 'vibrant-pop', 'minimal-clean', 'retro-film', 'corporate'];
const PLATFORMS: Array<{ id: Platform; label: string }> = [
  { id: 'instagram', label: 'Instagram (9:16)' },
  { id: 'youtube', label: 'YouTube (16:9)' },
  { id: 'tiktok', label: 'TikTok (9:16)' },
  { id: 'web', label: 'Web (16:9)' },
];
const DURATIONS = [15, 30, 45, 60];

const EXAMPLE_BRIEF =
  'A 30s cinematic promo for a product launch. Dark mood, English narration, professional motion graphics, Instagram output.';

export function NewProjectDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const router = useRouter();
  const [title, setTitle] = useState('');
  const [brief, setBrief] = useState('');
  const [style, setStyle] = useState(STYLES[0]);
  const [platform, setPlatform] = useState<Platform>('instagram');
  const [duration, setDuration] = useState(30);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const project = await createProject({
        title: title.trim() || 'Untitled production',
        brief: brief.trim() || EXAMPLE_BRIEF,
        style,
        platform,
        duration_hint_s: duration,
      });
      router.push(`/projects/${project.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create project');
      setBusy(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="New production">
      <form onSubmit={submit} className="space-y-4">
        <div>
          <label className="label" htmlFor="np-title">
            Title
          </label>
          <input
            id="np-title"
            className="input"
            placeholder="Nova Runners launch promo"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            autoFocus
          />
        </div>

        <div>
          <label className="label" htmlFor="np-brief">
            Creative brief — describe the video; the director agent plans the rest
          </label>
          <textarea
            id="np-brief"
            className="input min-h-[110px] resize-y"
            placeholder={EXAMPLE_BRIEF}
            value={brief}
            onChange={(e) => setBrief(e.target.value)}
          />
          <p className="mt-1.5 text-[11px] text-muted">
            Persian or English. Example: «یک ویدیوی تبلیغاتی سینمایی ۳۰ ثانیه‌ای، فضای دارک، نریشن انگلیسی، خروجی اینستاگرام»
          </p>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label" htmlFor="np-style">
              Style
            </label>
            <select id="np-style" className="input" value={style} onChange={(e) => setStyle(e.target.value)}>
              {STYLES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="np-platform">
              Platform
            </label>
            <select
              id="np-platform"
              className="input"
              value={platform}
              onChange={(e) => setPlatform(e.target.value as Platform)}
            >
              {PLATFORMS.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <span className="label">Target duration</span>
          <div className="flex gap-2">
            {DURATIONS.map((d) => (
              <button
                type="button"
                key={d}
                onClick={() => setDuration(d)}
                className={`flex-1 rounded-lg border px-2 py-1.5 text-sm font-semibold transition ${
                  duration === d
                    ? 'border-forge/60 bg-forge/20 text-ivory shadow-glow'
                    : 'border-line bg-white/5 text-muted hover:bg-white/10'
                }`}
              >
                {d}s
              </button>
            ))}
          </div>
        </div>

        {error ? <p className="text-xs text-rose-300">{error}</p> : null}

        <div className="flex items-center justify-between pt-2">
          <span className="font-mono text-[10px] text-muted/70">{API_URL}</span>
          <div className="flex gap-2">
            <button type="button" className="btn-ghost" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={busy}>
              {busy ? <Spinner /> : null}
              {busy ? 'Creating…' : 'Create & open studio'}
            </button>
          </div>
        </div>
      </form>
    </Modal>
  );
}
