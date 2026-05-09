/**
 * Theme Management Hook
 * Light mode only — dark mode has been removed.
 */

import { useCallback } from 'react';

type Theme = 'light';

// Always light
function _applyLightTheme(): void {
  const root = document.documentElement;
  root.classList.remove('dark');
  root.classList.add('light');
  root.setAttribute('data-theme', 'light');

  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute('content', '#ffffff');
}

// ─── Hook ────────────────────────────────────────────────────
export function useTheme() {
  return {
    theme: 'light' as Theme,
    isDark: false,
    isLight: true,
    toggleTheme: useCallback(() => {}, []),
    setTheme: useCallback((_t: Theme) => {}, []),
  };
}

// ─── Initialisation ──────────────────────────────────────────
export function initializeTheme(): void {
  if (typeof document === 'undefined') return;
  _applyLightTheme();
}

if (typeof window !== 'undefined') {
  initializeTheme();
}

export type { Theme };
