'use client';

// Polls ProjectDetail while any job is pending/running (contracts: chat is sync,
// renders are jobs — ADR-0008).
import { useCallback, useEffect, useRef, useState } from 'react';
import type { ProjectDetail } from '@/types/api';
import { api } from './api';

export function useProject(pid: string) {
  const [detail, setDetail] = useState<ProjectDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const refresh = useCallback(async () => {
    try {
      setDetail(await api.getProject(pid));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [pid]);

  useEffect(() => {
    let alive = true;
    const tick = async () => {
      await refresh();
      if (!alive) return;
      const busy = (d: ProjectDetail | null) =>
        d?.jobs.some((j) => j.status === 'pending' || j.status === 'running') ?? false;
      timer.current = setTimeout(tick, busy(detail) ? 1500 : 5000);
    };
    void tick();
    return () => {
      alive = false;
      if (timer.current) clearTimeout(timer.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pid, refresh]);

  return { detail, error, refresh };
}
