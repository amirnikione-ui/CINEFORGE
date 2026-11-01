import React from 'react';
import { Composition } from 'remotion';
import { CinematicPromo, STORYBOARD_PROPS, type StoryboardProps } from './scenes';

const DIMS: Record<string, { w: number; h: number }> = {
  '9:16': { w: 1080, h: 1920 },
  '16:9': { w: 1920, h: 1080 },
  '1:1': { w: 1080, h: 1080 },
  '4:5': { w: 1080, h: 1350 },
};

export const RemotionRoot: React.FC = () => {
  const sb = STORYBOARD_PROPS.storyboard;
  const dims = DIMS[sb.aspect] ?? DIMS['9:16'];
  const fps = sb.fps ?? 30;
  const total = sb.scenes.reduce((acc, s) => acc + s.duration_s, 0);

  return (
    <Composition<null, StoryboardProps>
      id="CinematicPromo"
      component={CinematicPromo}
      durationInFrames={Math.max(1, Math.round(total * fps))}
      fps={fps}
      width={dims.w}
      height={dims.h}
      defaultProps={STORYBOARD_PROPS}
    />
  );
};

export type { StoryboardProps };
