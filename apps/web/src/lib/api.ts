/**
 * Typed REST client for the CINEFORGE backend.
 * Implements `docs/API_CONTRACTS.md` v0.1 exactly. Every request bypasses the
 * fetch cache because studio state (jobs, renders) is live.
 */

import type {
  ChatResponse,
  CreateProjectBody,
  Health,
  Job,
  Project,
  ProjectDetail,
  Storyboard,
} from "@/types/api";

/** Backend base URL. Override with NEXT_PUBLIC_API_URL (inlined at build time). */
export const API_BASE: string = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** HTTP-level error raised for non-2xx responses (`{"detail": "…"}` per contract). */
export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

/** True when a request failed at the network level (backend unreachable), not with an HTTP error. */
export function apiDown(err: unknown): boolean {
  return err instanceof TypeError;
}

async function request<T>(path: string, init?: { method?: string; body?: string }): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method: init?.method,
      body: init?.body,
      cache: "no-store",
      headers: {
        Accept: "application/json",
        ...(init?.body != null ? { "Content-Type": "application/json" } : {}),
      },
    });
  } catch (err) {
    if (err instanceof TypeError) throw err;
    // Normalize exotic failures (abort, runtime errors) to TypeError so apiDown() classifies them.
    throw new TypeError(err instanceof Error ? err.message : String(err));
  }

  if (!res.ok) {
    let detail = `HTTP ${res.status} ${res.statusText}`.trim();
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body?.detail === "string") detail = body.detail;
      else if (body?.detail != null) detail = JSON.stringify(body.detail);
    } catch {
      // Non-JSON error body — keep the status-line fallback.
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as unknown as T;
  return (await res.json()) as T;
}

// ── Endpoints ───────────────────────────────────────────────────────────────

export function getHealth(): Promise<Health> {
  return request<Health>("/health");
}

export function listProjects(): Promise<Project[]> {
  return request<Project[]>("/api/projects");
}

export function createProject(body: CreateProjectBody): Promise<Project> {
  return request<Project>("/api/projects", { method: "POST", body: JSON.stringify(body) });
}

export function getProjectDetail(projectId: string): Promise<ProjectDetail> {
  return request<ProjectDetail>(`/api/projects/${encodeURIComponent(projectId)}`);
}

export function sendChat(projectId: string, message: string): Promise<ChatResponse> {
  return request<ChatResponse>(`/api/projects/${encodeURIComponent(projectId)}/chat`, {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}

export function getJob(jobId: string): Promise<Job> {
  return request<Job>(`/api/jobs/${encodeURIComponent(jobId)}`);
}

/** Public URL for an asset's raw bytes (video/mp4, image/png, audio/wav, application/json…). */
export function assetUrl(assetId: string): string {
  return `${API_BASE}/api/assets/${encodeURIComponent(assetId)}/file`;
}

/** Fetch a JSON asset (e.g. the storyboard file served from the asset endpoint). */
export function getAssetJson<T = Storyboard>(assetId: string): Promise<T> {
  return request<T>(`/api/assets/${encodeURIComponent(assetId)}/file`);
}

// ── Formatting helpers (deterministic → safe across server/client rendering) ─

export function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const formatted = new Intl.DateTimeFormat("en-US", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
  }).format(d);
  return `${formatted} UTC`;
}

export function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds)) return "–";
  const m = Math.floor(seconds / 60);
  const s = seconds - m * 60;
  return m > 0 ? `${m}:${s.toFixed(1).padStart(4, "0")}` : `${s.toFixed(1)}s`;
}
