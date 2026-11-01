/**
 * Storyboard helpers used by the studio UI.
 * Mirror of `@cineforge/timeline` helpers (packages/timeline/src/index.ts) — keep in sync.
 */
import type { Scene, SceneKind, Storyboard } from '@/types/api';

export const SCENE_KINDS: SceneKind[] = ['hook', 'reveal', 'typography', 'outro'];

export function storyboardDuration(sb: Storyboard): number {
  return sb.scenes.reduce((acc, s) => acc + s.duration_s, 0);
}

/** Contract rule: scenes must sum to duration_target_s within ±10%. */
export function storyboardDurationOk(sb: Storyboard): boolean {
  const target = sb.duration_target_s || 0;
  if (target <= 0) return false;
  return Math.abs(storyboardDuration(sb) - target) <= target * 0.1;
}

export function platformAspect(platform: Storyboard['platform']): string {
  switch (platform) {
    case 'instagram':
    case 'tiktok':
      return '9:16';
    case 'youtube':
      return '16:9';
    default:
      return '16:9';
  }
}

export function aspectDimensions(aspect: string): { width: number; height: number } {
  switch (aspect) {
    case '9:16':
      return { width: 1080, height: 1920 };
    case '1:1':
      return { width: 1080, height: 1080 };
    case '4:5':
      return { width: 1080, height: 1350 };
    default:
      return { width: 1920, height: 1080 };
  }
}

export interface LaneClip {
  scene: Scene;
  startS: number;
}

export interface Lane {
  id: 'video' | 'narration' | 'captions';
  label: string;
  clips: LaneClip[];
}

/** Derive timeline lane layouts (with start offsets) from a storyboard. */
export function storyboardLanes(sb: Storyboard): Lane[] {
  let t = 0;
  const video: LaneClip[] = [];
  const narration: LaneClip[] = [];
  const captions: LaneClip[] = [];
  for (const s of sb.scenes) {
    video.push({ scene: s, startS: t });
    if (s.narration) narration.push({ scene: s, startS: t });
    if (s.headline) captions.push({ scene: s, startS: t });
    t += s.duration_s;
  }
  return [
    { id: 'video', label: 'Video', clips: video },
    { id: 'narration', label: 'Narration', clips: narration },
    { id: 'captions', label: 'Captions', clips: captions },
  ];
}

/** Defensive parse of a storyboard JSON payload. */
export function parseStoryboard(raw: unknown): Storyboard | null {
  if (!raw || typeof raw !== 'object') return null;
  const sb = raw as Storyboard;
  if (sb.schema_version !== 1 || !Array.isArray(sb.scenes) || sb.scenes.length === 0) return null;
  return sb;
}
