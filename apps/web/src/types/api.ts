/**
 * TypeScript mirror of `docs/API_CONTRACTS.md` v0.1.
 * Keep in sync with the contract — changes there require changes here (and vice versa).
 */

// ── Projects ────────────────────────────────────────────────────────────────

export type ProjectStatus = "draft" | "generating" | "ready" | "failed";

export type Platform = "instagram" | "youtube" | "tiktok" | "web";

export interface Project {
  id: string;
  title: string;
  brief: string;
  style?: string | null;
  platform?: string | null;
  status: ProjectStatus;
  created_at: string;
}

export interface CreateProjectBody {
  title: string;
  brief: string;
  /** optional: e.g. "cinematic-dark" */
  style?: string;
  /** optional: instagram | youtube | tiktok | web */
  platform?: string;
  /** optional */
  duration_hint_s?: number;
}

// ── Messages ────────────────────────────────────────────────────────────────

export type MessageRole = "user" | "assistant" | "system";

export interface MessageMeta {
  /** Ordered director plan produced before execution (assistant messages). */
  plan?: string[];
  /** Tool names the director invoked (e.g. write_storyboard, render_slideshow). */
  tools_used?: string[];
  /** Which LLM provider answered (mock | openai | anthropic | zai | …). */
  llm_provider?: string;
  /** True when this turn was a revision of earlier output. */
  revision?: boolean;
  [key: string]: unknown;
}

export interface Message {
  id: string;
  project_id: string;
  role: MessageRole;
  content: string;
  meta?: MessageMeta | null;
  created_at: string;
}

// ── Assets ──────────────────────────────────────────────────────────────────

export type AssetKind = "storyboard" | "frame" | "audio" | "video" | "analysis" | "project";

export interface AssetMeta {
  provider?: string;
  duration_s?: number;
  width?: number;
  height?: number;
  fps?: number;
  prompt?: string;
  /** Frame picked as the video poster. */
  poster?: boolean;
  /** Audio asset is the music bed (vs. narration). */
  music?: boolean;
  [key: string]: unknown;
}

export interface Asset {
  id: string;
  project_id: string;
  kind: AssetKind;
  filename: string;
  path: string;
  meta?: AssetMeta | null;
  created_at: string;
}

// ── Jobs ────────────────────────────────────────────────────────────────────

export type JobStatus = "pending" | "running" | "done" | "failed";

export type JobKind = "render" | "generate" | "analyze";

export interface Job {
  id: string;
  project_id: string;
  kind: JobKind;
  status: JobStatus;
  /** 0.0 – 1.0 */
  progress: number;
  result?: Record<string, unknown> | null;
  error?: string | null;
  created_at?: string;
}

// ── Aggregate payloads ──────────────────────────────────────────────────────

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
  jobs: Job[];
}

// ── Health ──────────────────────────────────────────────────────────────────

export interface Health {
  status: string;
  version: string;
  /** capability → ordered provider chain, e.g. { llm: ["zai","openai","mock"], … } */
  providers: Record<string, string[]>;
  storage_root: string;
}

// ── Storyboard (schema_version 1) — the director's central artifact ─────────

export interface StoryboardPalette {
  bg: string;
  primary: string;
  accent: string;
  text: string;
}

export type SceneKind = "hook" | "reveal" | "typography" | "outro";

export interface SceneMotion {
  style: string;
  /** 0..1 */
  intensity: number;
}

export interface Scene {
  id: string;
  kind: SceneKind;
  duration_s: number;
  headline: string;
  body?: string;
  narration?: string;
  visual_prompt: string;
  motion: SceneMotion;
  transition_in: string;
}

export interface Storyboard {
  schema_version: 1;
  title: string;
  platform: string;
  aspect: string;
  fps: number;
  duration_target_s: number;
  palette: StoryboardPalette;
  music_mood: string;
  scenes: Scene[];
}
