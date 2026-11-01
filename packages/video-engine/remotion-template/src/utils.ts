import {Easing, interpolate} from 'remotion';

import type {MotionStyle, Scene, Storyboard} from './schema';

/**
 * Frame helpers for the CinematicPromo composition. All timing math is
 * derived from the storyboard itself (durations in seconds + fps) so the
 * renderer stays frame-accurate for any director-generated storyboard.
 */

/** Frames a single scene runs for. Always at least 1 frame. */
export const sceneFrames = (storyboard: Storyboard, scene: Scene): number =>
  Math.max(1, Math.round(scene.duration_s * storyboard.fps));

/**
 * Total frame count of the promo: the sum of all scene durations (in
 * seconds) sampled at the storyboard frame rate, per the contract rule
 * `sum(scenes[].duration_s) ~= duration_target_s`.
 */
export const totalFrames = (storyboard: Storyboard): number =>
  Math.max(
    1,
    Math.round(
      storyboard.scenes.reduce((sum, scene) => sum + scene.duration_s, 0) *
        storyboard.fps,
    ),
  );

/** Placement of one scene on the composition timeline. */
export type SceneLayout = {
  scene: Scene;
  /** Absolute frame at which the scene starts. */
  from: number;
  /** Frame count of the scene. */
  durationInFrames: number;
};

/**
 * Scenes back-to-back on the timeline. Offsets accumulate the per-scene
 * frame counts so sequences tile without gaps or overlaps.
 */
export const sceneLayouts = (storyboard: Storyboard): SceneLayout[] => {
  let cursor = 0;
  return storyboard.scenes.map((scene) => {
    const durationInFrames = sceneFrames(storyboard, scene);
    const layout: SceneLayout = {scene, from: cursor, durationInFrames};
    cursor += durationInFrames;
    return layout;
  });
};

const clamp01 = (value: number): number => Math.min(1, Math.max(0, value));

/**
 * Slow "camera" transform for a scene, used by both the per-scene backdrop
 * layer and the text container. Deterministic: derived only from frame
 * count, fps and the scene's motion parameters.
 */
export const sceneCameraTransform = (
  style: MotionStyle,
  intensity: number,
  frame: number,
  fps: number,
  durationInFrames: number,
): string => {
  const amount = clamp01(intensity);
  const progress =
    durationInFrames > 1 ? Math.min(1, frame / (durationInFrames - 1)) : 1;
  const seconds = fps > 0 ? frame / fps : 0;

  switch (style) {
    case 'ken-burns': {
      // Scale 1.0 -> 1.0 + 0.12 * intensity plus a slight translate drift.
      const scale = 1 + 0.12 * amount * progress;
      const driftX = Math.sin(seconds * 0.4) * 8 * amount;
      const driftY = Math.cos(seconds * 0.3) * -6 * amount;
      return `translate(${driftX.toFixed(2)}px, ${driftY.toFixed(2)}px) scale(${scale.toFixed(4)})`;
    }
    case 'zoom': {
      // Scale in then back out over the scene (sin pulse).
      const pulse = Math.sin(progress * Math.PI);
      const scale = 1 + 0.1 * amount * pulse;
      return `scale(${scale.toFixed(4)})`;
    }
    case 'slide': {
      // Slow horizontal drift across the scene.
      const driftX = (progress - 0.5) * 12 * amount;
      return `translateX(${driftX.toFixed(2)}px)`;
    }
    case 'reveal':
    default:
      // Reveal is expressed as a clip-path animation on the text block.
      return 'none';
  }
};

/** Frames it takes for the reveal clip-path to fully open. */
const REVEAL_OPEN_FRAMES = 20;

/**
 * Clip-path inset animation for the text block of scenes with
 * motion.style "reveal": starts as a thin horizontal slit and wipes open.
 */
export const revealClipPath = (frame: number): string => {
  const progress = interpolate(frame, [0, REVEAL_OPEN_FRAMES], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });
  const insetPercent = (1 - progress) * 42;
  return `inset(${insetPercent.toFixed(2)}% 0% ${insetPercent.toFixed(2)}% 0%)`;
};

/** Output dimensions for the aspect strings used in storyboard contracts. */
const ASPECT_DIMENSIONS: Record<string, {width: number; height: number}> = {
  '9:16': {width: 1080, height: 1920},
  '16:9': {width: 1920, height: 1080},
  '1:1': {width: 1080, height: 1080},
  '4:5': {width: 1080, height: 1350},
};

/** Resolve render dimensions from the storyboard `aspect` field. */
export const dimensionsForAspect = (aspect: string): {width: number; height: number} =>
  ASPECT_DIMENSIONS[aspect] ?? ASPECT_DIMENSIONS['9:16'];

/**
 * Convert a #rgb / #rrggbb color to rgba() with the given alpha. Unknown
 * color formats pass through untouched so CSS can still handle them.
 */
export const hexToRgba = (hex: string, alpha: number): string => {
  const normalized = hex.replace(/^#/, '');
  const sixDigit =
    normalized.length === 3
      ? normalized
          .split('')
          .map((char) => char + char)
          .join('')
      : normalized;
  const value = Number.parseInt(sixDigit, 16);
  if (sixDigit.length !== 6 || Number.isNaN(value)) {
    return hex;
  }
  const red = (value >> 16) & 0xff;
  const green = (value >> 8) & 0xff;
  const blue = value & 0xff;
  return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
};
