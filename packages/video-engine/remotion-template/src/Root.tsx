import { FC } from "react";
import { Composition } from "remotion";
import storyboardJson from "../public/storyboard.json";
import {
  CinematicPromo,
  cinematicPromoMetadata,
  type CinematicPromoProps,
} from "./CinematicPromo";
import { parseStoryboard } from "./parse";

/**
 * Scaffold contract (ADR-0006): the CINEFORGE backend copies this template into a
 * project workspace and overwrites public/storyboard.json with the generated
 * storyboard (schema v1). Canvas size, fps and scene timing all derive from that
 * file via calculateMetadata — nothing is hardcoded. The backend flips
 * `includeAudio` when narration files exist under public/audio/.
 */
const defaultProps: CinematicPromoProps = {
  storyboard: parseStoryboard(storyboardJson),
  includeAudio: false,
};

export const RemotionRoot: FC = () => {
  return (
    <Composition
      id="CinematicPromo"
      component={CinematicPromo}
      defaultProps={defaultProps}
      calculateMetadata={cinematicPromoMetadata}
      // Placeholder values; calculateMetadata always overrides them from the storyboard.
      width={1080}
      height={1920}
      fps={30}
      durationInFrames={1}
    />
  );
};
