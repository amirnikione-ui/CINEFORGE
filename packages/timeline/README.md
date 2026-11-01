# packages/timeline — shared timeline model (M4)

One timeline data model consumed by both the editor UI (`apps/web` Timeline) and
the renderer (`packages/video-engine`), so what you see while editing is exactly
what renders (CF-050…052).

## v1 data model sketch

```ts
export interface Timeline {
  id: string;
  fps: number;
  durationInFrames: number;
  tracks: Track[];
  transitions: Transition[];
  animations: ClipAnimation[];
}

export type TrackKind = "video" | "audio" | "overlay";

export interface Track {
  id: string;
  kind: TrackKind;
  name: string;
  clips: Clip[];
  muted?: boolean;
  locked?: boolean;
}

export interface Clip {
  id: string;
  trackId: string;
  /** Half-open frame range [fromFrame, fromFrame + durationInFrames). */
  fromFrame: number;
  durationInFrames: number;
  source: ClipSource;
  label?: string;
}

export type ClipSource =
  | { type: "storyboard-scene"; sceneId: string }
  | { type: "asset"; assetId: string; kind: "video" | "audio" | "image" }
  | { type: "text"; text: string };

export interface Transition {
  id: string;
  aClipId: string;
  bClipId: string;
  atFrame: number;
  durationInFrames: number;
  kind: "fade" | "slide" | "cut" | "wipe";
}

export interface Keyframe<T = number> {
  frame: number;
  value: T;
  easing?: "linear" | "ease-in" | "ease-out" | "ease-in-out" | "spring";
}

export interface ClipAnimation {
  clipId: string;
  property: "opacity" | "scale" | "x" | "y" | "rotation" | "volume";
  keyframes: Keyframe[];
}
```

Design notes:

- **Frame-based** (integers at the project fps). Seconds are a serialization
  concern only — the Storyboard (schema v1) is seconds, the timeline is frames.
- A storyboard compiles losslessly into this model: scenes → clips on one video
  track, narration → clips on an audio track, `transition_in` → transitions.
- `ClipSource` is a tagged union so the UI can render icons per source kind
  without string sniffing.

## Consumers

- `apps/web` Timeline UI (agent-02): editing, drag/drop, preview scrubbing (M4).
- `packages/video-engine`: compiles the timeline into FFmpeg filtergraphs /
  Remotion props (M4).

## Status

**M4 — sketch.** Interfaces may shift when the editor prototype lands; any
contract change updates `docs/API_CONTRACTS.md` in the same PR (ADR-0007 §6).
