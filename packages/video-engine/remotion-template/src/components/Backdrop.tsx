import { FC } from "react";
import { AbsoluteFill } from "remotion";
import { px, rgba } from "../theme";
import type { StoryboardPalette } from "../types";

// Deterministic string hash (djb2) → stable blob layout per scene.
const hashSeed = (seed: string): number => {
  let hash = 5381;
  for (let i = 0; i < seed.length; i++) {
    hash = ((hash * 33) ^ seed.charCodeAt(i)) >>> 0;
  }
  return hash;
};

/**
 * Procedural cinematic backdrop: gradient blobs + vignette derived from a scene
 * seed (id + visual_prompt). Stands in for generated concept frames — once the
 * image providers land, their stills composite right here.
 */
export const Backdrop: FC<{
  seed: string;
  palette: StoryboardPalette;
  width: number;
}> = ({ seed, palette, width }) => {
  const h = hashSeed(seed || "cineforge");
  const angle = h % 360;
  const blobAX = 16 + (h % 42);
  const blobAY = 10 + ((h >>> 3) % 44);
  const blobBX = 52 + ((h >>> 6) % 38);
  const blobBY = 50 + ((h >>> 9) % 40);

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(circle at ${blobAX}% ${blobAY}%, ${rgba(
            palette.primary,
            0.4,
          )}, transparent 56%), radial-gradient(circle at ${blobBX}% ${blobBY}%, ${rgba(
            palette.accent,
            0.22,
          )}, transparent 52%), linear-gradient(${angle}deg, ${rgba(
            palette.primary,
            0.12,
          )}, transparent 60%)`,
          filter: `blur(${px(10, width)}px)`,
          // Overscale to hide the blur edge bleed.
          transform: "scale(1.08)",
        }}
      />
      <AbsoluteFill
        style={{
          background: `radial-gradient(circle at 50% 46%, transparent 52%, ${rgba(
            "#000000",
            0.5,
          )} 100%)`,
        }}
      />
    </AbsoluteFill>
  );
};
