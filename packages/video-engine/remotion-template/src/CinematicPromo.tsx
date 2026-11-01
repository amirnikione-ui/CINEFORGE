import type {FC, ReactNode} from 'react';
import {
  AbsoluteFill,
  Easing,
  interpolate,
  random,
  Sequence,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

import {GradientBackdrop} from './components/GradientBackdrop';
import {VignetteOverlay} from './components/VignetteOverlay';
import WordReveal from './components/WordReveal';
import type {MotionStyle, Palette, Scene, Storyboard} from './schema';
import {
  hexToRgba,
  revealClipPath,
  sceneCameraTransform,
  sceneLayouts,
} from './utils';

/**
 * CinematicPromo - the storyboard-driven promo composition.
 *
 * The component receives the whole Storyboard JSON document as its props
 * object (Remotion passes `defaultProps` / `--props` entries as individual
 * props, and the root registers the storyboard document itself). It maps
 * every scene onto a <Sequence> and renders it according to `kind`,
 * `motion.style` and `transition_in`. Everything is deterministic: motion is
 * derived from the frame number and scene parameters only - no Math.random,
 * no Date.now (Remotion's seeded `random()` is used where variance helps).
 */

/**
 * System font stack only: renders must stay offline-safe, so no web font
 * loading happens in this template.
 */
const FONT_STACK = 'Inter, "Helvetica Neue", "Segoe UI", Arial, sans-serif';

type SceneProps = {
  storyboard: Storyboard;
  scene: Scene;
  durationFrames: number;
};

/** Split a headline into words; empty tokens are dropped. */
const toWords = (headline: string): string[] =>
  headline.split(/\s+/).filter((word) => word.length > 0);

/**
 * Cinematic color trick: the headline renders in palette.text with the LAST
 * word wrapped in a span colored palette.accent. Used by every scene kind.
 */
const accentLastWord = (headline: string, palette: Palette): ReactNode => {
  const words = toWords(headline);
  return words.map((word, index) => (
    <span
      key={`${index}:${word}`}
      style={index === words.length - 1 ? {color: palette.accent} : undefined}
    >
      {word}
      {index < words.length - 1 ? ' ' : ''}
    </span>
  ));
};

/**
 * Supporting body line: fades up with a critically damped spring after the
 * headline. Always rendered in palette.text at 70% opacity per spec.
 */
const BodyLine: FC<{
  body: string;
  delay: number;
  palette: Palette;
  fontSize: number;
  fontFamily: string;
  align?: 'left' | 'center';
}> = ({body, delay, palette, fontSize, fontFamily, align = 'left'}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const progress = spring({
    frame: frame - delay,
    fps,
    config: {damping: 200},
  });

  return (
    <p
      style={{
        margin: 0,
        marginTop: fontSize * 0.8,
        opacity: progress * 0.7,
        transform: `translateY(${interpolate(progress, [0, 1], [24, 0]).toFixed(2)}px)`,
        color: palette.text,
        fontSize,
        fontFamily,
        fontWeight: 500,
        lineHeight: 1.4,
        textAlign: align,
        maxWidth: '85%',
      }}
    >
      {body}
    </p>
  );
};

/**
 * hook scene: huge bold headline, one <WordReveal> per word with a spring
 * stagger, body line fading up after the headline settles.
 */
const HookScene: FC<SceneProps> = ({storyboard, scene, durationFrames}) => {
  const {width} = useVideoConfig();
  const words = toWords(scene.headline);
  const stagger = Math.max(2, Math.round(durationFrames * 0.04));
  const bodyDelay = words.length * stagger + Math.max(4, Math.round(durationFrames * 0.05));

  return (
    <AbsoluteFill
      style={{
        flexDirection: 'column',
        justifyContent: 'center',
        padding: `0 ${width * 0.09}px`,
      }}
    >
      <h1 style={{margin: 0, lineHeight: 1.04, fontSize: width * 0.11}}>
        {words.map((word, index) => (
          <span
            key={`${index}:${word}`}
            style={{display: 'inline-block', whiteSpace: 'nowrap'}}
          >
            <WordReveal
              word={word}
              delay={index * stagger}
              fontSize={width * 0.11}
              fontFamily={FONT_STACK}
              color={
                index === words.length - 1
                  ? storyboard.palette.accent
                  : storyboard.palette.text
              }
            />
            {index < words.length - 1 ? ' ' : ''}
          </span>
        ))}
      </h1>
      {scene.body ? (
        <BodyLine
          body={scene.body}
          delay={bodyDelay}
          palette={storyboard.palette}
          fontSize={width * 0.036}
          fontFamily={FONT_STACK}
        />
      ) : null}
    </AbsoluteFill>
  );
};

/**
 * reveal scene: headline slides in from the left with an overshoot spring,
 * an accent underline bar grows beneath it (scaleX spring from the left).
 */
const RevealScene: FC<SceneProps> = ({storyboard, scene, durationFrames}) => {
  const frame = useCurrentFrame();
  const {width, fps} = useVideoConfig();
  const palette = storyboard.palette;

  // Lower damping than 200 on purpose: the headline overshoots once.
  const slideIn = spring({frame, fps, config: {damping: 12, mass: 0.9}});
  const opacity = interpolate(slideIn, [0, 1], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const translateXPercent = interpolate(slideIn, [0, 1], [-32, 0]);
  const underlineDelay = Math.round(durationFrames * 0.12);
  const underlineGrow = spring({
    frame: frame - underlineDelay,
    fps,
    config: {damping: 200},
  });

  return (
    <AbsoluteFill
      style={{
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'flex-start',
        padding: `0 ${width * 0.09}px`,
      }}
    >
      <h1
        style={{
          margin: 0,
          opacity,
          transform: `translateX(${translateXPercent.toFixed(3)}%)`,
          fontSize: width * 0.085,
          color: palette.text,
          fontFamily: FONT_STACK,
          fontWeight: 900,
          lineHeight: 1.06,
          letterSpacing: '-0.015em',
        }}
      >
        {accentLastWord(scene.headline, palette)}
      </h1>
      <div
        style={{
          marginTop: width * 0.03,
          height: Math.max(4, width * 0.008),
          width: width * 0.42,
          backgroundColor: palette.accent,
          transformOrigin: 'left center',
          transform: `scaleX(${underlineGrow.toFixed(4)})`,
        }}
      />
      {scene.body ? (
        <BodyLine
          body={scene.body}
          delay={underlineDelay + 10}
          palette={palette}
          fontSize={width * 0.034}
          fontFamily={FONT_STACK}
        />
      ) : null}
    </AbsoluteFill>
  );
};

/**
 * typography scene: words pop in one-by-one on a beat grid
 * (framesPerWord = sceneFrames / wordCount) with a slight deterministic
 * rotation seeded per word (Remotion's seeded random - no Math.random).
 */
const TypographyScene: FC<SceneProps> = ({storyboard, scene, durationFrames}) => {
  const frame = useCurrentFrame();
  const {width, fps} = useVideoConfig();
  const palette = storyboard.palette;

  const words = toWords(scene.headline);
  const framesPerWord = Math.max(
    1,
    Math.floor(durationFrames / Math.max(words.length, 1)),
  );

  return (
    <AbsoluteFill
      style={{
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        textAlign: 'center',
        padding: `0 ${width * 0.08}px`,
      }}
    >
      <h1
        style={{
          margin: 0,
          fontSize: width * 0.095,
          fontFamily: FONT_STACK,
          fontWeight: 900,
          lineHeight: 1.15,
        }}
      >
        {words.map((word, index) => {
          const rotation = (random(`cineforge:rotation:${scene.id}:${index}`) - 0.5) * 6;
          const progress = spring({
            frame: frame - index * framesPerWord,
            fps,
            config: {damping: 14, mass: 0.7},
          });
          const opacity = interpolate(progress, [0, 1], [0, 1], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
          });
          const scale = interpolate(progress, [0, 1], [0.5, 1]);
          const wordRotation = interpolate(progress, [0, 1], [rotation * 2, rotation]);

          return (
            <span
              key={`${index}:${word}`}
              style={{display: 'inline-block', whiteSpace: 'nowrap'}}
            >
              <span
                style={{
                  display: 'inline-block',
                  color:
                    index === words.length - 1 ? palette.accent : palette.text,
                  opacity,
                  transform: `scale(${scale.toFixed(4)}) rotate(${wordRotation.toFixed(2)}deg)`,
                }}
              >
                {word}
              </span>
              {index < words.length - 1 ? ' ' : ''}
            </span>
          );
        })}
      </h1>
      {scene.body ? (
        <BodyLine
          body={scene.body}
          delay={Math.round(durationFrames * 0.3)}
          palette={palette}
          fontSize={width * 0.034}
          fontFamily={FONT_STACK}
          align="center"
        />
      ) : null}
    </AbsoluteFill>
  );
};

/**
 * outro scene: centered stack - wordmark (storyboard.title uppercase),
 * headline, thin accent rule - then a fade-through-black ending over the
 * last 12 frames of the scene.
 */
const OutroScene: FC<SceneProps> = ({storyboard, scene, durationFrames}) => {
  const frame = useCurrentFrame();
  const {width, fps} = useVideoConfig();
  const palette = storyboard.palette;

  const enter = spring({frame, fps, config: {damping: 200}});
  const ruleDelay = 10;
  const ruleGrow = spring({frame: frame - ruleDelay, fps, config: {damping: 200}});

  const fadeOutStart = Math.max(0, durationFrames - 12);
  const fadeOutEnd = Math.max(fadeOutStart + 1, durationFrames - 1);
  const fadeToBlack = interpolate(frame, [fadeOutStart, fadeOutEnd], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        padding: `0 ${width * 0.09}px`,
      }}
    >
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          opacity: enter,
          transform: `translateY(${interpolate(enter, [0, 1], [28, 0]).toFixed(2)}px)`,
        }}
      >
        <div
          style={{
            fontSize: width * 0.032,
            letterSpacing: '0.42em',
            textTransform: 'uppercase',
            color: palette.text,
            opacity: 0.72,
            fontFamily: FONT_STACK,
            fontWeight: 600,
          }}
        >
          {storyboard.title.toUpperCase()}
        </div>
        <h1
          style={{
            margin: `${width * 0.03}px 0 0`,
            fontSize: width * 0.12,
            color: palette.text,
            fontFamily: FONT_STACK,
            fontWeight: 900,
            letterSpacing: '-0.01em',
            textAlign: 'center',
          }}
        >
          {accentLastWord(scene.headline, palette)}
        </h1>
        <div
          style={{
            marginTop: width * 0.035,
            width: width * 0.2,
            height: 2,
            backgroundColor: palette.accent,
            transformOrigin: 'center center',
            transform: `scaleX(${ruleGrow.toFixed(4)})`,
          }}
        />
        {scene.body ? (
          <BodyLine
            body={scene.body}
            delay={ruleDelay + 8}
            palette={palette}
            fontSize={width * 0.032}
            fontFamily={FONT_STACK}
            align="center"
          />
        ) : null}
      </div>
      <AbsoluteFill
        style={{backgroundColor: '#000000', opacity: fadeToBlack}}
      />
    </AbsoluteFill>
  );
};

/**
 * Per-scene backdrop layer: two palette-tinted radial glows placed
 * deterministically per scene id, carrying the scene's camera motion
 * (ken-burns / zoom / slide). This is where the motion transform lands on
 * the "backdrop layer" per the motion spec.
 */
const SceneBackdrop: FC<{
  scene: Scene;
  palette: Palette;
  durationFrames: number;
}> = ({scene, palette, durationFrames}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const transform = sceneCameraTransform(
    scene.motion.style,
    scene.motion.intensity,
    frame,
    fps,
    durationFrames,
  );
  const blobA = random(`cineforge:backdrop-a:${scene.id}`);
  const blobB = random(`cineforge:backdrop-b:${scene.id}`);

  return (
    <AbsoluteFill style={transform === 'none' ? undefined : {transform}}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(60% 45% at ${(20 + blobA * 60).toFixed(1)}% ${(25 + blobB * 50).toFixed(1)}%, ${hexToRgba(palette.primary, 0.26)}, rgba(0, 0, 0, 0) 70%)`,
        }}
      />
      <AbsoluteFill
        style={{
          background: `radial-gradient(50% 40% at ${(75 - blobB * 50).toFixed(1)}% ${(70 - blobA * 40).toFixed(1)}%, ${hexToRgba(palette.accent, 0.18)}, rgba(0, 0, 0, 0) 72%)`,
        }}
      />
    </AbsoluteFill>
  );
};

/**
 * Camera-motion helper for the text container, per the motion spec:
 * ken-burns/zoom/slide return a transform, "reveal" returns a clip-path
 * inset animation; everything else is identity.
 */
const useSceneMotion = (
  style: MotionStyle,
  intensity: number,
  durationInFrames: number,
): {transform: string; clipPath: string} => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  return {
    transform: sceneCameraTransform(style, intensity, frame, fps, durationInFrames),
    clipPath: style === 'reveal' ? revealClipPath(frame) : 'none',
  };
};

/** transition_in handling, evaluated on sequence-local frames. */
const transitionInStyle = (
  transitionIn: Scene['transition_in'],
  frame: number,
  fps: number,
): {opacity: number; translateXPercent: number} => {
  if (transitionIn === 'fade') {
    return {
      opacity: interpolate(frame, [0, 10], [0, 1], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
        easing: Easing.out(Easing.cubic),
      }),
      translateXPercent: 0,
    };
  }
  if (transitionIn === 'slide') {
    const progress = spring({
      frame,
      fps,
      config: {damping: 200},
      durationInFrames: 12,
    });
    return {opacity: 1, translateXPercent: (1 - progress) * 8};
  }
  // "cut" (and any future value) enters without animation.
  return {opacity: 1, translateXPercent: 0};
};

/**
 * Renders one scene inside its <Sequence>: the transition-in wrapper holds
 * the scene backdrop (camera motion) and the text block (camera motion +
 * reveal clip-path). useCurrentFrame() is sequence-local here.
 */
const SceneRenderer: FC<SceneProps> = ({storyboard, scene, durationFrames}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const motion = useSceneMotion(
    scene.motion.style,
    scene.motion.intensity,
    durationFrames,
  );
  const transition = transitionInStyle(scene.transition_in, frame, fps);

  return (
    <AbsoluteFill
      style={{
        opacity: transition.opacity,
        transform:
          transition.translateXPercent !== 0
            ? `translateX(${transition.translateXPercent.toFixed(3)}%)`
            : undefined,
      }}
    >
      <SceneBackdrop
        scene={scene}
        palette={storyboard.palette}
        durationFrames={durationFrames}
      />
      <AbsoluteFill
        style={{
          transform: motion.transform === 'none' ? undefined : motion.transform,
          clipPath: motion.clipPath === 'none' ? undefined : motion.clipPath,
        }}
      >
        {scene.kind === 'hook' ? (
          <HookScene storyboard={storyboard} scene={scene} durationFrames={durationFrames} />
        ) : null}
        {scene.kind === 'reveal' ? (
          <RevealScene storyboard={storyboard} scene={scene} durationFrames={durationFrames} />
        ) : null}
        {scene.kind === 'typography' ? (
          <TypographyScene storyboard={storyboard} scene={scene} durationFrames={durationFrames} />
        ) : null}
        {scene.kind === 'outro' ? (
          <OutroScene storyboard={storyboard} scene={scene} durationFrames={durationFrames} />
        ) : null}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

export const CinematicPromo: FC<Storyboard> = (storyboard) => {
  return (
    <AbsoluteFill
      style={{backgroundColor: storyboard.palette.bg, fontFamily: FONT_STACK}}
    >
      <GradientBackdrop palette={storyboard.palette} />
      {sceneLayouts(storyboard).map(({scene, from, durationInFrames}) => (
        <Sequence
          key={scene.id}
          from={from}
          durationInFrames={durationInFrames}
          name={`${scene.id} (${scene.kind})`}
        >
          <SceneRenderer
            storyboard={storyboard}
            scene={scene}
            durationFrames={durationInFrames}
          />
        </Sequence>
      ))}
      <VignetteOverlay />
    </AbsoluteFill>
  );
};
