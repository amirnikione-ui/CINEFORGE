#!/usr/bin/env node
/**
 * CINEFORGE — DEV-ONLY MOCK API (frontend development fixture).
 *
 * ╔══════════════════════════════════════════════════════════════════╗
 * ║  THIS IS NOT THE PRODUCT BACKEND.                                ║
 * ║  It is a clearly-labeled in-memory fixture implementing the      ║
 * ║  docs/API_CONTRACTS.md v0.1 shapes so the studio UI can be       ║
 * ║  developed and demoed before `backend/` lands (CF-010/011).      ║
 * ║  Every artifact it returns is marked provider:"mock".            ║
 * ║  The real director agent lives in backend/app/agent (agent-03).  ║
 * ╚══════════════════════════════════════════════════════════════════╝
 *
 * Usage:  node mocks/mock-api.mjs   (PORT env optional, default 8000)
 * Serves: GET /health · POST/GET /api/projects · GET/DELETE /api/projects/:id
 *         POST /api/projects/:id/chat · GET /api/jobs/:id · GET /api/assets/:id/file
 */
import http from 'node:http';
import crypto from 'node:crypto';
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const PORT = Number(process.env.PORT || 8000);
const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURE_VIDEO = join(HERE, 'fixtures', 'mock_render.mp4');

const BANNER = `
┌─────────────────────────────────────────────────────────────┐
│  CINEFORGE DEV MOCK API — not the real backend              │
│  in-memory · deterministic · provider:"mock" everywhere     │
└─────────────────────────────────────────────────────────────┘`;

const uuid = () => crypto.randomUUID();
const now = () => new Date().toISOString();

/* ---------------- in-memory store ---------------- */
const projects = new Map(); // id -> {project, messages[], assets[], jobs[]}

/* ---------------- mock director (deterministic) ---------------- */
function mockStoryboard(project) {
  const target = project.duration_hint_s ?? 30;
  const dark = /dark|cinematic|دارک|سینمایی|noir/i.test(`${project.brief} ${project.style ?? ''}`);
  const palette = dark
    ? { bg: '#0a0a12', primary: '#7c5cff', accent: '#00e5ff', text: '#f5f5ff' }
    : { bg: '#120f0a', primary: '#ff8a3d', accent: '#ffd166', text: '#fffaf0' };
  const topic = (project.title || 'the product').replace(/promo|launch/i, '').trim() || 'the product';

  const scenes = [
    {
      id: 'scene-01', kind: 'hook', duration_s: Math.round(target * 0.2 * 10) / 10,
      headline: `${topic.toUpperCase()}`, body: 'Something is coming.',
      narration: `Meet ${topic}.`,
      visual_prompt: dark ? 'dark cinematic haze, violet rim light, slow dolly-in' : 'bright studio light, energetic push-in',
      motion: { style: 'ken-burns', intensity: 0.6 }, transition_in: 'fade',
    },
    {
      id: 'scene-02', kind: 'reveal', duration_s: Math.round(target * 0.35 * 10) / 10,
      headline: 'BUILT DIFFERENT', body: 'Designed for the bold.',
      narration: 'Built different. Designed for the bold.',
      visual_prompt: dark ? 'neon reflections on wet asphalt, anamorphic flare' : 'sunset skyline, lens flare, drone reveal',
      motion: { style: 'zoom', intensity: 0.5 }, transition_in: 'cut',
    },
    {
      id: 'scene-03', kind: 'typography', duration_s: Math.round(target * 0.25 * 10) / 10,
      headline: 'PROMPT → PREMIERE', body: 'One brief. One take.',
      narration: 'From prompt to premiere in one take.',
      visual_prompt: 'kinetic typography on gradient, particles',
      motion: { style: 'reveal', intensity: 0.7 }, transition_in: 'slide',
    },
    {
      id: 'scene-04', kind: 'outro', duration_s: Math.max(2, Math.round(target * 0.2 * 10) / 10),
      headline: 'CINEFORGE', body: 'The AI video studio.',
      narration: 'CINEFORGE. The AI video studio.',
      visual_prompt: 'logo reveal on dark gradient, volumetric light',
      motion: { style: 'ken-burns', intensity: 0.3 }, transition_in: 'fade',
    },
  ];
  const sum = scenes.reduce((a, s) => a + s.duration_s, 0);
  scenes[scenes.length - 1].duration_s = Math.max(2, scenes[scenes.length - 1].duration_s + (target - sum));

  return {
    schema_version: 1,
    title: project.title,
    platform: project.platform ?? 'instagram',
    aspect: project.platform === 'youtube' || project.platform === 'web' ? '16:9' : '9:16',
    fps: 30,
    duration_target_s: target,
    palette,
    music_mood: dark ? 'dark-cinematic' : 'bright-energetic',
    scenes,
  };
}

function mockDirect(project, userText) {
  const sb = mockStoryboard(project);
  const pid = project.id;
  const assets = [];
  const jobs = [];

  // storyboard asset
  const sbAsset = {
    id: uuid(), project_id: pid, kind: 'storyboard', filename: 'storyboard.json',
    path: `/data/storage/${pid}/storyboards/storyboard.json`,
    meta: { provider: 'mock', scenes: sb.scenes.length, storyboard: sb },
    created_at: now(),
  };
  assets.push(sbAsset);

  // mock video render (fixture file)
  const videoAsset = {
    id: uuid(), project_id: pid, kind: 'video', filename: 'final_v1.mp4',
    path: `/data/storage/${pid}/video/final_v1.mp4`,
    meta: { provider: 'mock', duration_s: sb.duration_target_s, width: sb.aspect === '9:16' ? 1080 : 1920, height: sb.aspect === '9:16' ? 1920 : 1080, fps: 30 },
    created_at: now(),
  };
  assets.push(videoAsset);

  const renderJob = {
    id: uuid(), project_id: pid, kind: 'render', status: 'done', progress: 1,
    result: { asset_id: videoAsset.id, duration_s: sb.duration_target_s }, error: null,
  };
  jobs.push(renderJob);

  project.status = 'ready';

  const plan = [
    `Parse brief: ${sb.duration_target_s}s, ${sb.aspect}, ${project.style ?? 'default'} (${sb.music_mood})`,
    `Write ${sb.scenes.length}-scene storyboard (hook → reveal → typography → outro)`,
    'Generate concept frames per scene',
    'Synthesize narration (mock voice)',
    'Render slideshow with FFmpeg toolkit',
    'QA: probe duration, verify stream integrity',
  ];

  const assistant = {
    id: uuid(), project_id: pid, role: 'assistant',
    content:
      `Done — I drafted a ${sb.duration_target_s}s ${sb.aspect} cut for “${project.title}”: ` +
      `hook, reveal, typography beat, and outro (${sb.scenes.length} scenes, ${sb.music_mood} mood). ` +
      'A mock render is attached so you can see the shape of it in Preview. ' +
      'Tell me what to change — pacing, headlines, narration, palette — and I will regenerate the affected scenes. ' +
      '[DEV MOCK API — real director lands with CF-011]',
    meta: { plan, tools_used: ['write_storyboard', 'generate_concept_frames', 'generate_narration', 'render_slideshow', 'probe_media'], llm_provider: 'mock' },
    created_at: now(),
  };

  return { assets, jobs, assistant };
}

/* ---------------- http plumbing ---------------- */
function json(res, code, body) {
  const payload = JSON.stringify(body);
  res.writeHead(code, {
    'Content-Type': 'application/json',
    'X-Mock-Api': 'true',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'GET,POST,DELETE,OPTIONS',
  });
  res.end(payload);
}

async function readBody(req) {
  const chunks = [];
  for await (const c of req) chunks.push(c);
  const raw = Buffer.concat(chunks).toString('utf8');
  return raw ? JSON.parse(raw) : {};
}

function projectDetail(p) {
  return { project: p.project, messages: p.messages, assets: p.assets, jobs: p.jobs };
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url ?? '/', `http://localhost:${PORT}`);
  const parts = url.pathname.split('/').filter(Boolean);

  if (req.method === 'OPTIONS') return json(res, 204, {});

  try {
    // GET /health
    if (req.method === 'GET' && url.pathname === '/health') {
      return json(res, 200, {
        status: 'ok', version: '0.1.0-mock',
        providers: { llm: ['mock'], image: ['mock'], tts: ['mock'], stt: ['mock'], music: ['mock'], video: ['mock'] },
        storage_root: '/data/storage (DEV MOCK, in-memory)',
      });
    }

    // POST /api/projects
    if (req.method === 'POST' && url.pathname === '/api/projects') {
      const body = await readBody(req);
      if (!body.title || !body.brief) return json(res, 400, { detail: 'title and brief are required' });
      const project = {
        id: uuid(), title: body.title, brief: body.brief,
        style: body.style, platform: body.platform, duration_hint_s: body.duration_hint_s,
        status: 'draft', created_at: now(),
      };
      projects.set(project.id, { project, messages: [], assets: [], jobs: [] });
      return json(res, 201, project);
    }

    // GET /api/projects
    if (req.method === 'GET' && url.pathname === '/api/projects') {
      const list = [...projects.values()].map(projectDetail).map((d) => d.project)
        .sort((a, b) => (a.created_at < b.created_at ? 1 : -1));
      return json(res, 200, list);
    }

    // /api/projects/:id...
    if (parts[0] === 'api' && parts[1] === 'projects' && parts[2]) {
      const rec = projects.get(parts[2]);
      if (!rec) return json(res, 404, { detail: 'project not found' });

      if (req.method === 'GET' && parts.length === 3) return json(res, 200, projectDetail(rec));

      if (req.method === 'DELETE' && parts.length === 3) {
        projects.delete(parts[2]);
        return json(res, 204, {});
      }

      if (req.method === 'POST' && parts[3] === 'chat') {
        const body = await readBody(req);
        if (!body.message) return json(res, 400, { detail: 'message is required' });
        const userMessage = { id: uuid(), project_id: rec.project.id, role: 'user', content: body.message, created_at: now() };
        rec.messages.push(userMessage);
        const { assets, jobs, assistant } = mockDirect(rec.project, body.message);
        rec.messages.push(assistant);
        rec.assets.push(...assets);
        rec.jobs.push(...jobs);
        return json(res, 200, { user_message: userMessage, assistant_message: assistant, assets, jobs });
      }
    }

    // GET /api/jobs/:id
    if (req.method === 'GET' && parts[0] === 'api' && parts[1] === 'jobs' && parts[2]) {
      for (const rec of projects.values()) {
        const job = rec.jobs.find((j) => j.id === parts[2]);
        if (job) return json(res, 200, job);
      }
      return json(res, 404, { detail: 'job not found' });
    }

    // GET /api/assets/:id/file
    if (req.method === 'GET' && parts[0] === 'api' && parts[1] === 'assets' && parts[3] === 'file') {
      for (const rec of projects.values()) {
        const asset = rec.assets.find((a) => a.id === parts[2]);
        if (!asset) continue;
        if (asset.kind === 'storyboard') {
          return json(res, 200, asset.meta?.storyboard ?? { detail: 'no storyboard payload' });
        }
        if (asset.kind === 'video' && existsSync(FIXTURE_VIDEO)) {
          const buf = readFileSync(FIXTURE_VIDEO);
          res.writeHead(200, {
            'Content-Type': 'video/mp4', 'Content-Length': buf.length,
            'X-Mock-Api': 'true', 'Access-Control-Allow-Origin': '*',
          });
          return res.end(buf);
        }
        return json(res, 200, { detail: 'mock asset has no binary payload', asset: asset.filename });
      }
      return json(res, 404, { detail: 'asset not found' });
    }

    return json(res, 404, { detail: `no mock route for ${req.method} ${url.pathname}` });
  } catch (err) {
    return json(res, 500, { detail: err instanceof Error ? err.message : 'mock crashed' });
  }
});

server.listen(PORT, () => {
  console.log(BANNER);
  console.log(`listening on http://localhost:${PORT}  (X-Mock-Api header on every response)\n`);
});
