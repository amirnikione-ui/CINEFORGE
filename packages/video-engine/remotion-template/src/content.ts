// Scene-content parsing shared by the typography and feature scenes.

import type { Scene } from "./types";

/**
 * Keyword list for a scene: `body` split on "|" (preferred) or ",",
 * falling back to headline words. Capped at `max` entries.
 * Example body: "ADAPTIVE CUSHIONING | NEON TRAIL GRIP | 214 G FEATHERLIGHT"
 */
export function keywordLines(scene: Scene, max = 3): string[] {
  const source = (scene.body ?? "").trim();
  if (source.length > 0) {
    const separator = source.includes("|") ? "|" : ",";
    const parts = source
      .split(separator)
      .map((part) => part.trim())
      .filter(Boolean);
    if (parts.length > 0) {
      return parts.slice(0, max);
    }
  }
  return (scene.headline ?? "")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, max);
}
