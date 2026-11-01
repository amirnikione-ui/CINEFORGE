'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { sendChat } from '@/lib/api';
import type { Asset, Job, Message, Project } from '@/types/api';
import { STATUS_STYLES } from '@/lib/format';
import { ProgressBar, Spinner } from '@/components/ui';

const QUICK_PROMPTS = [
  'A 30s cinematic promo — dark mood, English narration, Instagram output.',
  'Make the hook punchier and cut 5 seconds.',
  'Re-render with a brighter palette and new music mood.',
];

function PlanSteps({ plan }: { plan: string[] }) {
  return (
    <div className="rounded-lg border border-line bg-ink/40 p-3">
      <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-forge">
        Director plan · {plan.length} steps
      </p>
      <ol className="space-y-1.5">
        {plan.map((step, i) => (
          <li key={i} className="flex gap-2 text-xs leading-relaxed text-ivory/80">
            <span className="mt-0.5 font-mono text-[10px] text-accent">{String(i + 1).padStart(2, '0')}</span>
            {step}
          </li>
        ))}
      </ol>
    </div>
  );
}

function JobRow({ job }: { job: Job }) {
  return (
    <div className="rounded-lg border border-line bg-ink/40 p-3">
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <span className="font-mono text-[11px] text-ivory/80">
          {job.kind} · {job.id.slice(0, 8)}
        </span>
        <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${STATUS_STYLES[job.status] ?? ''}`}>
          {job.status}
        </span>
      </div>
      <ProgressBar value={job.progress} />
      {job.error ? <p className="mt-1.5 text-[11px] text-rose-300">{job.error}</p> : null}
    </div>
  );
}

function MessageBubble({ message, newAssets }: { message: Message; newAssets: Asset[] }) {
  const isUser = message.role === 'user';
  const plan = message.meta?.plan;
  const tools = message.meta?.tools_used ?? [];
  const provider = message.meta?.llm_provider;

  return (
    <div className={`flex animate-rise ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[88%] space-y-2 ${isUser ? 'items-end' : ''}`}>
        <div
          className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
            isUser
              ? 'rounded-br-sm bg-forge/25 text-ivory'
              : 'rounded-bl-sm border border-line bg-raised/80 text-ivory/90'
          }`}
        >
          {message.content}
        </div>

        {!isUser && plan && plan.length > 0 ? <PlanSteps plan={plan} /> : null}

        {!isUser && (tools.length > 0 || provider) ? (
          <div className="flex flex-wrap gap-1.5">
            {tools.map((t) => (
              <span key={t} className="chip font-mono !text-[10px]">
                ⚙ {t}
              </span>
            ))}
            {provider ? (
              <span className="chip !text-[10px] !border-accent/30 !text-accent/90" title="LLM provider used">
                ✦ {provider}
              </span>
            ) : null}
          </div>
        ) : null}

        {newAssets.length > 0 ? (
          <div className="flex flex-wrap gap-1.5">
            {newAssets.map((a) => (
              <span key={a.id} className="chip !text-[10px]">
                ▢ {a.kind}: {a.filename}
              </span>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}

export function ChatPanel({
  project,
  messages,
  assets,
  jobs,
  onActivity,
}: {
  project: Project;
  messages: Message[];
  assets: Asset[];
  jobs: Job[];
  onActivity: () => void;
}) {
  const [draft, setDraft] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Assets produced by the most recent assistant message → shown as artifact chips.
  const lastAssistant = useMemo(
    () => [...messages].reverse().find((m) => m.role === 'assistant'),
    [messages],
  );
  const newAssetIds = useMemo(() => {
    if (!lastAssistant) return new Set<string>();
    return new Set(
      assets
        .filter((a) => a.created_at <= lastAssistant.created_at)
        .slice(0, 12)
        .map((a) => a.id),
    );
  }, [assets, lastAssistant]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages.length, sending]);

  async function submit(text?: string) {
    const message = (text ?? draft).trim();
    if (!message || sending) return;
    setSending(true);
    setError(null);
    setDraft('');
    try {
      await sendChat(project.id, { message });
      onActivity();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Chat failed');
    } finally {
      setSending(false);
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  const activeJobs = jobs.filter((j) => j.status === 'pending' || j.status === 'running');

  return (
    <div className="panel flex h-full min-h-0 flex-col">
      {/* Header */}
      <div className="border-b border-line px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-forge opacity-60" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-forge" />
          </span>
          <h2 className="text-sm font-bold">Director agent</h2>
          <span className="chip ml-auto font-mono !text-[10px]">chat-first studio</span>
        </div>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4">
        {messages.length === 0 ? (
          <div className="space-y-3 pt-6 text-center">
            <p className="text-sm font-semibold text-ivory/85">Brief your director.</p>
            <p className="mx-auto max-w-xs text-xs leading-relaxed text-muted">
              Describe the video you want. The agent plans the structure, writes the storyboard,
              generates media and renders — you approve and iterate in chat.
            </p>
            <div className="mx-auto max-w-sm space-y-2 pt-2">
              {QUICK_PROMPTS.map((q) => (
                <button
                  key={q}
                  onClick={() => submit(q)}
                  className="w-full rounded-lg border border-line bg-ink/40 px-3 py-2 text-left text-[11px] leading-relaxed text-ivory/75 transition hover:border-forge/40 hover:bg-forge/10"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((m) => (
            <MessageBubble
              key={m.id}
              message={m}
              newAssets={m.role === 'assistant' && m.id === lastAssistant?.id
                ? assets.filter((a) => newAssetIds.has(a.id))
                : []}
            />
          ))
        )}

        {sending ? (
          <div className="flex items-center gap-2 text-xs text-forge">
            <Spinner />
            <span className="animate-breathe">Director is planning…</span>
          </div>
        ) : null}

        {activeJobs.length > 0 ? (
          <div className="space-y-2">
            {activeJobs.map((j) => (
              <JobRow key={j.id} job={j} />
            ))}
          </div>
        ) : null}
      </div>

      {/* Composer */}
      <div className="border-t border-line p-3">
        {error ? <p className="mb-2 text-[11px] text-rose-300">{error}</p> : null}
        <div className="flex items-end gap-2">
          <textarea
            className="input max-h-32 min-h-[42px] flex-1 resize-none"
            placeholder="Tell the director what to change or produce… (Enter to send)"
            value={draft}
            rows={1}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={onKeyDown}
            disabled={sending}
          />
          <button className="btn-primary !px-4" onClick={() => submit()} disabled={sending || !draft.trim()}>
            {sending ? <Spinner /> : 'Send'}
          </button>
        </div>
      </div>
    </div>
  );
}
