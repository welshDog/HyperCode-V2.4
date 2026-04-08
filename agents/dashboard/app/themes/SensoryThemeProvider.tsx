'use client';

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';

export type SensoryTheme = 'calm' | 'focus' | 'energise';

interface SensoryThemeContextValue {
  theme: SensoryTheme;
  setTheme: (t: SensoryTheme) => void;
}

const SensoryThemeContext = createContext<SensoryThemeContextValue>({
  theme: 'focus',
  setTheme: () => {},
});

const STORAGE_KEY = 'hc-sensory-theme';

export function SensoryThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<SensoryTheme>(() => {
    if (typeof window === 'undefined') return 'focus';
    const saved = localStorage.getItem(STORAGE_KEY) as SensoryTheme | null;
    if (saved && ['calm', 'focus', 'energise'].includes(saved)) return saved;
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'calm' : 'focus';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-hc-theme', theme);
  }, [theme]);

  const setTheme = useCallback((t: SensoryTheme) => {
    setThemeState(t);
    document.documentElement.setAttribute('data-hc-theme', t);
    localStorage.setItem(STORAGE_KEY, t);
  }, []);

  return (
    <SensoryThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </SensoryThemeContext.Provider>
  );
}

export function useSensoryTheme() {
  return useContext(SensoryThemeContext);
}
