import { create } from 'zustand'
import type { Theme } from '../types'

const THEMES: Theme[] = ['light', 'dark', 'premium', 'aurora', 'luxury']

interface ThemeMeta {
  label: string
  icon: string
}

const THEME_META: Record<Theme, ThemeMeta> = {
  light: { label: 'Light', icon: 'Sun' },
  dark: { label: 'Dark', icon: 'Moon' },
  premium: { label: 'Violet', icon: 'Sparkles' },
  aurora: { label: 'Aurora', icon: 'Waves' },
  luxury: { label: 'Luxury', icon: 'Crown' },
}

const getInitialTheme = (): Theme => {
  if (typeof window === 'undefined') return 'dark'
  const stored = localStorage.getItem('campusiq-theme') as Theme | null
  if (stored && THEMES.includes(stored)) return stored
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function applyTheme(theme: Theme): void {
  const root = document.documentElement
  THEMES.forEach((t) => root.classList.remove(t))
  if (theme !== 'light') root.classList.add(theme)
}

interface ThemeStore {
  theme: Theme
  cycle: () => void
  setTheme: (theme: Theme) => void
}

const useThemeStore = create<ThemeStore>((set) => ({
  theme: getInitialTheme(),
  cycle: () =>
    set((state) => {
      const idx = THEMES.indexOf(state.theme)
      const next = THEMES[(idx + 1) % THEMES.length]!
      localStorage.setItem('campusiq-theme', next)
      applyTheme(next)
      return { theme: next }
    }),
  setTheme: (theme) => {
    localStorage.setItem('campusiq-theme', theme)
    applyTheme(theme)
    set({ theme })
  },
}))

if (typeof window !== 'undefined') {
  applyTheme(getInitialTheme())
}

interface UseThemeReturn {
  theme: Theme
  cycle: () => void
  setTheme: (theme: Theme) => void
  themes: Theme[]
  meta: Record<Theme, ThemeMeta>
}

export const useTheme = (): UseThemeReturn => {
  const theme = useThemeStore((s) => s.theme)
  const cycle = useThemeStore((s) => s.cycle)
  const setTheme = useThemeStore((s) => s.setTheme)
  return { theme, cycle, setTheme, themes: THEMES, meta: THEME_META }
}
