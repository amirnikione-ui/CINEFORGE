// Mirror of the CINEFORGE Storyboard JSON schema v1 — docs/API_CONTRACTS.md.
// Keep field names EXACTLY as the contract (snake_case): the backend writes this
// shape verbatim. NOTE: `kind` additionally accepts "feature", a renderer
// extension used by the example storyboard; unknown kinds fall back to the
// typography scene at parse time (src/parse.ts).

export type Platform = "instagram" | "tiktok" | "youtube" | "web";

export type SceneKind = "hook" | "reveal" | "typography" | "feature" | "outro";

export type MotionStyle = "ken-burns" | "slide" | "zoom" | "reveal";

export type TransitionKind = "fade" | "cut" | "slide";

export interface StoryboardPalette {
  bg: string;
  primary: string;
  accent: string;
  text: string;
}

export interface SceneMotion {
  style: MotionStyle;
  /** 0..1 — drives ken-burns zoom depth and drift distance. */
  intensity: number;
}

export interface Scene {
  id: string;
  kind: SceneKind;
  /** Seconds. sum(scenes[].duration_s) ≈ duration_target_s (±10% per contract). */
  duration_s: number;
  headline?: string;
  body?: string;
  narration?: string;
  visual_prompt?: string;
  motion?: SceneMotion;
  transition_in?: TransitionKind;
}

export interface Storyboard {
  schema_version: number;
  title: string;
  platform: Platform;
  /** "9:16" | "16:9" | "1:1" | "4:5" — free string in the contract, mapped in theme.ts. */
  aspect: string;
  fps: number;
  duration_target_s: number;
  palette: StoryboardPalette;
  music_mood?: string;
  scenes: Scene[];
}

/** Props every scene component receives from CinematicPromo. */
export interface SceneRenderProps {
  scene: Scene;
  palette: StoryboardPalette;
  width: number;
  height: number;
  /** Scene length in frames (sequence-local — NOT the composition duration). */
  durationInFrames: number;
}
