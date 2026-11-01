"use client";

import { useEffect, useState } from "react";
import { ApiError, apiDown, createProject } from "@/lib/api";
import type { Project } from "@/types/api";

function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

const PLATFORMS = ["instagram", "youtube", "tiktok", "web"] as const;

interface NewProjectDialogProps {
  /** "inline" renders the hero card on the dashboard; "modal" renders the overlay dialog. */
  variant: "inline" | "modal";
  /** modal only */
  open?: boolean;
  /** modal only */
  onClose?: () => void;
  onCreated: (project: Project) => void;
  className?: string;
}

export default function NewProjectDialog({ variant, open = false, onClose, onCreated, className }: NewProjectDialogProps) {
  const [title, setTitle] = useState("");
  const [brief, setBrief] = useState("");
  const [platform, setPlatform] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Close the modal on Escape.
  useEffect(() => {
    if (variant !== "modal" || !open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose?.();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [variant, open, onClose]);

  const canSubmit = title.trim().length > 0 && brief.trim().length > 0 && !submitting;

  async function submit(): Promise<void> {
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      const project = await createProject({
        title: title.trim(),
        brief: brief.trim(),
        ...(platform ? { platform } : {}),
      });
      setTitle("");
      setBrief("");
      setPlatform("");
      onCreated(project);
    } catch (err) {
      setError(
        apiDown(err)
          ? "Could not reach the API — start the backend (make api) and try again."
          : err instanceof ApiError
            ? `API ${err.status}: ${err.detail}`
            : "Unexpected error while creating the project.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  const fields = (
    <>
      <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
        <input
          type="text"
          className="input"
          placeholder="Project title — e.g. Nova Runners promo"
          value={title}
          maxLength={120}
          autoFocus={variant === "modal"}
          onChange={(e) => setTitle(e.target.value)}
        />
        <select
          className="input sm:w-44"
          value={platform}
          onChange={(e) => setPlatform(e.target.value)}
          title="Target platform (optional)"
        >
          <option value="">platform: auto</option>
          {PLATFORMS.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
      </div>
      <textarea
        className="input mt-3 resize-y"
        rows={3}
        placeholder="A 30-second cinematic promo for my product. Dark mood, fitting music, English narration, pro motion graphics, Instagram output."
        value={brief}
        onChange={(e) => setBrief(e.target.value)}
      />
      {error && (
        <p className="mt-2 rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs leading-snug text-red-300">
          ⚠ {error}
        </p>
      )}
      <div className="mt-3 flex items-center justify-between gap-3">
        <p className="hidden text-[11px] text-zinc-600 sm:block">The director picks up the brief in the studio chat.</p>
        <button type="submit" className="btn-accent" disabled={!canSubmit}>
          {submitting ? (
            <>
              Creating
              <span className="typing-dots ml-1">
                <span>.</span>
                <span>.</span>
                <span>.</span>
              </span>
            </>
          ) : (
            "✦ Create with Director"
          )}
        </button>
      </div>
    </>
  );

  if (variant === "inline") {
    return (
      <form onSubmit={(e) => { e.preventDefault(); void submit(); }} className={cx("panel w-full max-w-2xl p-4", className)}>
        {fields}
      </form>
    );
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={() => onClose?.()} />
      <form
        onSubmit={(e) => { e.preventDefault(); void submit(); }}
        role="dialog"
        aria-modal="true"
        aria-label="New project"
        className="panel fade-up relative w-full max-w-lg p-5"
      >
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-zinc-400">New project</h2>
          <button
            type="button"
            onClick={() => onClose?.()}
            className="rounded p-1 text-zinc-500 transition hover:text-white"
            title="Close (Esc)"
          >
            ✕
          </button>
        </div>
        {fields}
      </form>
    </div>
  );
}
