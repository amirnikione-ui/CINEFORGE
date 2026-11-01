'use client';

import { useRef, useState } from 'react';
import { api } from '@/lib/api';
import type { Message, ProjectDetail } from '@/types/api';

export default function ChatPanel({ pid, detail, onRefresh }: {
  pid: string;
  detail: ProjectDetail;
  onRefresh: () => Promise<void>;
}) {
  const [messages, setMessages] = useState<Message[]>(detail.messages);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // merge refreshed history (poll) with local optimistic messages
  const merged = mergeMessages(detail.messages, messages);

  const send = async () => {
    const text = input.trim();
    if (!text || busy) return;
    setBusy(true);
    setErr(null);
    setInput('');
    try {
      const res = await api.chat(pid, text);
      setMessages((prev) => [...prev, res.user_message, res.assistant_message]);
      await onRefresh();
      setTimeout(() => listRef.current?.scrollTo({ top: 1e9, behavior: 'smooth' }), 50);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <aside className="flex min-h-0 flex-col border-r border-ink-700 bg-ink-900">
      <div className="flex items-center justify-between border-b border-ink-700 px-4 py-3">
        <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400">Director chat</h2>
        <span className="pill">agent</span>
      </div>

      <div ref={listRef} className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4">
        {merged.length === 0 && (
          <div className="panel p-4 text-xs leading-relaxed text-slate-400">
            👋 Brief the director — it writes the script, storyboards every scene, designs the motion
            with code, scores the music and renders the final cut. Try:
            <em className="mt-2 block text-slate-300">
              “Make it punchier and shorten the hook.”
            </em>
          </div>
        )}
        {merged.map((m) => <Bubble key={m.id} m={m} />)}
        {busy && (
          <div className="panel animate-pulse p-3 text-xs text-slate-400">
            🎬 Director is planning and calling tools…
          </div>
        )}
        {err && <p className="text-xs text-red-400">{err}</p>}
      </div>

      <div className="border-t border-ink-700 p-3">
        <div className="flex gap-2">
          <input
            className="field"
            placeholder="Tell the director what to change…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && void send()}
            disabled={busy}
          />
          <button className="btn-forge" onClick={send} disabled={busy || !input.trim()}>Send</button>
        </div>
      </div>
    </aside>
  );
}

function mergeMessages(server: Message[], local: Message[]): Message[] {
  const byId = new Map<string, Message>();
  for (const m of [...server, ...local]) byId.set(m.id, m);
  return [...byId.values()].sort((a, b) => a.created_at.localeCompare(b.created_at));
}

function Bubble({ m }: { m: Message }) {
  const isUser = m.role === 'user';
  return (
    <div className={`panel p-3 text-sm ${isUser ? 'border-forge-500/30 bg-forge-500/10' : ''}`}>
      <div className="mb-1 flex items-center gap-2 text-[10px] uppercase tracking-wider text-slate-500">
        <span className={isUser ? 'text-forge-300' : 'text-neon'}>{isUser ? 'You' : 'Director'}</span>
        {!isUser && m.meta?.llm_provider && (
          <span className="pill">{m.meta.llm_provider === 'mock' ? 'offline tier' : m.meta.llm_provider}</span>
        )}
      </div>
      <p className="whitespace-pre-wrap leading-relaxed text-slate-200">{m.content}</p>

      {!isUser && m.meta?.tools_used && m.meta.tools_used.length > 0 && (
        <div className="mt-3 space-y-1 border-t border-ink-700 pt-2">
          {m.meta.tools_used.map((t, i) => (
            <div key={i} className="flex items-center gap-2 text-[11px]">
              <span className={t.ok ? 'text-emerald-400' : 'text-red-400'}>{t.ok ? '✓' : '✗'}</span>
              <span className="font-mono text-slate-300">{t.tool}</span>
              <span className="pill">{t.provider}</span>
              <span className="truncate text-slate-500">{t.summary}</span>
            </div>
          ))}
        </div>
      )}

      {!isUser && m.meta?.plan && (
        <details className="mt-2 text-[11px] text-slate-500">
          <summary className="cursor-pointer select-none">plan</summary>
          <ol className="mt-1 list-inside list-decimal space-y-0.5 font-mono">
            {m.meta.plan.map((s, i) => (
              <li key={i}>
                {s.step}
                {s.provider ? ` · ${s.provider}` : ''}
                {s.strategy ? ` (${s.strategy})` : ''}
                {s.reason ? ` — ${s.reason}` : ''}
              </li>
            ))}
          </ol>
        </details>
      )}
    </div>
  );
}
