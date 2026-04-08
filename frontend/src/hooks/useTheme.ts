/**
 * Theme Management Hook
 * Supports Light/Dark mode with localStorage persistence
 *
 * Uses module-level shared state so all components stay in sync.
 * When any component toggles the theme, every mounted component
 * that calls useTheme() re-renders with the new value.
 */

import { useState, useEffect, useCallback } from 'react';

type Theme = 'light' | 'dark';

const THEME_KEY = 'my-ai-company-theme';

// ─── Shared state (module-level) ─────────────────────────────
let _currentTheme: Theme;
const _listeners = new Set<(theme: Theme) => void>();

function _getInitialTheme(): Theme {
  if (typeof window === 'undefined') return 'light';

  const stored = localStorage.getItem(THEME_KEY) as Theme | null;
  if (stored === 'light' || stored === 'dark') return stored;

  if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark';
  }
  return 'light';
}

// Initialise once when the module loads
_currentTheme = _getInitialTheme();

function _applyTheme(theme: Theme): void {
  const root = document.documentElement;
  root.classList.remove('light', 'dark');
  root.classList.add(theme);
  root.setAttribute('data-theme', theme);

  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute('content', theme === 'dark' ? '#0f172a' : '#ffffff');
}

function _setTheme(newTheme: Theme): void {
  if (newTheme === _currentTheme) return;
  _currentTheme = newTheme;
  _applyTheme(newTheme);
  localStorage.setItem(THEME_KEY, newTheme);
  _listeners.forEach((fn) => fn(newTheme));
}

// ─── Hook ────────────────────────────────────────────────────
export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(_currentTheme);

  // Subscribe to shared state
  useEffect(() => {
    _listeners.add(setThemeState);
    return () => { _listeners.delete(setThemeState); };
  }, []);

  // Sync on mount in case theme was changed before this component mounted
  useEffect(() => {
    if (theme !== _currentTheme) setThemeState(_currentTheme);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Listen for system preference changes
  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = (e: MediaQueryListEvent) => {
      if (!localStorage.getItem(THEME_KEY)) {
        _setTheme(e.matches ? 'dark' : 'light');
      }
    };
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  const toggleTheme = useCallback(() => {
    _setTheme(_currentTheme === 'light' ? 'dark' : 'light');
  }, []);

  const setTheme = useCallback((t: Theme) => {
    _setTheme(t);
  }, []);

  return {
    theme,
    isDark: theme === 'dark',
    isLight: theme === 'light',
    toggleTheme,
    setTheme,
  };
}

// ─── Initialisation ──────────────────────────────────────────
export function initializeTheme(): void {
  if (typeof document === 'undefined') return;
  _applyTheme(_currentTheme);
}

if (typeof window !== 'undefined') {
  initializeTheme();
}

export type { Theme };
