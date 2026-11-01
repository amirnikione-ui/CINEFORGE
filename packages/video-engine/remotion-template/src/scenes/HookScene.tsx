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

// Kinetic typography hook: headline words slam in one by one, each impact
// shakes the whole frame; an accent gradient sweeps the background.
const WORD_STAGGER = 5; // frames between word slams
const IMPACT_DELAY = 9; // frames from word start to impact
const SHAKE_FRAMES = 14;

/** Decaying ~6 Hz sine shake starting at `impact`; zero before it happens. */
const shakeAt = (frame: number, impact: number, fps: number): number => {
  const t = frame - impact;
  if (t < 0 || t > SHAKE_FRAMES) {
    return 0;
  }
  const amplitude = 11 * (1 - t / SHAKE_FRAMES);
  return Math.sin((t / fps) * Math.PI * 2 * 6) * amplitude;
};

export const HookScene: FC<SceneRenderProps> = ({
  scene,
  palette,
  width,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const words = (scene.headline ?? "").split(/\s+/).filter(Boolean);
  const impacts = words.map((_, i) => i * WORD_STAGGER + IMPACT_DELAY);
  const shakeX = impacts.reduce((acc, at) => acc + shakeAt(frame, at, fps), 0);
  const shakeY = impacts.reduce((acc, at) => acc + shakeAt(frame + 4, at, fps), 0) * 0.6;

  const sweep = interpolate(frame, [0, Math.max(1, durationInFrames)], [-45, 145]);

  const bodyStart = words.length * WORD_STAGGER + IMPACT_DELAY + 8;
  const bodyIn = interpolate(frame, [bodyStart, bodyStart + 16], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  return (
    <AbsoluteFill>
      <KenBurns
        style={scene.motion?.style}
        intensity={scene.motion?.intensity}
        durationInFrames={durationInFrames}
      >
        <Backdrop seed={`${scene.id}:${scene.visual_prompt ?? scene.headline ?? ""}`} palette={palette} width={width} />
      </KenBurns>

      {/* accent gradient sweep */}
      <AbsoluteFill
        style={{
          background: `linear-gradient(105deg, transparent 32%, ${rgba(
            palette.accent,
            0.16,
          )} 46%, ${rgba(palette.primary, 0.2)} 54%, transparent 68%)`,
          transform: `translateX(${sweep}%)`,
        }}
      />

      {/* kinetic headline with screen shake */}
      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
          padding: `0 ${px(70, width)}px`,
          transform: `translate(${shakeX}px, ${shakeY}px)`,
        }}
      >
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            justifyContent: "center",
            columnGap: px(26, width),
            rowGap: px(10, width),
          }}
        >
          {words.map((word, i) => {
            const slam = spring({
              frame: frame - i * WORD_STAGGER,
              fps,
              config: { damping: 11, stiffness: 170, mass: 0.9 },
            });
            return (
              <span
                key={`${word}-${i}`}
                style={{
                  display: "inline-block",
                  fontSize: px(128, width),
                  fontWeight: 900,
                  lineHeight: 1.05,
                  color: i % 2 === 0 ? palette.text : palette.accent,
                  textShadow: `0 0 ${px(46, width)}px ${rgba(palette.primary, 0.6)}`,
                  opacity: clamp01(slam),
                  transform: `scale(${interpolate(slam, [0, 1], [2.3, 1])}) translateY(${
                    (1 - slam) * px(42, width)
                  }px)`,
                }}
              >
                {word}
              </span>
            );
          })}
        </div>
      </AbsoluteFill>

      {scene.body ? (
        <AbsoluteFill
          style={{
            alignItems: "center",
            justifyContent: "flex-end",
            paddingBottom: px(170, width),
          }}
        >
          <span
            style={{
              fontSize: px(40, width),
              fontWeight: 500,
              letterSpacing: "0.04em",
              color: rgba(palette.text, 0.85),
              opacity: bodyIn,
              transform: `translateY(${(1 - bodyIn) * px(28, width)}px)`,
            }}
          >
            {scene.body}
          </span>
        </AbsoluteFill>
      ) : null}
    </AbsoluteFill>
  );
};
