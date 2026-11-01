import type { Metadata, Viewport } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: {
    default: 'CINEFORGE — AI Video Studio',
    template: '%s · CINEFORGE',
  },
  description:
    'The AI-native video studio: chat with a director agent that scripts, storyboards, generates, edits and renders your video — from prompt to premiere.',
};

export const viewport: Viewport = {
  themeColor: '#0a0a12',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen font-sans text-ivory antialiased">{children}</body>
    </html>
  );
}
