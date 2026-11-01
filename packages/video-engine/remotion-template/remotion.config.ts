import { Config } from "@remotion/cli/config";

// Minimal defaults — per-render overrides come from the CLI / video-engine runner.
Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
