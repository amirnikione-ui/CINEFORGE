import React from 'react';
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import { TransitionSeries, linearTiming } from '@remotion/transitions';
import { fade } from '@remotion/transitions/fade';
import { slide } from '@remotion/transitions/slide';
import storyboardJson from '../storyboard.json';

// ── Types (storyboard schema v1 — docs/API_CONTRACTS.md) ─────────────────────
export type Scene = {
  id: string;
  kind: 'hook' | 'reveal' | 'typography' | 'outro';
  duration_s: number;
  headline?: string;
  body?: string;
  narration?: string;
  visual_prompt?: string;
  motion?: { style?: 'ken-burns' | 'slide' | 'zoom' | 'reveal'; intensity?: number };
  transition_in?: 'fade' | 'cut' | 'slide';
};

export type StoryboardProps = {
  [key: string]: unknown;
  storyboard: {
    title: string;
    aspect: string;
    fps: number;
    palette: { bg: string; primary: string; accent: string; text: string };
    music_mood: string;
    scenes: Scene[];
  };
}

export const STORYBOARD_PROPS: StoryboardProps = {
  storyboard: storyboardJson as StoryboardProps['storyboard'],
};

// ── CinematicPromo ───────────────────────────────────────────────────────────
export const CinematicPromo: React.FC<StoryboardProps> = ({ storyboard }) => {
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={{ backgroundColor: storyboard.palette.bg }}>
      <TransitionSeries>
        {storyboard.scenes.map((scene) => (
          <TransitionSeries.Sequence
            key={scene.id}
            durationInFrames={Math.max(1, Math.round(scene.duration_s * fps))}
          >
            <TransitionSeries.Transition
              presentation={scene.transition_in === 'slide' ? slide() : fade()}
              timing={linearTiming({ durationInFrames: Math.round(0.5 * fps) })}
            />
            <SceneView scene={scene} palette={storyboard.palette} />
          </TransitionSeries.Sequence>
        ))}
      </TransitionSeries>
      <Overlays palette={storyboard.palette} />
    </AbsoluteFill>
  );
}

// ── Scene renderer: kind × motion style ──────────────────────────────────────
const SceneView: React.FC<{ scene: Scene; palette: StoryboardProps['storyboard']['palette'] }> = ({
  scene,
  palette,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames, width, height } = useVideoConfig();
  const style = scene.motion?.style ?? 'ken-burns';
  const intensity = scene.motion?.intensity ?? 0.6;
  const progress = frame / Math.max(1, durationInFrames);

  // code-driven "virtual camera"
  const zoom =
    style === 'zoom'
      ? 1 + 0.18 * intensity * progress
      : style === 'reveal'
        ? 1 + 0.18 * intensity * (1 - progress)
        : 1 + 0.1 * intensity * progress;
  const panX = style === 'slide' ? interpolate(progress, [0, 1], [-40, 40]) : 0;
  const panY = style === 'ken-burns' ? interpolate(progress, [0, 1], [12, -12]) : 0;

  const pop = spring({ frame, fps, config: { damping: 18, stiffness: 110 } });
  const textRise = interpolate(pop, [0, 1], [48, 0]);
  const fade = interpolate(frame, [0, 10, durationInFrames - 12, durationInFrames], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const headline = scene.headline ?? '';
  const isCentered = scene.kind === 'typography' || scene.kind === 'outro';

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(120% 90% at 30% 20%, ${palette.primary}22 0%, ${palette.bg} 55%, ${palette.bg} 100%)`,
        transform: `scale(${zoom}) translate(${panX}px, ${panY}px)`,
      }}
    >
      {/* glow orb — procedural visual anchor (visual_prompt stand-in) */}
      <div
        style={{
          position: 'absolute',
          top: isCentered ? '18%' : '24%',
          right: '12%',
          width: height * 0.28,
          height: height * 0.28,
          borderRadius: '50%',
          background: `radial-gradient(circle, ${palette.accent}55 0%, transparent 70%)`,
          filter: 'blur(2px)',
          opacity: 0.8 * fade,
        }}
      />
      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: isCentered ? 'center' : 'flex-start',
          paddingTop: isCentered ? 0 : height * 0.3,
          opacity: fade,
          transform: `translateY(${textRise}px)`,
          padding: width * 0.08,
          textAlign: 'center',
        }}
      >
        <div
          style={{
            fontFamily:
              'Inter, "Helvetica Neue", Arial, sans-serif',
            fontWeight: 900,
            fontSize: height * (scene.kind === 'typography' ? 0.085 : 0.07),
            letterSpacing: '-0.02em',
            color: palette.text,
            textShadow: '0 6px 40px rgba(0,0,0,0.6)',
            lineHeight: 1.05,
          }}
        >
          {letters(headline, pop, palette)}
        </div>
        {scene.body ? (
          <div
            style={{
              marginTop: height * 0.02,
              fontFamily: 'Inter, Arial, sans-serif',
              fontWeight: 500,
              fontSize: height * 0.028,
              color: palette.accent,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              opacity: interpolate(pop, [0.3, 1], [0, 1]),
            }}
          >
            {scene.body}
          </div>
        ) : null}
        {scene.kind === 'outro' ? (
          <div
            style={{
              marginTop: height * 0.05,
              padding: `${height * 0.012}px ${height * 0.05}px`,
              borderRadius: 999,
              border: `2px solid ${palette.accent}`,
              color: palette.text,
              fontFamily: 'Inter, Arial, sans-serif',
              fontWeight: 700,
              fontSize: height * 0.026,
              boxShadow: `0 0 60px ${palette.accent}44`,
              transform: `scale(${interpolate(pop, [0.5, 1], [0.92, 1])})`,
            }}
          >
            Get yours today →
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

// per-letter stagger for cinematic typography
function letters(text: string, pop: number, palette: StoryboardProps['storyboard']['palette']) {
  if (!text) return null;
  return text.split('').map((ch, i) => (
    <span
      key={i}
      style={{
        display: 'inline-block',
        opacity: interpolate(pop, [i * 0.03, Math.min(1, i * 0.03 + 0.35)], [0, 1], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        }),
        color: ch === ' ' ? undefined : palette.text,
      }}
    >
      {ch === ' ' ? '\u00A0' : ch}
    </span>
  ));
}

// ── Cinematic overlays: vignette + grain + letterbox ─────────────────────────
const Overlays: React.FC<{ palette: StoryboardProps['storyboard']['palette'] }> = () => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const bars = height * 0.045;
  return (
    <>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'radial-gradient(120% 120% at 50% 50%, transparent 55%, rgba(0,0,0,0.55) 100%)',
        }}
      />
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: bars, background: '#000' }} />
      <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: bars, background: '#000' }} />
      <Grain width={width} height={height} frame={frame} />
    </>
  );
};

const Grain: React.FC<{ width: number; height: number; frame: number }> = ({ width, height, frame }) => {
  const dots = React.useMemo(() => {
    const rand = mulberry(frame * 7919 + 17);
    return Array.from({ length: 90 }, () => ({
      x: rand() * width,
      y: rand() * height,
      r: rand() * 1.6 + 0.4,
      o: rand() * 0.05,
    }));
  }, [width, height, frame]);
  return (
    <svg width={width} height={height} style={{ position: 'absolute', inset: 0 }}>
      {dots.map((d, i) => (
        <circle key={i} cx={d.x} cy={d.y} r={d.r} fill="#fff" opacity={d.o} />
      ))}
    </svg>
  );
};

function mulberry(seed: number) {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
