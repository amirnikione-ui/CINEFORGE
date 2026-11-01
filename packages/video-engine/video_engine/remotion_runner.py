"""Remotion project scaffolding + rendering (Node/Chromium required — worker container).

``scaffold_project`` copies the repo template ``packages/video-engine/remotion-template``
into the target dir (falling back to a generated, fully functional baseline project when
the template is absent) and drops ``public/storyboard.json`` next to it.
``render`` shells out to ``npx --yes remotion render CinematicPromo <out>`` with a
30-minute timeout; it needs Node >= 18 and Chromium (the Remotion headless shell).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path

RENDER_TIMEOUT_S = 1800


class RemotionError(RuntimeError):
    """Raised when scaffolding or rendering a Remotion project fails."""


def _find_template_dir() -> Path | None:
    env = os.environ.get("CINEFORGE_REMOTION_TEMPLATE")
    if env and Path(env).is_dir():
        return Path(env)
    here = Path(__file__).resolve()
    for candidate in here.parents:
        probe = candidate / "packages" / "video-engine" / "remotion-template"
        if probe.is_dir():
            return probe
    return None


# ---------------------------------------------------------------------------
# Baseline project writer (used when the repo template is not present yet).
# ---------------------------------------------------------------------------

_PACKAGE_JSON = """{
  "name": "remotion-cinematicpromo",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "render": "remotion render CinematicPromo out/final.mp4",
    "studio": "remotion studio"
  },
  "dependencies": {
    "@remotion/cli": "^4.0.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "remotion": "^4.0.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "typescript": "^5.5.0"
  }
}
"""

_TSCONFIG_JSON = """{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "jsx": "react-jsx",
    "strict": true,
    "skipLibCheck": true,
    "resolveJsonModule": true,
    "esModuleInterop": true,
    "lib": ["DOM", "ES2020"]
  },
  "include": ["src", "remotion.config.ts"]
}
"""

_REMOTION_CONFIG_TS = """import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
Config.setEntryPoint("./src/index.ts");
"""

_INDEX_TS = """import { registerRoot } from "remotion";
import { RemotionRoot } from "./Root";

registerRoot(RemotionRoot);
"""

_ROOT_TSX = """import React from "react";
import { Composition } from "remotion";
import { CinematicPromo, Storyboard } from "./CinematicPromo";
import storyboard from "../public/storyboard.json";

export const RemotionRoot: React.FC = () => {
  const fps = storyboard.fps ?? 30;
  const totalS = storyboard.scenes.reduce((acc: number, s: { duration_s?: number }) => acc + (s.duration_s ?? 4), 0);
  const dims =
    (storyboard.aspect ?? "9:16") === "16:9"
      ? { width: 1920, height: 1080 }
      : { width: 1080, height: 1920 };
  return (
    <Composition
      id="CinematicPromo"
      component={CinematicPromo}
      durationInFrames={Math.max(1, Math.round(totalS * fps))}
      fps={fps}
      width={dims.width}
      height={dims.height}
      defaultProps={{ storyboard: storyboard as Storyboard }}
    />
  );
};
"""

_CINEMATIC_PROMO_TSX = """import React from "react";
import {
  AbsoluteFill,
  interpolate,
  Sequence,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

export type Scene = {
  id?: string;
  kind?: string;
  duration_s?: number;
  headline?: string;
  body?: string;
  narration?: string;
  visual_prompt?: string;
  motion?: { style?: string; intensity?: number };
  transition_in?: string;
};

export type Storyboard = {
  schema_version?: number;
  title?: string;
  platform?: string;
  aspect?: string;
  fps?: number;
  duration_target_s?: number;
  palette?: { bg?: string; primary?: string; accent?: string; text?: string };
  music_mood?: string;
  scenes: Scene[];
};

const SceneView: React.FC<{ scene: Scene; palette: NonNullable<Storyboard["palette"]> }> = ({
  scene,
  palette,
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const intensity = scene.motion?.intensity ?? 0.6;
  const style = scene.motion?.style ?? "ken-burns";
  const fade = interpolate(frame, [0, Math.min(12, durationInFrames * 0.3)], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const zoom = 1 + 0.0009 * frame * (0.5 + intensity);
  const pan = interpolate(frame, [0, durationInFrames], [0, 40]);
  const transform =
    style === "slide"
      ? `translateX(${-pan}px) scale(1.05)`
      : `scale(${zoom.toFixed(4)})`;

  return (
    <AbsoluteFill
      style={{
        opacity: fade,
        background: `linear-gradient(180deg, ${palette.bg ?? "#0a0a12"} 0%, ${
          palette.primary ?? "#7c5cff"
        } 130%)`,
        transform,
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <div
        style={{
          color: palette.text ?? "#f5f5ff",
          fontSize: 96,
          fontWeight: 800,
          letterSpacing: -2,
          textAlign: "center",
          padding: "0 80px",
          textShadow: "4px 4px 18px rgba(0,0,0,0.6)",
        }}
      >
        {scene.headline}
      </div>
      {scene.body ? (
        <div
          style={{
            color: palette.text ?? "#f5f5ff",
            fontSize: 40,
            opacity: 0.85,
            marginTop: 28,
            textAlign: "center",
            padding: "0 100px",
          }}
        >
          {scene.body}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

export const CinematicPromo: React.FC<{ storyboard: Storyboard }> = ({ storyboard }) => {
  const { fps } = useVideoConfig();
  const palette = storyboard.palette ?? {};
  let cursor = 0;
  return (
    <AbsoluteFill style={{ backgroundColor: palette.bg ?? "#0a0a12" }}>
      {storyboard.scenes.map((scene, i) => {
        const from = Math.round(cursor * fps);
        cursor += scene.duration_s ?? 4;
        return (
          <Sequence
            key={scene.id ?? i}
            from={from}
            durationInFrames={Math.max(1, Math.round((scene.duration_s ?? 4) * fps))}
          >
            <SceneView scene={scene} palette={palette} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
"""


def _write_baseline_project(out_dir: Path) -> None:
    """Write a complete, editable Remotion 4 project (no template dir available)."""
    src = out_dir / "src"
    public = out_dir / "public"
    src.mkdir(parents=True, exist_ok=True)
    public.mkdir(parents=True, exist_ok=True)
    (out_dir / "package.json").write_text(_PACKAGE_JSON, encoding="utf-8")
    (out_dir / "tsconfig.json").write_text(_TSCONFIG_JSON, encoding="utf-8")
    (out_dir / "remotion.config.ts").write_text(_REMOTION_CONFIG_TS, encoding="utf-8")
    (src / "index.ts").write_text(_INDEX_TS, encoding="utf-8")
    (src / "Root.tsx").write_text(_ROOT_TSX, encoding="utf-8")
    (src / "CinematicPromo.tsx").write_text(_CINEMATIC_PROMO_TSX, encoding="utf-8")


def scaffold_project(storyboard: dict, out_dir: str | Path) -> dict:
    """Materialize a Remotion project for ``storyboard`` under ``out_dir``."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    template = _find_template_dir()
    used_template = False
    if template is not None:
        shutil.copytree(
            template,
            out,
            ignore=shutil.ignore_patterns("node_modules", ".git", "*.log", "out"),
            dirs_exist_ok=True,
        )
        used_template = True
    else:
        _write_baseline_project(out)

    public = out / "public"
    public.mkdir(parents=True, exist_ok=True)
    (public / "storyboard.json").write_text(
        json.dumps(storyboard, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    files_count = sum(1 for p in out.rglob("*") if p.is_file())
    return {
        "path": str(out),
        "entry": "src/index.ts",
        "composition": "CinematicPromo",
        "storyboard": str(public / "storyboard.json"),
        "files_count": files_count,
        "template": str(template) if used_template else "generated-baseline",
    }


def render(out_dir: str | Path, out_mp4: str | Path) -> dict:
    """Render the ``CinematicPromo`` composition. Requires Node >= 18 + Chromium."""
    project = Path(out_dir)
    if not project.is_dir():
        raise RemotionError(f"remotion project directory not found: {project}")
    out = Path(out_mp4)
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["npx", "--yes", "remotion", "render", "CinematicPromo", str(out)]
    try:
        proc = subprocess.run(
            cmd, cwd=str(project), capture_output=True, text=True, timeout=RENDER_TIMEOUT_S
        )
    except FileNotFoundError as exc:
        raise RemotionError("npx not found — Node.js is required for Remotion renders") from exc
    except subprocess.TimeoutExpired as exc:
        raise RemotionError(f"remotion render timed out after {RENDER_TIMEOUT_S}s") from exc
    if proc.returncode != 0:
        tail = "\n".join((proc.stderr or proc.stdout or "").strip().splitlines()[-20:])
        raise RemotionError(f"remotion render failed (exit {proc.returncode}): {tail}")
    return {
        "path": str(out),
        "command": " ".join(cmd),
        "renderer": "remotion",
        "size_bytes": out.stat().st_size if out.exists() else 0,
        "job_id": uuid.uuid4().hex[:8],  # correlation tag for logs
    }
