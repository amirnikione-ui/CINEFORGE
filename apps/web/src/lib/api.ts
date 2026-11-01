// Typed API client against the FastAPI service (docs/API_CONTRACTS.md).
import type { Asset, Health, Job, Message, Project, ProjectDetail } from '@/types/api';

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export interface ChatResponse {
  user_message: Message;
  assistant_message: Message;
  assets: Asset[];
  jobs: Job[];
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    cache: 'no-store',
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json())?.detail ?? detail;
    } catch {
      /* non-JSON error */
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  health: () => req<Health>('/health'),
  listProjects: () => req<Project[]>('/api/projects'),
  createProject: (body: { title: string; brief: string; platform: string; duration_hint_s: number }) =>
    req<Project>('/api/projects', { method: 'POST', body: JSON.stringify(body) }),
  getProject: (pid: string) => req<ProjectDetail>(`/api/projects/${pid}`),
  deleteProject: (pid: string) => req<void>(`/api/projects/${pid}`, { method: 'DELETE' }),
  chat: (pid: string, message: string) =>
    req<ChatResponse>(`/api/projects/${pid}/chat`, { method: 'POST', body: JSON.stringify({ message }) }),
  getJob: (jid: string) => req<Job>(`/api/jobs/${jid}`),
  assetUrl: (aid: string) => `${API_URL}/api/assets/${aid}/file`,
};
