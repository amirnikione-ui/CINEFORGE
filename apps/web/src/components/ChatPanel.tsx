"use client";

import { useEffect, useRef, useState } from "react";
import { formatTimestamp } from "@/lib/api";
import type { Message, MessageMeta } from "@/types/api";

function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

interface ChatPanelProps {
  messages: Message[];
  sending: boolean;
  sendError: string | null;
  /** Resolves to false when delivery failed so the composer can restore the draft. */
  onSend: (text: string) => Promise<boolean>;
  className?: string;
  /** Rendered as a ✕ button (mobile drawer only — hidden ≥ lg). */
  onClose?: () => void;
}

export default function ChatPanel({ messages, sending, sendError, onSend, className, onClose }: ChatPanelProps) {
  const [text, setText] = useState("");
  const listRef = useRef<HTMLDivElement>(null);
  const prevCountRef = useRef(0);

  // Auto-scroll to the newest message.
  useEffect(() => {
    const el = listRef.current;
    if (el && messages.length !== prevCountRef.current) {
      el.scrollTop = el.scrollHeight;
      prevCountRef.current = messages.length;
    }
  }, [messages]);

  async function submit(): Promise<void> {
    const value = text.trim();
    if (!value || sending) return;
    setText("");
    const ok = await onSend(value);
    if (!ok) setText((cur) => (cur.length === 0 ? value : cur)); // restore the draft if delivery failed
  }

  return (
    <section className={cx("flex min-h-0 flex-col", className)} aria-label="Director chat">
      <header className="flex h-10 shrink-0 items-center justify-between border-b border-ink-line px-3">
        <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">Director chat</span>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-zinc-500 transition hover:text-white lg:hidden"
            title="Close chat"
          >
            ✕
          </button>
        )}
      </header>

      <div ref={listRef} className="min-h-0 flex-1 space-y-3 overflow-y-auto p-3">
        {messages.length === 0 && !sending && (
          <div className="rounded-xl border border-dashed border-ink-line p-3 text-xs leading-relaxed text-zinc-500">
            Describe the video you want — the director will plan it, generate the media, render the cut, and report
            back here. Ask for changes in plain language at any time.
          </div>
        )}
        {messages.map((m) => renderMessage(m))}
      </div>

      <div className="shrink-0 border-t border-ink-line bg-ink-panel p-3">
        {sendError && (
          <div className="mb-2 rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-[11px] leading-snug text-red-300">
            ⚠ {sendError}
          </div>
        )}
        {sending && (
          <div className="mb-2 flex items-center gap-1.5 text-xs text-accent-violet">
            Director is working
            <span className="typing-dots">
              <span>.</span>
              <span>.</span>
              <span>.</span>
            </span>
          </div>
        )}
        <div className="flex items-end gap-2">
          <textarea
            rows={2}
            className="input flex-1 resize-none"
            placeholder={sending ? "The director is on it…" : "Describe the video you want — or ask for a change…"}
            value={text}
            disabled={sending}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void submit();
              }
            }}
          />
          <button
            type="button"
            className="btn-accent h-[44px] px-3.5"
            disabled={sending || text.trim().length === 0}
            onClick={() => void submit()}
            title="Send (Enter)"
          >
            ➤
          </button>
        </div>
        <p className="mt-1.5 font-mono text-[9px] text-zinc-600">Enter to send · Shift+Enter for a new line</p>
      </div>
    </section>
  );
}

function renderMessage(m: Message) {
  if (m.role === "system") {
    return (
      <div
        key={m.id}
        className="mx-auto w-fit max-w-full rounded-full border border-ink-line bg-ink-raised/60 px-3 py-1 text-center font-mono text-[10px] text-zinc-500"
      >
        {m.content}
      </div>
    );
  }

  const isUser = m.role === "user";
  return (
    <div key={m.id} className={cx("fade-up max-w-[85%]", isUser ? "ml-auto" : "mr-auto")}>
      <div
        className={cx(
          "rounded-xl border px-3 py-2 text-[13px] leading-relaxed",
          isUser
            ? "border-accent-violet/40 bg-accent-violet/10 text-zinc-100"
            : "border-ink-line bg-ink-raised text-zinc-300",
        )}
      >
        <p className="whitespace-pre-wrap break-words">{m.content}</p>
        {!isUser && <AssistantExtras meta={m.meta} />}
      </div>
      <div className={cx("mt-1 font-mono text-[9px] text-zinc-600", isUser ? "text-right" : "text-left")}>
        {formatTimestamp(m.created_at)}
      </div>
    </div>
  );
}

/** Director transparency: collapsible plan, tool chips, LLM provider tag. */
function AssistantExtras({ meta }: { meta?: MessageMeta | null }) {
  const [planOpen, setPlanOpen] = useState(false);
  if (!meta) return null;

  const plan = Array.isArray(meta.plan) ? meta.plan.map(String) : [];
  const tools = Array.isArray(meta.tools_used) ? meta.tools_used.map(String) : [];
  const provider = typeof meta.llm_provider === "string" ? meta.llm_provider : null;
  if (plan.length === 0 && tools.length === 0 && !provider) return null;

  return (
    <div className="mt-2 border-t border-ink-line/70 pt-2">
      {plan.length > 0 && (
        <div>
          <button
            type="button"
            onClick={() => setPlanOpen((o) => !o)}
            className="text-[11px] font-medium text-accent-violet transition hover:text-accent-cyan"
          >
            {planOpen ? "▾" : "▸"} Director plan ({plan.length} steps)
          </button>
          {planOpen && (
            <ol className="mt-1.5 space-y-1">
              {plan.map((step, i) => (
                <li key={i} className="flex items-start gap-1.5 text-[11px] leading-snug text-zinc-400">
                  <span className="mt-px shrink-0 text-emerald-400">✓</span>
                  <span>{step}</span>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}

      {tools.length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-1">
          {tools.map((t, i) => (
            <span key={i} className="chip border-ink-line bg-ink-panel font-mono text-zinc-400">
              🔧 {t}
            </span>
          ))}
        </div>
      )}

      {provider && <div className="mt-1.5 font-mono text-[9px] text-zinc-600">provider: {provider}</div>}
    </div>
  );
}
