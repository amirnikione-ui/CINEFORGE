'use client';

import Link from 'next/link';
import type { Project } from '@/types/api';
import { relTime, truncate } from '@/lib/format';
import { StatusChip } from '@/components/ui';

export function ProjectCard({ project }: { project: Project }) {
  return (
    <Link
      href={`/projects/${project.id}`}
      className="panel group flex flex-col gap-3 p-5 transition hover:border-forge/40 hover:shadow-glow"
    >
      <div className="flex items-start justify-between gap-3">
        <h3 className="line-clamp-1 text-base font-bold text-ivory group-hover:text-white">
          {project.title}
        </h3>
        <StatusChip status={project.status} />
      </div>

      <p className="line-clamp-2 min-h-[32px] text-xs leading-relaxed text-muted">
        {truncate(project.brief || 'No brief yet — open the studio and brief the director.', 120)}
      </p>

      <div className="flex flex-wrap items-center gap-1.5">
        {project.platform ? <span className="chip">{project.platform}</span> : null}
        {project.style ? <span className="chip">{project.style}</span> : null}
        {project.duration_hint_s ? <span className="chip">{project.duration_hint_s}s</span> : null}
      </div>

      <div className="mt-auto flex items-center justify-between border-t border-line pt-3 text-[11px] text-muted">
        <span>{relTime(project.created_at)}</span>
        <span className="font-semibold text-forge opacity-0 transition group-hover:opacity-100">
          Open studio →
        </span>
      </div>
    </Link>
  );
}
