import { useEffect, useState } from 'react';
import { getNextTheme, resolveInitialTheme, THEME_STORAGE_KEY } from '../theme-state.js';

export function useGlobalTheme() {
  const [theme, setTheme] = useState(() =>
    resolveInitialTheme(() => {
      if (typeof window === 'undefined') return 'light';
      return window.localStorage.getItem(THEME_STORAGE_KEY);
    })
  );

  useEffect(() => {
    if (typeof document !== 'undefined') {
      document.documentElement.dataset.theme = theme;
      document.documentElement.style.colorScheme = theme;
    }

    if (typeof window !== 'undefined') {
      try {
        window.localStorage.setItem(THEME_STORAGE_KEY, theme);
      } catch (_) {
        // Ignore localStorage errors
      }
    }
  }, [theme]);

  function toggleTheme() {
    setTheme((currentTheme) => getNextTheme(currentTheme));
  }

  return { theme, toggleTheme };
}
