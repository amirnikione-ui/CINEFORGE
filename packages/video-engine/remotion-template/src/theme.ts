// Palette + geometry helpers. Every color/size in the comp flows through here so
// the storyboard fully drives the look — no hardcoded hex in scene components.

import type { Storyboard, StoryboardPalette } from "./types";

export interface Dimensions {
  width: number;
  height: number;
}

const HEX_RE = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i;

export function clamp01(value: number): number {
  return Math.min(1, Math.max(0, value));
}

/** "#rrggbb" | "#rgb" → "r,g,b" triplet for use inside rgba() / gradients. */
export function hexToRgbTriplet(hex: string): string {
  const normalized = hex.trim().replace("#", "");
  const full =
    normalized.length === 3
      ? normalized
          .split("")
          .map((c) => c + c)
          .join("")
      : normalized;
  const int = Number.parseInt(full.slice(0, 6), 16);
  if (Number.isNaN(int)) {
    return "0,0,0";
  }
  const r = (int >> 16) & 255;
  const g = (int >> 8) & 255;
  const b = int & 255;
  return `${r},${g},${b}`;
}

/** hex → `rgba(r, g, b, alpha)` with alpha clamped to 0..1. */
export function rgba(hex: string, alpha: number): string {
  return `rgba(${hexToRgbTriplet(hex)}, ${clamp01(alpha)})`;
}

export const FALLBACK_PALETTE: StoryboardPalette = {
  bg: "#0a0a12",
  primary: "#7c5cff",
  accent: "#00e5ff",
  text: "#f5f5ff",
};

/** Palette resolution with per-channel fallbacks — a partial palette never breaks a render. */
export function resolvePalette(
  p?: Partial<Record<keyof StoryboardPalette, unknown>>,
): StoryboardPalette {
  const resolved: StoryboardPalette = { ...FALLBACK_PALETTE };
  if (!p) {
    return resolved;
  }
  (Object.keys(FALLBACK_PALETTE) as Array<keyof StoryboardPalette>).forEach((key) => {
    const value = p[key];
    if (typeof value === "string" && HEX_RE.test(value.trim())) {
      resolved[key] = value.trim();
    }
  });
  return resolved;
}

/** aspect → canvas size. */
export const ASPECT_MAP: Record<string, Dimensions> = {
  "9:16": { width: 1080, height: 1920 },
  "16:9": { width: 1920, height: 1080 },
  "1:1": { width: 1080, height: 1080 },
  "4:5": { width: 1080, height: 1350 },
};

/** platform → default aspect (matches the contract's platform examples). */
export const PLATFORM_ASPECT: Record<string, string> = {
  instagram: "9:16",
  tiktok: "9:16",
  youtube: "16:9",
  web: "16:9",
};

/** Canvas for a storyboard: explicit aspect wins, else the platform default, else 9:16. */
export function resolveCanvas(storyboard: Pick<Storyboard, "aspect" | "platform">): Dimensions {
  const byAspect = ASPECT_MAP[storyboard.aspect];
  if (byAspect) {
    return byAspect;
  }
  const platformAspect = PLATFORM_ASPECT[storyboard.platform];
  if (platformAspect) {
    return ASPECT_MAP[platformAspect];
  }
  return ASPECT_MAP["9:16"];
}

/** Size scale relative to the 1080px reference width (font sizes, paddings, radii). */
export function px(base: number, width: number): number {
  return Math.round(base * (width / 1080));
}
