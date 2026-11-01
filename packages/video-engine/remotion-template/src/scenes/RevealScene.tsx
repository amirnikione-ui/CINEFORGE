import { FC } from "react";
import {
  AbsoluteFill,
  Easing,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Backdrop } from "../components/Backdrop";
import { KenBurns } from "../components/KenBurns";
import { clamp01, px, rgba } from "../theme";
import type { SceneRenderProps } from "../types";

// Product reveal: a glowing "product card" springs in over a rotating conic
// sheen, bobs gently, and the body line fades up beneath it.
export const RevealScene: FC<SceneRenderProps> = ({
  scene,
  palette,
  width,
  height,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const entrance = spring({
    frame,
    fps,
    config: { damping: 14, stiffness: 110, mass: 0.9 },
  });
  const scale = interpolate(entrance, [0, 1], [0.62, 1]);
  const tilt = interpolate(entrance, [0, 1], [-9, 0]);
  const float = Math.sin((frame / fps) * Math.PI) * px(10, width); // slow 0.5 Hz bob
  const sheenSpin = frame * 0.9; // degrees per frame

  const bodyIn = interpolate(frame, [26, 46], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  const cardW = Math.min(px(620, width), width * 0.44);
  const cardH = Math.min(px(720, width), height * 0.64);

  return (
    <AbsoluteFill>
      <KenBurns
        style={scene.motion?.style}
        intensity={scene.motion?.intensity}
        durationInFrames={durationInFrames}
      >
        <Backdrop seed={`${scene.id}:${scene.visual_prompt ?? ""}`} palette={palette} width={width} />
      </KenBurns>

      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        {/* rotating conic-gradient sheen behind the card */}
        <div
          style={{
            position: "absolute",
            width: cardH * 1.8,
            height: cardH * 1.8,
            borderRadius: "50%",
            background: `conic-gradient(from 0deg, transparent 0deg, ${rgba(
              palette.accent,
              0.3,
            )} 42deg, transparent 95deg, transparent 185deg, ${rgba(
              palette.primary,
              0.36,
            )} 225deg, transparent 285deg)`,
            filter: `blur(${px(34, width)}px)`,
            opacity: clamp01(entrance),
            transform: `translateY(${float * 0.5}px) rotate(${sheenSpin}deg)`,
          }}
        />

        {/* product card */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: px(26, width),
            width: cardW,
            height: cardH,
            borderRadius: px(36, width),
            border: `2px solid ${rgba(palette.primary, 0.9)}`,
            background: `linear-gradient(160deg, ${rgba(palette.primary, 0.24)}, ${rgba(
              palette.bg,
              0.88,
            )} 55%, ${rgba(palette.accent, 0.18)})`,
            boxShadow: `0 0 ${px(90, width)}px ${rgba(
              palette.primary,
              0.5,
            )}, inset 0 0 ${px(60, width)}px ${rgba(palette.primary, 0.16)}`,
            opacity: clamp01(entrance),
            transform: `translateY(${float}px) rotate(${tilt}deg) scale(${scale})`,
          }}
        >
          {/* product visual stand-in until real frames composite in */}
          <div
            style={{
              width: px(170, width),
              height: px(170, width),
              borderRadius: "50%",
              border: `3px solid ${palette.accent}`,
              background: `radial-gradient(circle at 32% 28%, ${rgba(
                palette.accent,
                0.5,
              )}, ${rgba(palette.primary, 0.35)} 60%, ${rgba(palette.bg, 0.9)})`,
              boxShadow: `0 0 ${px(46, width)}px ${rgba(palette.accent, 0.45)}`,
            }}
          />
          <span
            style={{
              fontSize: px(64, width),
              fontWeight: 800,
              letterSpacing: "0.06em",
              color: palette.text,
              textAlign: "center",
            }}
          >
            {scene.headline ?? ""}
          </span>
          {scene.visual_prompt ? (
            <span
              style={{
                fontSize: px(22, width),
                color: rgba(palette.text, 0.6),
                textAlign: "center",
                padding: `0 ${px(40, width)}px`,
              }}
            >
              {scene.visual_prompt}
            </span>
          ) : null}
        </div>
      </AbsoluteFill>

      {scene.body ? (
        <AbsoluteFill
          style={{
            alignItems: "center",
            justifyContent: "flex-end",
            paddingBottom: px(150, width),
          }}
        >
          <span
            style={{
              fontSize: px(38, width),
              fontWeight: 500,
              color: rgba(palette.text, 0.85),
              opacity: bodyIn,
              transform: `translateY(${(1 - bodyIn) * px(26, width)}px)`,
            }}
          >
            {scene.body}
          </span>
        </AbsoluteFill>
      ) : null}
    </AbsoluteFill>
  );
};
