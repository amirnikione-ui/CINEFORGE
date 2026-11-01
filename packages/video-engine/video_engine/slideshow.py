"""Slideshow renderer: storyboard + frames + narration + music -> final mp4 (FFmpeg only).

Pipeline per scene: cover-scale the frame, apply motion (ken-burns / zoom / slide /
reveal via zoompan or time-based crop), overlay headline/body drawtext (palette-aware,
fade-in alpha), fade video in/out, encode an intermediate clip. Then concat all clips,
mix narration + music, and mux the final file (faststart, -shortest).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Optional

from . import ffmpeg_tools as ff

PLATFORM_DIMS: dict[str, tuple[int, int]] = {
    "instagram": (1080, 1920),
    "tiktok": (1080, 1920),
    "youtube": (1920, 1080),
    "web": (1920, 1080),
}

_ASPECT_MAP = {True: "9:16", False: "16:9"}


def _hex(value: str, default: str) -> str:
    v = str(value or default).lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    return "".join(ch for ch in v.lower() if ch in "0123456789abcdef")[:6].ljust(6, "0")


def _dims_for(storyboard: dict) -> tuple[int, int]:
    platform = str(storyboard.get("platform") or "instagram").lower()
    if platform in PLATFORM_DIMS:
        return PLATFORM_DIMS[platform]
    aspect = str(storyboard.get("aspect") or "9:16")
    return (1080, 1920) if aspect.startswith("9:16") else (1920, 1080)


def _scene_text_filters(
    scene: dict, W: int, H: int, palette: dict, fontfiles: dict, workdir: Path, index: int
) -> list[str]:
    """drawtext filters for headline + body, using textfiles to dodge escaping bugs."""
    headline = str(scene.get("headline") or "").strip()
    body = str(scene.get("body") or "").strip()
    filters: list[str] = []
    if not headline and not body:
        return filters

    text_col = "0x" + _hex(palette.get("text"), "f5f5ff")
    bold = fontfiles.get("bold")
    regular = fontfiles.get("regular")
    headline_size = max(40, min(110, int(W * 0.075)))
    body_size = max(18, min(40, int(W * 0.036)))

    def _textfile(name: str, content: str) -> str:
        p = workdir / f"{name}-{index:02d}.txt"
        p.write_text(content.replace("\n", " ").strip(), encoding="utf-8")
        return str(p).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")

    y_head = H * 0.72
    if headline:
        tf = _textfile("hl", headline)
        opts = [
            f"fontfile='{bold}'" if bold else None,
            f"textfile='{tf}'",
            f"fontsize={headline_size}",
            f"fontcolor={text_col}",
            "borderw=0",
            "shadowx=4",
            "shadowy=4",
            "shadowcolor=black@0.6",
            "x=(w-text_w)/2",
            f"y=(h*0.72)",
            "alpha='if(lt(t,0.6),t/0.6,1)'",
            "expansion=none",
        ]
        filters.append("drawtext=" + ":".join(o for o in opts if o))
    if body:
        y_body = H * (0.72 + (0.085 if headline else 0.0))
        tf = _textfile("bd", body)
        opts = [
            f"fontfile='{regular}'" if regular else None,
            f"textfile='{tf}'",
            f"fontsize={body_size}",
            f"fontcolor={text_col}",
            "borderw=0",
            "shadowx=2",
            "shadowy=2",
            "shadowcolor=black@0.5",
            "x=(w-text_w)/2",
            f"y={y_body:.0f}",
            "alpha='if(lt(t,0.8),t/0.8,1)'",
            "expansion=none",
        ]
        filters.append("drawtext=" + ":".join(o for o in opts if o))
    return filters


def _scene_input_args(style: str, dur: float, fps: int, frame: Path) -> list[str]:
    if style in ("ken-burns", "zoom"):
        # Single-frame input; zoompan generates the full frame count itself.
        return ["-i", str(frame)]
    return ["-loop", "1", "-framerate", str(fps), "-t", f"{dur:.3f}", "-i", str(frame)]


def _scene_motion_filters(
    scene: dict, index: int, dur: float, fps: int, W: int, H: int
) -> tuple[list[str], str]:
    motion = scene.get("motion") or {}
    style = str(motion.get("style") or "ken-burns").lower()
    intensity = max(0.0, min(1.0, float(motion.get("intensity", 0.6) or 0.6)))
    filters: list[str] = []
    frames = max(2, int(round(dur * fps)))

    if style in ("ken-burns", "zoom"):
        inc = 0.0006 + 0.0008 * intensity
        zmax = 1.0 + 0.12 + 0.25 * intensity
        if index % 2 == 0:  # zoom in
            zexpr = f"min(zoom+{inc:.5f},{zmax:.3f})"
        else:  # zoom out
            zexpr = f"if(lte(on,1),{zmax:.3f},max(zoom-{inc:.5f},1.001))"
        filters.append(f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}")
        filters.append(
            f"zoompan=z='{zexpr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={frames}:s={W}x{H}:fps={fps}"
        )
    elif style == "slide":
        pad = int(W * 0.12)
        filters.append(
            f"scale={W + pad}:{H + pad}:force_original_aspect_ratio=increase,crop={W + pad}:{H + pad}"
        )
        if index % 2 == 0:
            xexpr = f"(iw-ow)*(t/{dur:.3f})"
        else:
            xexpr = f"(iw-ow)*(1-t/{dur:.3f})"
        filters.append(f"crop={W}:{H}:x='{xexpr}':y=(ih-oh)/2")
    else:  # reveal / unknown -> static cover frame
        filters.append(f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}")
    return filters, style


def _render_scene_clip(
    scene: dict,
    index: int,
    total: int,
    frame: Path,
    clip_out: Path,
    W: int,
    H: int,
    fps: int,
    dur: float,
    palette: dict,
    fontfiles: dict,
    workdir: Path,
) -> Path:
    motion_filters, style = _scene_motion_filters(scene, index, dur, fps, W, H)
    filters: list[str] = list(motion_filters)
    filters.extend(_scene_text_filters(scene, W, H, palette, fontfiles, workdir, index))

    transition_in = str(scene.get("transition_in") or "fade").lower()
    fade_in_applied = False
    if style == "reveal":
        bg = "0x" + _hex(palette.get("bg"), "0a0a12")
        reveal_d = min(0.8, max(0.25, dur * 0.3))
        filters.append(f"fade=t=in:st=0:d={reveal_d:.2f}:color={bg}")
        fade_in_applied = True
    if not fade_in_applied and (index == 0 or transition_in != "cut"):
        filters.append("fade=t=in:st=0:d=0.25")
    filters.append(f"fade=t=out:st={max(0.0, dur - 0.25):.3f}:d=0.25")
    filters.append("format=yuv420p")
    filters.append("setsar=1")

    args = [
        *_scene_input_args(style, dur, fps, frame),
        "-vf", ",".join(filters),
        "-t", f"{dur:.3f}",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-r", str(fps),
        str(clip_out),
    ]
    ff.run_ffmpeg(args, timeout=600)
    if not clip_out.exists():
        raise ff.VideoEngineError(f"scene clip was not written: {clip_out}")
    return clip_out


def render_slideshow(
    storyboard: dict,
    frames: list[str | Path],
    narration_paths: list[str | Path],
    music_path: Optional[str | Path],
    out_path: str | Path,
    workdir: str | Path,
    progress_cb: Optional[Callable[[float], None]] = None,
) -> dict:
    """THE core pipeline: storyboard (schema v1) + per-scene frames + audio -> final mp4.

    All intermediate files live under ``workdir``; ``out_path`` is the deliverable.
    Returns ``{path, duration_s, width, height, fps, size_bytes}``.
    """
    if not isinstance(storyboard, dict) or not storyboard.get("scenes"):
        raise ff.VideoEngineError("render_slideshow: storyboard with scenes[] is required")

    scenes = storyboard["scenes"]
    W, H = _dims_for(storyboard)
    fps = int(storyboard.get("fps") or 30)
    palette = storyboard.get("palette") or {}
    fontfiles = ff.fonts()

    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    if len(frames) < len(scenes):
        raise ff.VideoEngineError(
            f"render_slideshow: need {len(scenes)} frames, got {len(frames)}"
        )

    total = sum(float(s.get("duration_s") or 0) for s in scenes)
    if total <= 0:
        raise ff.VideoEngineError("render_slideshow: scenes have no positive duration")

    def report(p: float) -> None:
        if progress_cb is not None:
            try:
                progress_cb(max(0.0, min(1.0, p)))
            except Exception:  # noqa: BLE001 - progress must never break a render
                pass

    # 1-2) per-scene clips
    clips: list[Path] = []
    for i, scene in enumerate(scenes):
        frame = Path(frames[i])
        if not frame.exists():
            raise ff.VideoEngineError(f"render_slideshow: missing frame {frame}")
        dur = float(scene.get("duration_s") or 0)
        if dur <= 0:
            raise ff.VideoEngineError(f"scene {scene.get('id', i)} has non-positive duration")
        clip = workdir / f"clip-{i:02d}.mp4"
        _render_scene_clip(
            scene, i, len(scenes), frame, clip, W, H, fps, dur, palette, fontfiles, workdir
        )
        clips.append(clip)
        report(0.02 + 0.65 * ((i + 1) / len(scenes)))

    # 3) concat -> silent video
    silent = workdir / "silent.mp4"
    ff.concat_clips(clips, silent)
    report(0.72)

    # 4) audio bed
    audio_out = workdir / "mix.m4a"
    ff.mix_audio([str(p) for p in narration_paths], music_path, total, audio_out)
    report(0.86)

    # 5) mux
    ff.run_ffmpeg(
        [
            "-i", str(silent),
            "-i", str(audio_out),
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            "-movflags", "+faststart",
            str(out),
        ],
        timeout=600,
    )
    report(0.97)

    info = ff.summary(out)
    result = {
        "path": str(out),
        "duration_s": info["duration_s"],
        "width": info["width"],
        "height": info["height"],
        "fps": info["fps"],
        "size_bytes": os.path.getsize(out),
    }
    report(1.0)
    return result
