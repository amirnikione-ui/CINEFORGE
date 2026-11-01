/**
 * Typed REST client for the CINEFORGE backend (docs/API_CONTRACTS.md v0.1).
 * Single place where the API URL + error handling live; components never fetch raw.
 */
import type {
  Asset,
  ChatResponse,
  CreateProjectInput,
  Health,
  Job,
  Project,
  ProjectDetail,
  SendChatInput,
} from '@/types/api';

export const API_URL: string =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, '') || 'http://localhost:8000';

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
      cache: 'no-store',
    });
  } catch {
    throw new ApiError(0, 'Backend unreachable — is it running? (see Makefile: make api)');
  }
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body?.detail) detail = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

/* ---------------- health ---------------- */

export function getHealth(): Promise<Health> {
  return request<Health>('/health');
}

/* ---------------- projects ---------------- */

export function listProjects(): Promise<Project[]> {
  return request<Project[]>('/api/projects');
}

export function createProject(input: CreateProjectInput): Promise<Project> {
  return request<Project>('/api/projects', { method: 'POST', body: JSON.stringify(input) });
}

export function getProject(pid: string): Promise<ProjectDetail> {
  return request<ProjectDetail>(`/api/projects/${pid}`);
}

export function deleteProject(pid: string): Promise<void> {
  return request<void>(`/api/projects/${pid}`, { method: 'DELETE' });
}

/* ---------------- chat ---------------- */

export function sendChat(pid: string, input: SendChatInput): Promise<ChatResponse> {
  return request<ChatResponse>(`/api/projects/${pid}/chat`, {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

/* ---------------- jobs ---------------- */

export function getJob(id: string): Promise<Job> {
  return request<Job>(`/api/jobs/${id}`);
}

/* ---------------- assets ---------------- */

/** URL for the raw file behind an asset (mp4/png/wav/json). */
export function assetFileUrl(asset: Pick<Asset, 'id'>): string {
  return `${API_URL}/api/assets/${asset.id}/file`;
}

export function assetDownloadUrl(asset: Asset): string {
  return `${assetFileUrl(asset)}?download=1`;
}

/* ---------------- helpers ---------------- */

export function latestAsset<T extends Asset>(assets: T[], kind: T['kind']): T | undefined {
  return assets
    .filter((a) => a.kind === kind)
    .sort((a, b) => (a.created_at < b.created_at ? 1 : -1))[0];
}

export function isJobActive(job: Job): boolean {
  return job.status === 'pending' || job.status === 'running';
}
