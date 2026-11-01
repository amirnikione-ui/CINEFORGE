"""Timeline IR + FFmpeg plan compiler.

Timeline JSON is CINEFORGE's central rendering contract (D-006):
    tracks -> clips (color / text / image / video / audio) -> styles & animation

compile_ffmpeg_plan() lowers a Timeline into an ordered list of shell-safe steps:
    1. render every visual/audio clip to an isolated segment file
    2. concat visual segments
    3. mix audio segments (+ optional music bed) onto the final duration
    4. mux/scale/normalize with faststart

v0 by AGENT-1; AGENT-4 owns upgrading to single-graph filter_complex and more
clip kinds while keeping this public API compatible.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------- dataclasses


@dataclass
class Animation:
    fade_in: float = 0.0
    fade_out: float = 0.0

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "Animation":
        data = data or {}
        return cls(
            fade_in=float(data.get("in", data.get("fade_in", 0)) or 0),
            fade_out=float(data.get("out", data.get("fade_out", 0)) or 0),
        )


@dataclass
class Clip:
    id: str
    kind: str  # color | text | image | video | audio
    start: float
    duration: float
    color: str | None = None
    text: str | None = None
    asset_path: str | None = None
    style: dict[str, Any] = field(default_factory=dict)
    animation: Animation = field(default_factory=Animation)
    volume: float = 1.0

    @property
    def end(self) -> float:
        return self.start + self.duration

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Clip":
        return cls(
            id=str(data.get("id", "clip")),
            kind=str(data.get("kind", "color")),
            start=float(data.get("start", 0)),
            duration=max(float(data.get("duration", 1)), 0.04),
            color=data.get("color"),
            text=data.get("text"),
            asset_path=data.get("asset_path"),
            style=dict(data.get("style") or {}),
            animation=Animation.from_dict(data.get("animation")),
            volume=float(data.get("volume", 1.0)),
        )


@dataclass
class Track:
    name: str
    kind: str  # background | video | text | audio | overlay
    clips: list[Clip] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Track":
        return cls(
            name=str(data.get("name", "track")),
            kind=str(data.get("kind", "video")),
            clips=[Clip.from_dict(c) for c in data.get("clips", [])],
        )


@dataclass
class Timeline:
    fps: int = 30
    width: int = 1920
    height: int = 1080
    background: str = "#0A0C10"
    tracks: list[Track] = field(default_factory=list)

    def visual_clips(self) -> list[Clip]:
        clips: list[Clip] = []
        for track in self.tracks:
            if track.kind in ("background", "video", "text", "overlay"):
                clips.extend(track.clips)
        return sorted(clips, key=lambda c: c.start)

    def audio_clips(self) -> list[Clip]:
        clips: list[Clip] = []
        for track in self.tracks:
            if track.kind == "audio":
                clips.extend(track.clips)
        return sorted(clips, key=lambda c: c.start)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Timeline":
        return cls(
            fps=int(data.get("fps", 30)),
            width=int(data.get("width", 1920)),
            height=int(data.get("height", 1080)),
            background=str(data.get("background", "#0A0C10")),
            tracks=[Track.from_dict(t) for t in data.get("tracks", [])],
        )


def timeline_from_dict(data: dict[str, Any]) -> Timeline:
    return Timeline.from_dict(data)


def timeline_to_dict(tl: Timeline) -> dict[str, Any]:
    def clip_dict(c: Clip) -> dict[str, Any]:
        out: dict[str, Any] = {"id": c.id, "kind": c.kind, "start": c.start, "duration": c.duration}
        for key in ("color", "text", "asset_path"):
            if getattr(c, key) is not None:
                out[key] = getattr(c, key)
        if c.style:
            out["style"] = c.style
        if c.animation.fade_in or c.animation.fade_out:
            out["animation"] = {"in": c.animation.fade_in, "out": c.animation.fade_out}
        if c.volume != 1.0:
            out["volume"] = c.volume
        return out

    return {
        "version": 1,
        "fps": tl.fps,
        "width": tl.width,
        "height": tl.height,
        "background": tl.background,
        "tracks": [
            {"name": t.name, "kind": t.kind, "clips": [clip_dict(c) for c in t.clips]}
            for t in tl.tracks
        ],
    }


def total_duration(tl: Timeline) -> float:
    end = 0.0
    for track in tl.tracks:
        for clip in track.clips:
            end = max(end, clip.end)
    return end


# ------------------------------------------------------------------- ffmpeg plan


@dataclass
class Step:
    """One ordered ffmpeg invocation (args exclude the binary itself)."""

    name: str
    args: list[str]
    description: str = ""


@dataclass
class FFmpegPlan:
    steps: list[Step]
    output_path: str
    width: int
    height: int
    fps: int
    duration: float

    @property
    def command_count(self) -> int:
        return len(self.steps)


def _hex_to_ffmpeg_color(color: str, default: str = "black") -> str:
    if not color:
        return default
    value = color.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) in (6, 8) and all(ch in "0123456789abcdefABCDEF" for ch in value):
        return f"0x{value}"
    return default


def _escape_drawtext(text: str) -> str:
    replacements = {
        "\\": "\\\\",
        ":": "\\:",
        "'": "\u2019",  # typographic apostrophe avoids filter escaping pain
        '"': "",
        "%": "\\%",
        "\n": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def _escape_expr(expr: str) -> str:
    """Escape commas/colons for use inside filter option expressions."""
    return expr.replace(",", "\\,").replace(":", "\\:")


def _fade_alpha_expr(duration: float, fade_in: float, fade_out: float) -> str | None:
    """drawtext alpha expression with per-clip fades (commas escaped)."""
    fi = min(fade_in, duration / 2)
    fo = min(fade_out, duration / 2)
    inner = "1"
    if fo > 0:
        out_start = max(duration - fo, 0)
        inner = f"if(gt(t,{out_start:.3f}),({duration:.3f}-t)/{fo:.3f},1)"
    if fi > 0:
        inner = f"if(lt(t,{fi:.3f}),t/{fi:.3f},{inner})"
    return _escape_expr(inner)


def _font_file() -> str:
    return os.environ.get(
        "FONT_FILE", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    )


def _segment_args(clip: Clip, tl: Timeline, out_path: str) -> list[str]:
    """Build args rendering one clip in isolation to out_path."""
    w, h, fps = tl.width, tl.height, tl.fps
    if clip.kind == "color":
        color = _hex_to_ffmpeg_color(clip.color or tl.background)
        return [
            "-f", "lavfi", "-i", f"color=c={color}:s={w}x{h}:r={fps}:d={clip.duration:.3f}",
            "-t", f"{clip.duration:.3f}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", out_path,
        ]
    if clip.kind == "text":
        # Text clips are composited in the FINAL pass (drawtext over the
        # concatenated base) — they must not extend the timeline duration.
        raise ValueError("text clips are composited in the final pass, not as segments")
    if clip.kind in ("image", "video"):
        if not clip.asset_path or not os.path.exists(clip.asset_path):
            # Missing asset: fall back to a dark segment so renders never dead-end.
            bg = _hex_to_ffmpeg_color(tl.background)
            return [
                "-f", "lavfi", "-i", f"color=c={bg}:s={w}x{h}:r={fps}:d={clip.duration:.3f}",
                "-t", f"{clip.duration:.3f}",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", out_path,
            ]
        if clip.kind == "image":
            loops = f"-loop 1 -t {clip.duration:.3f}".split()
            return [
                *loops, "-i", clip.asset_path,
                "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,fps={fps}",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", out_path,
            ]
        trim = ["-ss", f"{clip.start:.3f}"] if clip.style.get("seek") else []
        return [
            *trim, "-i", clip.asset_path,
            "-t", f"{clip.duration:.3f}",
            "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,fps={fps}",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", out_path,
        ]
    # Unknown visual kind -> safe dark segment
    bg = _hex_to_ffmpeg_color(tl.background)
    return [
        "-f", "lavfi", "-i", f"color=c={bg}:s={w}x{h}:r={fps}:d={clip.duration:.3f}",
        "-t", f"{clip.duration:.3f}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", out_path,
    ]


def _audio_segment_args(clip: Clip, out_path: str) -> list[str] | None:
    if not clip.asset_path or not os.path.exists(clip.asset_path):
        return None
    vol = max(0.0, min(clip.volume, 4.0))
    return [
        "-i", clip.asset_path,
        "-t", f"{clip.duration:.3f}",
        "-af", f"volume={vol:.2f}",
        "-ar", "44100", "-ac", "2",
        "-c:a", "aac", "-b:a", "192k",
        out_path,
    ]


def _text_overlay_filters(text_clips: list[Clip]) -> list[str]:
    """One drawtext filter per text clip, composited on global timeline time."""
    filters: list[str] = []
    font = _font_file()
    for clip in text_clips:
        size = int(clip.style.get("font_size", 96))
        color = _hex_to_ffmpeg_color(clip.style.get("color", "#FFFFFF"), "white")
        end = clip.start + clip.duration
        enable = _escape_expr(f"between(t,{clip.start:.3f},{end:.3f})")
        alpha = _fade_alpha_expr(clip.duration, clip.animation.fade_in, clip.animation.fade_out)
        text_arg = _escape_drawtext(clip.text or "")
        parts = [
            f"drawtext=fontfile={font}",
            f"text='{text_arg}'",
            f"fontsize={size}",
            f"fontcolor={color}",
            "x=(w-text_w)/2",
            f"y=(h-text_h)/2",
            f"enable='{enable}'",
        ]
        if alpha:
            parts.append(f"alpha='{alpha}'")
        filters.append(":".join(parts))
    return filters


def compile_ffmpeg_plan(tl: Timeline, output_path: str, work_dir: str) -> FFmpegPlan:
    """Lower a Timeline into ordered ffmpeg steps writing to output_path.

    Pipeline: base segments (color/image/video) -> concat -> drawtext overlays ->
    audio mix/mux. Text never inflates duration; missing assets never dead-end.
    """
    os.makedirs(work_dir, exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
    duration = total_duration(tl)
    steps: list[Step] = []

    base_clips = [c for c in tl.visual_clips() if c.kind != "text"]
    text_clips = [c for c in tl.visual_clips() if c.kind == "text"]

    base_segments: list[str] = []
    for idx, clip in enumerate(base_clips):
        seg = os.path.join(work_dir, f"v{idx:03d}_{clip.id}.mp4")
        steps.append(Step(f"segment:{clip.id}", _segment_args(clip, tl, seg),
                          f"render clip {clip.id} ({clip.kind})"))
        base_segments.append(seg)

    audio_segments: list[str] = []
    for idx, clip in enumerate(tl.audio_clips()):
        seg = os.path.join(work_dir, f"a{idx:03d}_{clip.id}.m4a")
        args = _audio_segment_args(clip, seg)
        if args:
            steps.append(Step(f"audio:{clip.id}", args, f"prepare audio {clip.id}"))
            audio_segments.append(seg)

    if not base_segments:
        color = _hex_to_ffmpeg_color(tl.background)
        fallback = os.path.join(work_dir, "base_empty.mp4")
        steps.append(Step(
            "segment:base",
            ["-f", "lavfi", "-i", f"color=c={color}:s={tl.width}x{tl.height}:r={tl.fps}:d={max(duration, 1.0):.3f}",
             "-t", f"{max(duration, 1.0):.3f}", "-c:v", "libx264", "-pix_fmt", "yuv420p", fallback],
            "empty timeline fallback",
        ))
        base_segments = [fallback]

    # 1) concat base segments (same codec/size/rate -> demuxer concat is exact)
    concat_list = os.path.join(work_dir, "concat.txt")
    with open(concat_list, "w", encoding="utf-8") as fh:
        for seg in base_segments:
            fh.write(f"file '{os.path.abspath(seg)}'\n")
    base_video = os.path.join(work_dir, "base_video.mp4")
    steps.append(Step(
        "concat",
        ["-f", "concat", "-safe", "0", "-i", concat_list, "-c", "copy", base_video],
        "concatenate visual segments",
    ))

    has_text = bool(text_clips)
    has_audio = bool(audio_segments)

    if has_audio:
        audio_list = os.path.join(work_dir, "audio_concat.txt")
        with open(audio_list, "w", encoding="utf-8") as fh:
            for seg in audio_segments:
                fh.write(f"file '{os.path.abspath(seg)}'\n")
        audio_concat = os.path.join(work_dir, "audio_concat.m4a")
        steps.append(Step(
            "audio:concat",
            ["-f", "concat", "-safe", "0", "-i", audio_list, "-c", "copy", audio_concat],
            "concatenate audio segments",
        ))

    # 2) final pass: overlays + audio
    final_args: list[str] = ["-i", base_video]
    if has_audio:
        final_args += ["-i", audio_concat]
    if has_text:
        final_args += ["-vf", ",".join(_text_overlay_filters(text_clips))]
    if has_audio:
        final_args += ["-map", "0:v:0", "-map", "1:a:0", "-af", "apad"]
        final_args += ["-c:v", "libx264" if has_text else "copy", "-c:a", "aac", "-b:a", "192k",
                       "-shortest", "-movflags", "+faststart"]
    else:
        final_args += ["-c:v", "libx264" if has_text else "copy",
                       "-movflags", "+faststart"]
    final_args.append(output_path)
    steps.append(Step("finalize", final_args,
                      "text overlays + audio mux + faststart"))

    return FFmpegPlan(steps, output_path, tl.width, tl.height, tl.fps, duration)


# ------------------------------------------------------------- remotion bridge


def to_remotion_props(tl: Timeline) -> dict[str, Any]:
    """Project a Timeline into Remotion <Composition defaultProps> shape."""
    scenes: list[dict[str, Any]] = []
    fps = tl.fps
    for clip in tl.visual_clips():
        scenes.append({
            "id": clip.id,
            "kind": clip.kind,
            "fromFrame": round(clip.start * fps),
            "durationInFrames": max(round(clip.duration * fps), 1),
            "text": clip.text,
            "color": clip.color or clip.style.get("color"),
            "assetPath": clip.asset_path,
            "fontSize": clip.style.get("font_size"),
        })
    audio = [
        {
            "id": c.id, "assetPath": c.asset_path, "volume": c.volume,
            "fromFrame": round(c.start * fps), "durationInFrames": max(round(c.duration * fps), 1),
        }
        for c in tl.audio_clips()
    ]
    return {
        "fps": fps,
        "width": tl.width,
        "height": tl.height,
        "background": tl.background,
        "scenes": scenes,
        "audio": audio,
        "durationInFrames": max(round(total_duration(tl) * fps), 1),
    }
