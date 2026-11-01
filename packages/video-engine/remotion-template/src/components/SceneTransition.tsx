import { FC } from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import type { TransitionKind } from "../types";

export const TRANSITION_FRAMES = 15;

/**
 * Scene entrance wrapper: fade | slide | cut.
 * Runs over the first TRANSITION_FRAMES of the scene's Sequence.
 */
export const SceneTransition: FC<{
  kind: TransitionKind;
  children: React.ReactNode;
}> = ({ kind, children }) => {
  const frame = useCurrentFrame();

  if (kind === "cut") {
    return <AbsoluteFill>{children}</AbsoluteFill>;
  }

  const p = interpolate(frame, [0, TRANSITION_FRAMES], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  const style: React.CSSProperties =
    kind === "fade"
      ? { opacity: p }
      : { opacity: p, transform: `translateX(${(1 - p) * 6}%)` };

  return <AbsoluteFill style={style}>{children}</AbsoluteFill>;
};
