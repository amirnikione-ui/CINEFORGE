import { FC } from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import type { MotionStyle } from "../types";

/**
 * KenBurns wrapper: slow cinematic zoom + drift over its children.
 * ken-burns/zoom styles zoom IN, slide/reveal zoom OUT; "slide" drifts horizontally.
 */
export const KenBurns: FC<{
  style?: MotionStyle;
  intensity?: number;
  /** Scene duration in frames (sequence-local). Falls back to the composition duration. */
  durationInFrames?: number;
  children: React.ReactNode;
}> = ({ style = "ken-burns", intensity = 0.5, durationInFrames, children }) => {
  const frame = useCurrentFrame();
  const video = useVideoConfig();
  const total = Math.max(1, durationInFrames ?? video.durationInFrames);

  const k = Math.min(1, Math.max(0, intensity));
  const progress = interpolate(frame, [0, total], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.ease),
  });

  const zoomIn = style === "ken-burns" || style === "zoom";
  const scale = zoomIn ? 1 + 0.12 * k * progress : 1 + 0.12 * k * (1 - progress);
  const driftX = style === "slide" ? (progress - 0.5) * 4 * k : 0;
  const driftY = style === "slide" ? 0 : (0.5 - progress) * 2.4 * k;

  return (
    <AbsoluteFill style={{ transform: `scale(${scale}) translate(${driftX}%, ${driftY}%)` }}>
      {children}
    </AbsoluteFill>
  );
};
