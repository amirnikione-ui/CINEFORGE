"""Slideshow renderer — storyboard JSON → cinematic MP4 (pure FFmpeg, ADR-0006).

Pipeline (each step argv-only, workspace-confined):
  1. per-scene clip: PNG (or color fallback) → zoompan motion + drawtext
     typography (palette colors, fade-in) + scale/pad → scene-XX.mp4
  2. joins: xfade chain (fade/slide/cut→1-frame fade)
  3. audio: per-scene narration delayed to scene starts + music with
     side-chain ducking → aac
  4. subtitles: SRT from narration timing → burn-in
  5. conform: platform scale/pad, yuv420p, +faststart
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from .ffmpeg_tools import (concat_xfade_plan, drawtext_filter, ffmpeg_bin, find_font,
                           scale_pad_filter, xfade_name)

_PRESETS = {
    "9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080), "4:5": (1080, 1350),
}


def dims_for(aspect: str) -> tuple[int, int]:
    return _PRESETS.get(aspect, _PRESETS["9:16"])


async def _run(cmd: list[str], timeout: int = 900) -> None:
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        _, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except TimeoutError:
        proc.kill()
        raise RuntimeError("ffmpeg timeout")
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {err.decode(errors='replace')[-400:]}")


# ------------------------------------------------------- scene clip build ----

def _motion_filter(style: str, intensity: float, dur_s: float, w: int, h: int) -> str:
    fps = 30
    frames = max(2, int(dur_s * fps))
    k = 0.06 + 0.14 * float(intensity)  # zoom span
    pre = f"scale={w * 4}:{h * 4}:force_original_aspect_ratio=increase,crop={w * 4}:{h * 4}"
    if style == "zoom":
        z = f"1+{k:.4f}*in/{frames}"
        x = "(iw-iw/zoom)/2"
        y = "(ih-ih/zoom)/2"
    elif style == "reveal":
        z = f"{1 + k:.4f}-{k:.4f}*in/{frames}"
        x = "(iw-iw/zoom)/2"
        y = "(ih-ih/zoom)/2"
    elif style == "slide":
        z = f"{1 + k / 2:.4f}"
        x = f"(iw-iw/zoom)*in/{frames}"
        y = "(ih-ih/zoom)/2"
    else:  # ken-burns: slow push + slight upward drift
        z = f"1+{k:.4f}*in/{frames}"
        x = f"(iw-iw/zoom)/2 + (iw-iw/zoom)*0.05*in/{frames}"
        y = f"(ih-ih/zoom)/2 - (ih-ih/zoom)*0.05*in/{frames}"
    return f"{pre},zoompan=z='{z}':x='{x}':y='{y}':d=1:s={w}x{h}:fps={fps}"


def _scene_text_filters(scene: dict[str, Any], dur_s: float, w: int, h: int,
                        palette: dict[str, str]) -> list[str]:
    text_color = palette.get("text", "#f5f5ff").lstrip("#")
    accent = palette.get("accent", "#00e5ff").lstrip("#")
    headline = (scene.get("headline") or "").strip()
    body = (scene.get("body") or "").strip()
    filters: list[str] = []
    if not find_font():
        return filters  # honest: no typography without a font; frames still render
    if headline:
        size = int(h * (0.075 if scene.get("kind") in ("typography", "outro") else 0.065))
        y = f"h*0.32" if scene.get("kind") in ("hook", "reveal") else "h*0.42"
        filters.append(drawtext_filter(
            headline, size=size, color=f"0x{text_color}", y_expr=y,
            fade_in=0.5, fade_out_at=max(0.5, dur_s - 0.6)))
    if body:
        filters.append(drawtext_filter(
            body, size=int(h * 0.028), color=f"0x{accent}", y_expr="h*0.42",
            fade_in=0.9, fade_out_at=max(0.9, dur_s - 0.6)))
    if scene.get("kind") == "outro":
        filters.append(drawtext_filter(
            "CINEFORGE", size=int(h * 0.02), color=f"0x{accent}@0.8",
            y_expr="h*0.92", fade_in=1.0))
    return filters


async def render_scene_clip(
    scene: dict[str, Any], frame_path: Path | None, out_path: Path,
    *, w: int, h: int, palette: dict[str, str],
) -> None:
    dur = float(scene.get("duration_s", 4.0))
    motion = (scene.get("motion") or {})
    style = motion.get("style", "ken-burns")
    intensity = float(motion.get("intensity", 0.6))
    vf = [_motion_filter(style, intensity, dur, w, h)]
    vf += _scene_text_filters(scene, dur, w, h, palette)
    if frame_path and frame_path.exists():
        src = ["-loop", "1", "-t", f"{dur:.3f}", "-i", str(frame_path)]
    else:
        # honest fallback: palette background instead of a missing asset
        bg = (palette.get("bg") or "#0a0a12").lstrip("#")
        src = ["-f", "lavfi", "-t", f"{dur:.3f}",
               "-i", f"color=c=0x{bg}:s={w}x{h}:r=30"]
    cmd = [ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error", *src,
           "-vf", ",".join(vf), "-frames:v", str(int(dur * 30)),
           "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
           "-pix_fmt", "yuv420p", str(out_path)]
    await _run(cmd)


# ------------------------------------------------------------- full render ----

async def render_slideshow(
    storyboard: dict[str, Any], frame_paths: list[Path | None],
    narration_paths: list[Path | None], music_path: Path | None,
    out_path: Path, workdir: Path,
) -> dict[str, Any]:
    scenes = storyboard.get("scenes", [])
    if not scenes:
        raise ValueError("storyboard has no scenes")
    w, h = dims_for(storyboard.get("aspect", "9:16"))
    palette = storyboard.get("palette", {})
    workdir.mkdir(parents=True, exist_ok=True)

    # 1. scene clips
    clips: list[Path] = []
    for i, scene in enumerate(scenes):
        clip = workdir / f"scene-{i + 1:02d}.mp4"
        await render_scene_clip(scene, frame_paths[i] if i < len(frame_paths) else None,
                                clip, w=w, h=h, palette=palette)
        clips.append(clip)

    # 2. xfade chain
    durations = [float(s.get("duration_s", 4.0)) for s in scenes]
    transitions = [s.get("transition_in", "fade") for s in scenes]
    plan = concat_xfade_plan(durations, transitions)
    silent = workdir / "visual.mp4"
    if len(clips) == 1:
        await _run(
            [ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error", "-i", str(clips[0]),
             "-c", "copy", str(silent)])
    else:
        inputs: list[str] = []
        for c in clips:
            inputs += ["-i", str(c)]
        parts: list[str] = []
        prev = "[0:v]"
        for i in range(1, len(clips)):
            name, fdur = xfade_name(transitions[i] if i < len(transitions) else "fade")
            out_lbl = f"[v{i}]" if i < len(clips) - 1 else "[vout]"
            parts.append(
                f"{prev}[{i}:v]xfade=transition={name}:duration={fdur:.2f}"
                f":offset={plan['offsets'][i - 1]:.3f}{out_lbl}")
            prev = out_lbl
        cmd = [ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error", *inputs,
               "-filter_complex", ";".join(parts), "-map", "[vout]",
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
               "-pix_fmt", "yuv420p", "-r", "30", str(silent)]
        await _run(cmd)
    duration = plan["duration"]

    # 3+4+5. audio mix, subtitles, conform → final
    final = await _master(silent, scenes, durations, transitions, narration_paths,
                          music_path, out_path, workdir, w, h, duration)
    return {"duration_s": duration, "width": w, "height": h, "scenes": len(scenes),
            "plan": plan, "output": str(final)}


async def _master(
    silent: Path, scenes: list[dict[str, Any]], durations: list[float],
    transitions: list[str], narrations: list[Path | None], music: Path | None,
    out_path: Path, workdir: Path, w: int, h: int, duration: float,
) -> Path:
    # narration delays = xfade scene starts
    plan = concat_xfade_plan(durations, transitions)
    starts = [0.0] + plan["offsets"]

    srt_segments = []
    for i, scene in enumerate(scenes):
        text = (scene.get("narration") or "").strip()
        if not text:
            continue
        srt_segments.append({"start_s": starts[i] + 0.2,
                             "end_s": starts[i] + min(durations[i] - 0.4, 0.2 + len(text) * 0.055),
                             "text": text})
    srt_path = workdir / "subtitles.srt"
    from .ffmpeg_tools import build_srt

    srt_path.write_text(build_srt(srt_segments), encoding="utf-8")

    inputs: list[str] = ["-i", str(silent)]
    narration_idx: list[int] = []
    for p in narrations:
        if p and Path(p).exists():
            inputs += ["-i", str(p)]
            narration_idx.append(len(inputs) // 2 - 1)
    music_idx = None
    if music and Path(music).exists():
        inputs += ["-i", str(music)]
        music_idx = len(inputs) // 2 - 1

    fc: list[str] = []
    mix_label = "[aout]"
    if narration_idx:
        delays = []
        for k, ni in enumerate(narration_idx):
            ms = int(starts[min(k, len(starts) - 1)] * 1000)
            delays.append(f"[{ni}:a]adelay={ms}|{ms}[n{k}]")
        fc += delays
        nar_mix = "".join(f"[n{k}]" for k in range(len(narration_idx)))
        fc.append(f"{nar_mix}amix=inputs={len(narration_idx)}:normalize=0[nar]")
        if music_idx is not None:
            fc.append("[nar]asplit=2[nar1][nar2]")
            fc.append(f"[{music_idx}:a]volume=0.9[mus]")
            fc.append("[mus][nar1]sidechaincompress=threshold=0.03:ratio=6:attack=60:"
                      "release=400:makeup=1[duck]")
            fc.append("[nar2][duck]amix=inputs=2:duration=longest:normalize=0,apad[mix]")
        else:
            fc.append("[nar]apad[mix]")
    elif music_idx is not None:
        fc.append(f"[{music_idx}:a]volume=0.9,apad[mix]")
    else:
        fc.append("anullsrc=channel_layout=stereo:sample_rate=44100,apad[mix]")
    fc.append(f"[mix]atrim=0:{duration:.3f},afade=t=out:st={max(0.0, duration - 1.0):.3f}:d=1"
              f",aformat=sample_rates=44100:channel_layouts=stereo[aout]")

    vf = [scale_pad_filter(w, h)]
    if srt_segments and find_font():
        srt_escaped = str(srt_path).replace("\\", "/").replace(":", "\\:")
        vf.append(f"subtitles={srt_escaped}:force_style='FontSize=14,Outline=1,"
                  f"MarginV=60,Alignment=2'")

    cmd = [ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error", *inputs,
           "-filter_complex", ";".join(fc), "-map", "0:v:0", "-map", "[aout]",
           "-vf", ",".join(vf), "-t", f"{duration:.3f}",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out_path)]
    await _run(cmd)
    return out_path
