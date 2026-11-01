// Runtime normalizer for incoming storyboard JSON (schema v1).
// The backend sends this shape, but the renderer never trusts raw input:
// coerce, clamp and default here so a partial payload still renders honestly.

import { clamp01, resolvePalette } from "./theme";
import type {
  MotionStyle,
  Platform,
  Scene,
  SceneKind,
  Storyboard,
  TransitionKind,
} from "./types";

const SCENE_KINDS: readonly SceneKind[] = ["hook", "reveal", "typography", "feature", "outro"];
const MOTION_STYLES: readonly MotionStyle[] = ["ken-burns", "slide", "zoom", "reveal"];
const TRANSITIONS: readonly TransitionKind[] = ["fade", "cut", "slide"];
const PLATFORMS: readonly Platform[] = ["instagram", "tiktok", "youtube", "web"];

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

const asString = (value: unknown): string | undefined =>
  typeof value === "string" && value.trim().length > 0 ? value : undefined;

const asNumber = (value: unknown): number | undefined =>
  typeof value === "number" && Number.isFinite(value) ? value : undefined;

const oneOf = <T extends string>(value: unknown, allowed: readonly T[], fallback: T): T =>
  allowed.includes(value as T) ? (value as T) : fallback;

export function parseStoryboard(input: unknown): Storyboard {
  const data = isRecord(input) ? input : {};
  const paletteRaw = isRecord(data.palette) ? data.palette : undefined;
  const scenesRaw = Array.isArray(data.scenes) ? data.scenes : [];

  const scenes: Scene[] = scenesRaw.map((raw, index): Scene => {
    const scene = isRecord(raw) ? raw : {};
    const motion = isRecord(scene.motion) ? scene.motion : {};
    return {
      id: asString(scene.id) ?? `scene-${String(index + 1).padStart(2, "0")}`,
      kind: oneOf(scene.kind, SCENE_KINDS, "typography"),
      duration_s: Math.max(0.2, asNumber(scene.duration_s) ?? 3),
      headline: asString(scene.headline),
      body: asString(scene.body),
      narration: asString(scene.narration),
      visual_prompt: asString(scene.visual_prompt),
      motion: {
        style: oneOf(motion.style, MOTION_STYLES, "ken-burns"),
        intensity: clamp01(asNumber(motion.intensity) ?? 0.5),
      },
      transition_in: oneOf(scene.transition_in, TRANSITIONS, "fade"),
    };
  });

  return {
    schema_version: asNumber(data.schema_version) ?? 1,
    title: asString(data.title) ?? "Untitled CINEFORGE promo",
    platform: oneOf(data.platform, PLATFORMS, "instagram"),
    aspect: asString(data.aspect) ?? "9:16",
    fps: Math.max(1, Math.round(asNumber(data.fps) ?? 30)),
    duration_target_s:
      asNumber(data.duration_target_s) ?? scenes.reduce((acc, s) => acc + s.duration_s, 0),
    palette: resolvePalette(paletteRaw),
    music_mood: asString(data.music_mood),
    scenes,
  };
}
