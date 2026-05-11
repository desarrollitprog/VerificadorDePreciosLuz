import { create } from 'zustand';

interface ThemeState {
  isDark: boolean;
  toggle: () => void;
}

const getInitialTheme = (): boolean => {
  try {
    const stored = localStorage.getItem('theme');
    if (stored) return stored === 'dark';
  } catch {}
  return document.documentElement.classList.contains('dark');
};

export const useThemeStore = create<ThemeState>((set) => ({
  isDark: getInitialTheme(),
  toggle: () => {
    set((state) => {
      const next = !state.isDark;
      try {
        localStorage.setItem('theme', next ? 'dark' : 'light');
      } catch {}
      document.documentElement.classList.toggle('dark', next);
      return { isDark: next };
    });
  },
}));
