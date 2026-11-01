/**
 * CINEFORGE API contract mirror — `docs/API_CONTRACTS.md` v0.1.
 *
 * Keep in sync with:
 *  - docs/API_CONTRACTS.md (binding)
 *  - packages/timeline/src/index.ts (shared storyboard model)
 *  - backend/app/schemas.py (Python mirror, agent-03)
 * Any contract change ships in the same PR across all mirrors (ADR-0007).
 */

/**
 * Scene-level types: local mirror of `@cineforge/timeline` (packages/timeline/src/index.ts).
 * Deliberately copied (not imported) so apps/web builds standalone in any environment —
 * keep the two files in sync in the same PR (ADR-0007 contract discipline).
 */

export type Platform = 'instagram' | 'youtube' | 'tiktok' | 'web';

/** Scene kinds drive renderer styling and the timeline track colors. */
export type SceneKind = 'hook' | 'reveal' | 'typography' | 'outro';

export type MotionStyle = 'ken-burns' | 'slide' | 'zoom' | 'reveal';
export type TransitionIn = 'fade' | 'cut' | 'slide';

export interface SceneMotion {
  style: MotionStyle;
  /** 0..1 — how strongly the motion is applied. */
  intensity: number;
}

export interface Scene {
  id: string;
  kind: SceneKind;
  /** Seconds. `sum(scenes[].duration_s)` ≈ `duration_target_s` (±10%). */
  duration_s: number;
  headline?: string;
  body?: string;
  narration?: string;
  visual_prompt?: string;
  motion: SceneMotion;
  transition_in: TransitionIn;
}

export type ProjectStatus = 'draft' | 'generating' | 'ready' | 'failed';
export type JobStatus = 'pending' | 'running' | 'done' | 'failed';
export type JobKind = 'render' | 'generate' | 'analyze';
export type AssetKind = 'storyboard' | 'frame' | 'audio' | 'video' | 'analysis' | 'project';
export type MessageRole = 'user' | 'assistant' | 'system';

export interface Project {
  id: string;
  title: string;
  brief: string;
  style?: string;
  platform?: Platform;
  duration_hint_s?: number;
  status: ProjectStatus;
  created_at: string;
}

export interface Message {
  id: string;
  project_id: string;
  role: MessageRole;
  content: string;
  meta?: {
    plan?: string[];
    tools_used?: string[];
    llm_provider?: string;
    [k: string]: unknown;
  };
  created_at: string;
}

export interface Asset {
  id: string;
  project_id: string;
  kind: AssetKind;
  filename: string;
  /** Server-side storage path (opaque to the UI; files are served via /api/assets/{id}/file). */
  path: string;
  meta?: {
    provider?: string;
    duration_s?: number;
    width?: number;
    height?: number;
    fps?: number;
    prompt?: string;
    scenes?: number;
    storyboard?: Storyboard;
    [k: string]: unknown;
  };
  created_at: string;
}

export interface Job {
  id: string;
  project_id: string;
  kind: JobKind;
  status: JobStatus;
  /** 0.0 – 1.0 */
  progress: number;
  result?: Record<string, unknown>;
  error?: string | null;
}

export interface ProjectDetail {
  project: Project;
  messages: Message[];
  assets: Asset[];
  jobs: Job[];
}

export interface ChatResponse {
  user_message: Message;
  assistant_message: Message;
  /** Newly created artifacts (storyboard, frames, audio, video, project). */
  assets: Asset[];
  /** Long operations surfaced as jobs; poll GET /api/jobs/{id}. */
  jobs: Job[];
}

/** GET /health */
export interface Health {
  status: string;
  version: string;
  /** capability -> provider ids, ordered by availability in the current env (first = active). */
  providers: Partial<Record<ProviderCapability, string[]>>;
  storage_root: string;
}

export type ProviderCapability = 'llm' | 'image' | 'tts' | 'stt' | 'music' | 'video';

/** The director's central artifact (schema_version 1) — mirror of @cineforge/timeline. */
export interface Storyboard {
  schema_version: 1;
  title: string;
  platform: Platform;
  aspect: string;
  fps: number;
  duration_target_s: number;
  palette: { bg: string; primary: string; accent: string; text: string };
  music_mood: string;
  scenes: Scene[];
}

export interface CreateProjectInput {
  title: string;
  brief: string;
  style?: string;
  platform?: Platform;
  duration_hint_s?: number;
}

export interface SendChatInput {
  message: string;
}
