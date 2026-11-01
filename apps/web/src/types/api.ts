// TypeScript mirror of docs/API_CONTRACTS.md (v0.1) — keep in sync per rule CF-003.
export type Platform = 'instagram' | 'youtube' | 'tiktok' | 'web';
export type AssetKind = 'storyboard' | 'frame' | 'audio' | 'video' | 'analysis' | 'project';
export type JobKind = 'render' | 'generate' | 'analyze';
export type JobStatus = 'pending' | 'running' | 'done' | 'failed';

export interface Project {
  id: string;
  title: string;
  brief: string;
  style: string;
  platform: string;
  duration_hint_s: number;
  status: 'draft' | 'generating' | 'ready' | 'failed';
  created_at: string;
}

export interface Asset {
  id: string;
  project_id: string;
  kind: AssetKind;
  filename: string;
  path: string;
  meta: Record<string, unknown>;
  created_at: string;
}

export interface Message {
  id: string;
  project_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  meta: {
    plan?: { step: string; strategy?: string; provider?: string; note?: string; reason?: string }[];
    tools_used?: { tool: string; provider: string; summary: string; ok: boolean }[];
    llm_provider?: string;
    job_id?: string;
    warnings?: string[];
  };
  created_at: string;
}

export interface Job {
  id: string;
  project_id: string;
  kind: JobKind;
  status: JobStatus;
  progress: number;
  result: { asset_id?: string; duration_s?: number; width?: number; height?: number; report?: unknown };
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectDetail {
  project: Project;
  messages: Message[];
  assets: Asset[];
  jobs: Job[];
}

export interface Storyboard {
  schema_version: number;
  title: string;
  platform: string;
  aspect: string;
  fps: number;
  duration_target_s: number;
  palette: { bg: string; primary: string; accent: string; text: string };
  music_mood: string;
  scenes: {
    id: string;
    kind: 'hook' | 'reveal' | 'typography' | 'outro';
    duration_s: number;
    headline?: string;
    body?: string;
    narration?: string;
    visual_prompt?: string;
    motion: { style: string; intensity: number };
    transition_in: 'fade' | 'cut' | 'slide';
  }[];
}

export interface Health {
  status: string;
  version: string;
  providers: Record<string, string[]>;
  storage_root: string;
}
