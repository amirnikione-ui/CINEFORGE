import {z} from 'zod';

/**
 * Zod mirror of the CINEFORGE Storyboard JSON contract (schema_version 1).
 *
 * Source of truth: docs/API_CONTRACTS.md ("Storyboard JSON (schema_version 1)").
 * The renderer accepts storyboards verbatim - any field the director agent
 * emits must validate against this schema without transformation, so the
 * schema stays as close to the contract as possible (only `body`,
 * `narration` and `visual_prompt` are optional, exactly as specified).
 */

export const paletteSchema = z.object({
  bg: z.string(),
  primary: z.string(),
  accent: z.string(),
  text: z.string(),
});

export const motionSchema = z.object({
  style: z.enum(['ken-burns', 'slide', 'zoom', 'reveal']),
  intensity: z.number(),
});

export const sceneSchema = z.object({
  id: z.string(),
  kind: z.enum(['hook', 'reveal', 'typography', 'outro']),
  duration_s: z.number().positive(),
  headline: z.string(),
  body: z.string().optional(),
  narration: z.string().optional(),
  visual_prompt: z.string().optional(),
  motion: motionSchema,
  transition_in: z.enum(['fade', 'cut', 'slide']),
});

export const storyboardSchema = z.object({
  schema_version: z.literal(1),
  title: z.string(),
  platform: z.enum(['instagram', 'youtube', 'tiktok', 'web']),
  aspect: z.string(),
  fps: z.number().int().positive(),
  duration_target_s: z.number().positive(),
  palette: paletteSchema,
  music_mood: z.string(),
  scenes: z.array(sceneSchema).min(1),
});

export type Palette = z.infer<typeof paletteSchema>;
export type Motion = z.infer<typeof motionSchema>;
export type MotionStyle = Motion['style'];
export type Scene = z.infer<typeof sceneSchema>;
export type Storyboard = z.infer<typeof storyboardSchema>;
