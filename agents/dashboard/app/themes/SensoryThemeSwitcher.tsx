'use client';

import React from 'react';
import { useSensoryTheme, type SensoryTheme } from './SensoryThemeProvider';

const THEMES: { id: SensoryTheme; label: string; emoji: string; description: string }[] = [
  {
    id: 'calm',
    label: 'CALM',
    emoji: '🌙',
    description: 'Muted colours, no motion, OpenDyslexic font — low sensory load',
  },
  {
    id: 'focus',
    label: 'FOCUS',
    emoji: '🎯',
    description: 'High-contrast cyan, minimal animation — sharp and clear',
  },
  {
    id: 'energise',
    label: 'ENERGISE',
    emoji: '⚡',
    description: 'Vibrant purple/pink, full animations — maximum flow state',
  },
];

export function SensoryThemeSwitcher() {
  const { theme, setTheme } = useSensoryTheme();

  return (
    <div
      role="group"
      aria-label="Sensory theme selector"
      className="flex gap-2 items-center"
    >
      <span className="text-xs opacity-60 mr-1 sr-only sm:not-sr-only" id="theme-switcher-label">
        Sensory Profile:
      </span>
      {THEMES.map((t) => (
        <button
          key={t.id}
          onClick={() => setTheme(t.id)}
          aria-pressed={theme === t.id}
          aria-describedby={`theme-desc-${t.id}`}
          title={t.description}
          className={`
            px-3 py-1.5 rounded text-xs font-bold tracking-wide
            border transition-all
            focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-black
            ${
              theme === t.id
                ? 'border-[var(--hc-color-accent)] bg-[var(--hc-color-accent)] text-black focus:ring-[var(--hc-color-accent)]'
                : 'border-[var(--hc-color-border)] text-[var(--hc-color-text-secondary)] hover:border-[var(--hc-color-accent)] focus:ring-[var(--hc-color-accent)]'
            }
          `}
        >
          <span aria-hidden="true">{t.emoji}</span>{' '}
          {t.label}
        </button>
      ))}
      {/* Hidden descriptions for screen readers */}
      {THEMES.map((t) => (
        <span key={`desc-${t.id}`} id={`theme-desc-${t.id}`} className="sr-only">
          {t.description}
        </span>
      ))}
    </div>
  );
}
