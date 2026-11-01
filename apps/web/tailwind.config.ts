import type { Config } from 'tailwindcss';

/**
 * CINEFORGE studio theme — dark cinematic palette from the v0.1 contract example:
 * bg #0a0a12 · primary #7c5cff · accent #00e5ff · text #f5f5ff.
 */
const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#0a0a12',
        panel: '#10101a',
        raised: '#161624',
        line: 'rgba(245,245,255,0.08)',
        forge: { DEFAULT: '#7c5cff', dim: '#5840d0' },
        accent: '#00e5ff',
        ivory: '#f5f5ff',
        muted: '#9b9bb0',
      },
      fontFamily: {
        sans: ['ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Consolas', 'monospace'],
      },
      boxShadow: {
        glow: '0 0 28px rgba(124,92,255,0.28)',
        glowa: '0 0 28px rgba(0,229,255,0.18)',
      },
      keyframes: {
        breathe: {
          '0%,100%': { opacity: '1' },
          '50%': { opacity: '0.45' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        rise: {
          '0%': { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        breathe: 'breathe 1.6s ease-in-out infinite',
        shimmer: 'shimmer 2.4s linear infinite',
        rise: 'rise .28s ease-out both',
      },
    },
  },
  plugins: [],
};

export default config;
