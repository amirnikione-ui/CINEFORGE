import { FC } from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";

// CSS-only film grain: feTurbulence SVG tile, very low opacity, overlay blend.
// The tile is nudged each frame so the grain shimmers instead of sitting still.
const NOISE_TILE = `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300'%3E%3Cfilter id='grain'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23grain)'/%3E%3C/svg%3E")`;

export const GrainOverlay: FC = () => {
  const frame = useCurrentFrame();
  const jitterX = (frame % 5) * 11;
  const jitterY = (frame % 7) * 7;

  return (
    <AbsoluteFill
      style={{
        backgroundImage: NOISE_TILE,
        backgroundSize: "300px 300px",
        backgroundPosition: `${-jitterX}px ${-jitterY}px`,
        opacity: 0.05,
        mixBlendMode: "overlay",
        pointerEvents: "none",
      }}
    />
  );
};
