import { FC } from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Backdrop } from "../components/Backdrop";
import { KenBurns } from "../components/KenBurns";
import { clamp01, px, rgba } from "../theme";
import type { SceneRenderProps } from "../types";

// Outro: the headline scales down into a centered logo lockup, the CTA line
// (scene.body) types on with a blinking cursor, then the scene fades to bg.
export const OutroScene: FC<SceneRenderProps> = ({
  scene,
  palette,
  width,
  height,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const lockIn = spring({
    frame,
    fps,
    config: { damping: 15, stiffness: 80, mass: 0.9 },
  });
  const scale = interpolate(lockIn, [0, 1], [1.7, 1]);

  const cta = (scene.body ?? "Follow for more").trim();
  const typeStart = 18;
  const typeEnd = Math.max(
    typeStart + 12,
    Math.min(typeStart + cta.length * 1.5, durationInFrames - 40),
  );
  const charCount = interpolate(frame, [typeStart, typeEnd], [0, cta.length], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const typed = cta.slice(0, Math.round(charCount));
  const cursorOn = frame > typeStart - 6 && frame % 24 < 12;

  const fadeOutStart = Math.max(0, durationInFrames - 26);
  const fadeOut = interpolate(frame, [fadeOutStart, Math.max(1, durationInFrames - 1)], [0, 1], {
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
        <Backdrop seed={`${scene.id}:${scene.headline ?? ""}`} palette={palette} width={width} />
      </KenBurns>

      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: px(44, width) }}>
          <span
            style={{
              fontSize: px(104, width),
              fontWeight: 900,
              letterSpacing: "0.08em",
              color: palette.text,
              textShadow: `0 0 ${px(60, width)}px ${rgba(palette.primary, 0.55)}`,
              textAlign: "center",
              padding: `0 ${px(60, width)}px`,
              opacity: clamp01(lockIn),
              transform: `scale(${scale})`,
            }}
          >
            {scene.headline ?? ""}
          </span>
          <span
            style={{
              display: "flex",
              alignItems: "center",
              minHeight: px(52, width),
              fontSize: px(38, width),
              fontWeight: 500,
              letterSpacing: "0.03em",
              color: rgba(palette.text, 0.85),
            }}
          >
            {typed}
            <span
              style={{
                display: "inline-block",
                width: px(3, width),
                height: px(38, width),
                marginLeft: px(8, width),
                background: palette.accent,
                opacity: cursorOn ? 1 : 0,
              }}
            />
          </span>
        </div>
      </AbsoluteFill>

      {/* final fade to the palette background */}
      <AbsoluteFill style={{ background: palette.bg, opacity: fadeOut }} />
    </AbsoluteFill>
  );
};
