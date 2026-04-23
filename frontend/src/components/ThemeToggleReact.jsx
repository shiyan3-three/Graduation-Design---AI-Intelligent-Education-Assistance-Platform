export function ThemeToggle({ theme, onToggle }) {
  const nextThemeLabel = theme === 'dark' ? '切换浅色' : '切换深色';

  return (
    <button type="button" className="theme-toggle" onClick={onToggle}>
      <span className="theme-toggle__swatch" aria-hidden="true" />
      <span>{nextThemeLabel}</span>
    </button>
  );
}
