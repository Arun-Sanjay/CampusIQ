import { create } from 'zustand'

const THEMES = ['light', 'dark', 'premium', 'aurora', 'luxury']

const THEME_META = {
  light:   { label: 'Light',   icon: 'Sun' },
  dark:    { label: 'Dark',    icon: 'Moon' },
  premium: { label: 'Violet',  icon: 'Sparkles' },
  aurora:  { label: 'Aurora',  icon: 'Waves' },
  luxury:  { label: 'Luxury',  icon: 'Crown' },
}

const getInitialTheme = () => {
  if (typeof window === 'undefined') return 'dark'
  const stored = localStorage.getItem('campusiq-theme')
  if (stored && THEMES.includes(stored)) return stored
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function applyTheme(theme) {
  const root = document.documentElement
  THEMES.forEach(t => root.classList.remove(t))
  if (theme !== 'light') root.classList.add(theme)
}

const useThemeStore = create((set) => ({
  theme: getInitialTheme(),
  cycle: () => set((state) => {
    const idx = THEMES.indexOf(state.theme)
    const next = THEMES[(idx + 1) % THEMES.length]
    localStorage.setItem('campusiq-theme', next)
    applyTheme(next)
    return { theme: next }
  }),
  setTheme: (theme) => set(() => {
    localStorage.setItem('campusiq-theme', theme)
    applyTheme(theme)
    return { theme }
  }),
}))

if (typeof window !== 'undefined') {
  applyTheme(getInitialTheme())
}

export const useTheme = () => {
  const theme = useThemeStore((s) => s.theme)
  const cycle = useThemeStore((s) => s.cycle)
  const setTheme = useThemeStore((s) => s.setTheme)
  return { theme, cycle, setTheme, themes: THEMES, meta: THEME_META }
}
