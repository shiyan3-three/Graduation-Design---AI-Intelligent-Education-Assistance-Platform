export const THEME_STORAGE_KEY = 'frontend-theme';
const THEMES = new Set(['light', 'dark']);

export function normalizeTheme(value) {
  return THEMES.has(value) ? value : 'light';
}

export function getNextTheme(currentTheme) {
  return normalizeTheme(currentTheme) === 'dark' ? 'light' : 'dark';
}

export function resolveInitialTheme(readStoredTheme) {
  try {
    return normalizeTheme(readStoredTheme?.());
  } catch (_) {
    return 'light';
  }
}
