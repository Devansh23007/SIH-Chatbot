import { useCallback, useEffect, useState } from 'react';

export type Theme = 'light' | 'dark';

function detectHostTheme(): Theme {
  if (typeof document === 'undefined') return 'light';
  const el = document.documentElement;
  if (el.classList.contains('dark') || el.dataset.theme === 'dark') return 'dark';
  if (el.classList.contains('light') || el.dataset.theme === 'light') return 'light';
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

/**
 * Follows the NCCT app's theme (html.dark / data-theme / OS setting) so no competing theme system exists.
 * - Pass `theme` to fully control it from the host's theme provider.
 * - Pass `onThemeChange` to forward the toggle button to the host's provider.
 * Without either, the toggle only overrides the chatbot (in memory, nothing persisted).
 */
export function useTheme(controlled?: Theme, onThemeChange?: (t: Theme) => void) {
  const [host, setHost] = useState<Theme>(detectHostTheme);
  const [override, setOverride] = useState<Theme | null>(null);

  useEffect(() => {
    const update = () => setHost(detectHostTheme());
    const observer = new MutationObserver(update);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class', 'data-theme'] });
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    mq.addEventListener('change', update);
    return () => { observer.disconnect(); mq.removeEventListener('change', update); };
  }, []);

  const theme = controlled ?? override ?? host;
  const toggleTheme = useCallback(() => {
    const next: Theme = theme === 'dark' ? 'light' : 'dark';
    setOverride(next);
    onThemeChange?.(next);
  }, [theme, onThemeChange]);

  return { theme, toggleTheme };
}
