import { FC, useEffect, useMemo, useState } from "react";
import {
  AbsoluteFill,
  Audio,
  Sequence,
  continueRender,
  delayRender,
  staticFile,
  useVideoConfig,
  type CalculateMetadataFunction,
} from "remotion";
import { AnimatedSubtitles } from "./components/AnimatedSubtitles";
import { GrainOverlay } from "./components/GrainOverlay";
import { SceneTransition } from "./components/SceneTransition";
import { FeatureScene } from "./scenes/FeatureScene";
import { HookScene } from "./scenes/HookScene";
import { OutroScene } from "./scenes/OutroScene";
import { RevealScene } from "./scenes/RevealScene";
import { TypographyScene } from "./scenes/TypographyScene";
import { px, resolveCanvas, resolvePalette } from "./theme";
import type { Scene, SceneRenderProps, Storyboard } from "./types";

export interface CinematicPromoProps {
  storyboard: Storyboard;
  /** When true, narration files (public/audio/<scene-id>.mp3) play if they exist. */
  includeAudio: boolean;
}

interface Segment {
  scene: Scene;
  from: number;
  durationInFrames: number;
}

/** Cut the storyboard into frame segments: scene i covers [from, from + durationInFrames). */
export function segmentStoryboard(storyboard: Storyboard): Segment[] {
  const fps = storyboard.fps > 0 ? storyboard.fps : 30;
  let cursor = 0;
  return storyboard.scenes.map((scene) => {
    const durationInFrames = Math.max(1, Math.round(scene.duration_s * fps));
    const segment = { scene, from: cursor, durationInFrames };
    cursor += durationInFrames;
    return segment;
  });
}

export function totalDurationInFrames(storyboard: Storyboard): number {
  return segmentStoryboard(storyboard).reduce((acc, s) => acc + s.durationInFrames, 0);
}

/** Canvas, fps and duration derive entirely from the storyboard — nothing hardcoded. */
export const cinematicPromoMetadata: CalculateMetadataFunction<CinematicPromoProps> = ({
  props,
}) => {
  const dimensions = resolveCanvas(props.storyboard);
  return {
    width: dimensions.width,
    height: dimensions.height,
    fps: props.storyboard.fps > 0 ? props.storyboard.fps : 30,
    durationInFrames: totalDurationInFrames(props.storyboard),
  };
};

/**
 * HEAD-check which narration files actually exist under public/audio/.
 * Missing files degrade gracefully: subtitles render, audio is skipped.
 */
function useAvailableNarration(paths: string[]): Set<string> {
  const [available, setAvailable] = useState<Set<string>>(() => new Set());
  const key = paths.join("\n");

  useEffect(() => {
    const list = key.length > 0 ? key.split("\n") : [];
    if (list.length === 0) {
      return undefined;
    }
    const handle = delayRender("resolving narration audio availability");
    let cancelled = false;
    void Promise.all(
      list.map(async (path) => {
        try {
          const response = await fetch(path, { method: "HEAD" });
          return response.ok ? path : null;
        } catch {
          return null;
        }
      }),
    ).then((results) => {
      if (!cancelled) {
        setAvailable(new Set(results.filter((path): path is string => path !== null)));
      }
      continueRender(handle);
    });
    return () => {
      cancelled = true;
    };
  }, [key]);

  return available;
}

const SceneRenderer: FC<SceneRenderProps> = (props) => {
  switch (props.scene.kind) {
    case "hook":
      return <HookScene {...props} />;
    case "reveal":
      return <RevealScene {...props} />;
    case "typography":
      return <TypographyScene {...props} />;
    case "feature":
      return <FeatureScene {...props} />;
    case "outro":
      return <OutroScene {...props} />;
    default:
      return <TypographyScene {...props} />;
  }
};

/** Optional 2.39:1-style letterbox bars for wide (16:9) canvases. */
const Letterbox: FC<{ barHeight: number }> = ({ barHeight }) => (
  <>
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        right: 0,
        height: barHeight,
        background: "#000000",
        zIndex: 40,
      }}
    />
    <div
      style={{
        position: "absolute",
        bottom: 0,
        left: 0,
        right: 0,
        height: barHeight,
        background: "#000000",
        zIndex: 40,
      }}
    />
  </>
);

export const CinematicPromo: FC<CinematicPromoProps> = ({ storyboard, includeAudio }) => {
  const { width, height } = useVideoConfig();
  const palette = useMemo(() => resolvePalette(storyboard.palette), [storyboard.palette]);
  const segments = useMemo(() => segmentStoryboard(storyboard), [storyboard]);

  const narrationPaths = useMemo(() => {
    if (!includeAudio) {
      return [];
    }
    return storyboard.scenes
      .filter((scene) => (scene.narration ?? "").trim().length > 0)
      .map((scene) => staticFile(`audio/${scene.id}.mp3`));
  }, [includeAudio, storyboard]);
  const availableNarration = useAvailableNarration(narrationPaths);

  return (
    <AbsoluteFill style={{ background: palette.bg }}>
      {segments.map(({ scene, from, durationInFrames }) => {
        const narration = (scene.narration ?? "").trim();
        const audioSrc =
          includeAudio && narration ? staticFile(`audio/${scene.id}.mp3`) : null;
        return (
          <Sequence
            key={scene.id}
            from={from}
            durationInFrames={durationInFrames}
            name={`${scene.kind} · ${scene.id}`}
          >
            <SceneTransition kind={scene.transition_in ?? "fade"}>
              <AbsoluteFill>
                <SceneRenderer
                  scene={scene}
                  palette={palette}
                  width={width}
                  height={height}
                  durationInFrames={durationInFrames}
                />
                {narration ? (
                  <AnimatedSubtitles
                    text={narration}
                    palette={palette}
                    width={width}
                    durationInFrames={durationInFrames}
                  />
                ) : null}
              </AbsoluteFill>
            </SceneTransition>
            {audioSrc && availableNarration.has(audioSrc) ? <Audio src={audioSrc} /> : null}
          </Sequence>
        );
      })}

      {/* global cinematic finish: film grain everywhere, letterbox on wide canvases */}
      <GrainOverlay />
      {width > height ? <Letterbox barHeight={px(64, width)} /> : null}
    </AbsoluteFill>
  );
};
