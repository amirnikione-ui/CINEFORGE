import { FC } from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Backdrop } from "../components/Backdrop";
import { KenBurns } from "../components/KenBurns";
import { keywordLines } from "../content";
import { clamp01, px, rgba } from "../theme";
import type { SceneRenderProps } from "../types";

const PILL_STAGGER = 10;

// Feature scene ("feature" kind — renderer extension): headline up top, feature
// pills (from body, "|" separated) pop in staggered and bob gently.
export const FeatureScene: FC<SceneRenderProps> = ({
  scene,
  palette,
  width,
  height,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pills = keywordLines(scene);

  const headIn = interpolate(frame, [0, 18], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill>
      <KenBurns
        style={scene.motion?.style}
        intensity={scene.motion?.intensity}
        durationInFrames={durationInFrames}
      >
        <Backdrop seed={`${scene.id}:${scene.visual_prompt ?? ""}`} palette={palette} width={width} />
      </KenBurns>

      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", gap: px(46, width) }}>
        <span
          style={{
            fontSize: px(58, width),
            fontWeight: 800,
            letterSpacing: "0.05em",
            color: palette.text,
            textAlign: "center",
            opacity: headIn,
            transform: `translateY(${(1 - headIn) * px(24, width)}px)`,
          }}
        >
          {scene.headline ?? ""}
        </span>

        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: px(34, width) }}>
          {pills.map((label, i) => {
            const pop = spring({
              frame: frame - 16 - i * PILL_STAGGER,
              fps,
              config: { damping: 12, stiffness: 150, mass: 0.8 },
            });
            const bob = Math.sin((frame / fps) * Math.PI * 1.2 + i * 1.3) * px(6, width);
            return (
              <div
                key={`${label}-${i}`}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: px(20, width),
                  padding: `${px(20, width)}px ${px(40, width)}px`,
                  borderRadius: 999,
                  border: `1.5px solid ${rgba(palette.accent, 0.55)}`,
                  background: rgba(palette.bg, 0.6),
                  boxShadow: `0 0 ${px(40, width)}px ${rgba(palette.accent, 0.22)}`,
                  opacity: clamp01(pop),
                  transform: `translateY(${bob}px) scale(${interpolate(pop, [0, 1], [0.78, 1])})`,
                }}
              >
                <span
                  style={{
                    width: px(14, width),
                    height: px(14, width),
                    borderRadius: "50%",
                    background: i % 2 === 0 ? palette.accent : palette.primary,
                    boxShadow: `0 0 ${px(18, width)}px ${rgba(palette.accent, 0.8)}`,
                  }}
                />
                <span
                  style={{
                    fontSize: px(42, width),
                    fontWeight: 700,
                    letterSpacing: "0.02em",
                    color: palette.text,
                  }}
                >
                  {label}
                </span>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
