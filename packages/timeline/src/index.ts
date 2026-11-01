/**
 * @cineforge/timeline — shared Storyboard/Timeline data model.
 *
 * MIRROR of `docs/API_CONTRACTS.md` v0.1 ("Storyboard JSON (schema_version 1)").
 * This package is the canonical TS source; `apps/web/src/types/api.ts` re-mirrors it for
 * the app bundle. Keep all three in sync in the same PR (docs + package + app mirror).
 * Renderer implementations (FFmpeg toolkit, Remotion template) MUST accept this shape verbatim.
 */

export const STORYBOARD_SCHEMA_VERSION = 1 as const;

export type Platform = 'instagram' | 'youtube' | 'tiktok' | 'web';

/** Scene kinds drive renderer styling and the timeline track colors. */
export type SceneKind = 'hook' | 'reveal' | 'typography' | 'outro';

/** Motion style applied to the scene's visual. */
export type MotionStyle = 'ken-burns' | 'slide' | 'zoom' | 'reveal';

/** Scene transition. */
export type TransitionIn = 'fade' | 'cut' | 'slide';

export interface SceneMotion {
  style: MotionStyle;
  /** 0..1 — how strongly the motion is applied (zoom reach, pan distance, etc). */
  intensity: number;
}

export interface Scene {
  id: string;
  kind: SceneKind;
  /** Seconds. `sum(scenes[].duration_s)` ≈ `duration_target_s` (±10%). */
  duration_s: number;
  /** Main on-screen text (also used as the captions lane source). */
  headline?: string;
  /** Optional supporting line. */
  body?: string;
  /** Voice-over script for this scene (consumed by the narration tool). */
  narration?: string;
  /** Text-to-image prompt describing this scene's visual. */
  visual_prompt?: string;
  motion: SceneMotion;
  transition_in: TransitionIn;
}

export interface Palette {
  bg: string;
  primary: string;
  accent: string;
  text: string;
}

/** The director's central artifact — a whole video program in one JSON document. */
export interface Storyboard {
  schema_version: typeof STORYBOARD_SCHEMA_VERSION;
  title: string;
  platform: Platform;
  /** Target aspect, e.g. "9:16" | "16:9" | "1:1". */
  aspect: string;
  fps: number;
  duration_target_s: number;
  palette: Palette;
  /** Free-form mood tag consumed by the music tool, e.g. "dark-cinematic". */
  music_mood: string;
  scenes: Scene[];
}

export interface StoryboardAssetMeta {
  provider?: string;
  prompt?: string;
  duration_s?: number;
  width?: number;
  height?: number;
  fps?: number;
  scenes?: number;
  [k: string]: unknown;
}

/** Sum of scene durations (what the renderer will actually produce). */
export function storyboardDuration(sb: Storyboard): number {
  return sb.scenes.reduce((acc, s) => acc + s.duration_s, 0);
}

/** Contract rule: scenes must sum to duration_target_s within ±10%. */
export function storyboardDurationOk(sb: Storyboard): boolean {
  const target = sb.duration_target_s || 0;
  if (target <= 0) return false;
  const actual = storyboardDuration(sb);
  return Math.abs(actual - target) <= target * 0.1;
}

/** Pixel dimensions for a platform/aspect pair (renderer + preview sizing). */
export function aspectDimensions(aspect: string): { width: number; height: number } {
  switch (aspect) {
    case '9:16':
      return { width: 1080, height: 1920 };
    case '1:1':
      return { width: 1080, height: 1080 };
    case '4:5':
      return { width: 1080, height: 1350 };
    case '16:9':
    default:
      return { width: 1920, height: 1080 };
  }
}

export function platformAspect(platform: Platform): string {
  switch (platform) {
    case 'instagram':
      return '9:16';
    case 'tiktok':
      return '9:16';
    case 'youtube':
      return '16:9';
    case 'web':
    default:
      return '16:9';
  }
}

/** Timeline-lane view model used by the studio UI (video / narration / captions lanes). */
export interface TimelineLane {
  id: 'video' | 'narration' | 'captions';
  label: string;
  clips: Array<{
    sceneId: string;
    startS: number;
    durationS: number;
    label: string;
    kind?: SceneKind;
  }>;
}

/** Derive lane clip layouts (start offsets) from a storyboard. */
export function storyboardLanes(sb: Storyboard): TimelineLane[] {
  let t = 0;
  const video: TimelineLane['clips'] = [];
  const narration: TimelineLane['clips'] = [];
  const captions: TimelineLane['clips'] = [];
  for (const s of sb.scenes) {
    video.push({ sceneId: s.id, startS: t, durationS: s.duration_s, label: s.kind, kind: s.kind });
    if (s.narration) narration.push({ sceneId: s.id, startS: t, durationS: s.duration_s, label: 'voice' });
    if (s.headline) captions.push({ sceneId: s.id, startS: t, durationS: s.duration_s, label: s.headline });
    t += s.duration_s;
  }
  return [
    { id: 'video', label: 'Video', clips: video },
    { id: 'narration', label: 'Narration', clips: narration },
    { id: 'captions', label: 'Captions', clips: captions },
  ];
}
