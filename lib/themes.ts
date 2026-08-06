export interface ThemeConfig {
  name: string
  label: string
  colors: {
    background: string
    foreground: string
    card: string
    'card-foreground': string
    primary: string
    'primary-foreground': string
    secondary: string
    'secondary-foreground': string
    accent: string
    'accent-foreground': string
    muted: string
    'muted-foreground': string
    destructive: string
    border: string
    input: string
    ring: string
  }
}

export const themes: Record<string, ThemeConfig> = {
  light: {
    name: 'light',
    label: 'Light',
    colors: {
      background: 'oklch(1 0 0)',
      foreground: 'oklch(0.145 0 0)',
      card: 'oklch(1 0 0)',
      'card-foreground': 'oklch(0.145 0 0)',
      primary: 'oklch(0.205 0 0)',
      'primary-foreground': 'oklch(0.985 0 0)',
      secondary: 'oklch(0.97 0 0)',
      'secondary-foreground': 'oklch(0.205 0 0)',
      accent: 'oklch(0.97 0 0)',
      'accent-foreground': 'oklch(0.205 0 0)',
      muted: 'oklch(0.97 0 0)',
      'muted-foreground': 'oklch(0.556 0 0)',
      destructive: 'oklch(0.577 0.245 27.325)',
      border: 'oklch(0.922 0 0)',
      input: 'oklch(0.922 0 0)',
      ring: 'oklch(0.708 0 0)',
    },
  },
  dark: {
    name: 'dark',
    label: 'Dark',
    colors: {
      background: 'oklch(0.145 0 0)',
      foreground: 'oklch(0.985 0 0)',
      card: 'oklch(0.205 0 0)',
      'card-foreground': 'oklch(0.985 0 0)',
      primary: 'oklch(0.922 0 0)',
      'primary-foreground': 'oklch(0.205 0 0)',
      secondary: 'oklch(0.269 0 0)',
      'secondary-foreground': 'oklch(0.985 0 0)',
      accent: 'oklch(0.269 0 0)',
      'accent-foreground': 'oklch(0.985 0 0)',
      muted: 'oklch(0.269 0 0)',
      'muted-foreground': 'oklch(0.708 0 0)',
      destructive: 'oklch(0.704 0.191 22.216)',
      border: 'oklch(1 0 0 / 10%)',
      input: 'oklch(1 0 0 / 15%)',
      ring: 'oklch(0.556 0 0)',
    },
  },
  'dust-pink': {
    name: 'dust-pink',
    label: 'Dust Pink',
    colors: {
      background: 'oklch(0.98 0.02 25)',
      foreground: 'oklch(0.2 0.05 25)',
      card: 'oklch(1 0 0)',
      'card-foreground': 'oklch(0.2 0.05 25)',
      primary: 'oklch(0.7 0.15 15)',
      'primary-foreground': 'oklch(1 0 0)',
      secondary: 'oklch(0.92 0.08 20)',
      'secondary-foreground': 'oklch(0.3 0.05 25)',
      accent: 'oklch(0.75 0.12 10)',
      'accent-foreground': 'oklch(1 0 0)',
      muted: 'oklch(0.88 0.04 20)',
      'muted-foreground': 'oklch(0.5 0.03 25)',
      destructive: 'oklch(0.6 0.2 25)',
      border: 'oklch(0.92 0.06 20)',
      input: 'oklch(0.95 0.03 20)',
      ring: 'oklch(0.7 0.12 15)',
    },
  },
  blue: {
    name: 'blue',
    label: 'Blue',
    colors: {
      background: 'oklch(0.14 0.02 260)',
      foreground: 'oklch(0.98 0.02 260)',
      card: 'oklch(0.2 0.04 260)',
      'card-foreground': 'oklch(0.98 0.02 260)',
      primary: 'oklch(0.5 0.15 260)',
      'primary-foreground': 'oklch(0.98 0.02 260)',
      secondary: 'oklch(0.25 0.08 260)',
      'secondary-foreground': 'oklch(0.98 0.02 260)',
      accent: 'oklch(0.65 0.18 260)',
      'accent-foreground': 'oklch(0.1 0.02 260)',
      muted: 'oklch(0.28 0.05 260)',
      'muted-foreground': 'oklch(0.7 0.08 260)',
      destructive: 'oklch(0.6 0.2 25)',
      border: 'oklch(1 0 0 / 10%)',
      input: 'oklch(1 0 0 / 15%)',
      ring: 'oklch(0.6 0.15 260)',
    },
  },
  green: {
    name: 'green',
    label: 'Green',
    colors: {
      background: 'oklch(0.14 0.02 140)',
      foreground: 'oklch(0.98 0.02 140)',
      card: 'oklch(0.2 0.04 140)',
      'card-foreground': 'oklch(0.98 0.02 140)',
      primary: 'oklch(0.5 0.15 140)',
      'primary-foreground': 'oklch(0.98 0.02 140)',
      secondary: 'oklch(0.25 0.08 140)',
      'secondary-foreground': 'oklch(0.98 0.02 140)',
      accent: 'oklch(0.65 0.18 140)',
      'accent-foreground': 'oklch(0.1 0.02 140)',
      muted: 'oklch(0.28 0.05 140)',
      'muted-foreground': 'oklch(0.7 0.08 140)',
      destructive: 'oklch(0.6 0.2 25)',
      border: 'oklch(1 0 0 / 10%)',
      input: 'oklch(1 0 0 / 15%)',
      ring: 'oklch(0.6 0.15 140)',
    },
  },
  purple: {
    name: 'purple',
    label: 'Purple',
    colors: {
      background: 'oklch(0.14 0.02 290)',
      foreground: 'oklch(0.98 0.02 290)',
      card: 'oklch(0.2 0.04 290)',
      'card-foreground': 'oklch(0.98 0.02 290)',
      primary: 'oklch(0.5 0.15 290)',
      'primary-foreground': 'oklch(0.98 0.02 290)',
      secondary: 'oklch(0.25 0.08 290)',
      'secondary-foreground': 'oklch(0.98 0.02 290)',
      accent: 'oklch(0.65 0.18 290)',
      'accent-foreground': 'oklch(0.1 0.02 290)',
      muted: 'oklch(0.28 0.05 290)',
      'muted-foreground': 'oklch(0.7 0.08 290)',
      destructive: 'oklch(0.6 0.2 25)',
      border: 'oklch(1 0 0 / 10%)',
      input: 'oklch(1 0 0 / 15%)',
      ring: 'oklch(0.6 0.15 290)',
    },
  },
}

export function applyTheme(themeName: string) {
  const theme = themes[themeName]
  if (!theme) return

  const root = document.documentElement
  Object.entries(theme.colors).forEach(([key, value]) => {
    root.style.setProperty(`--${key}`, value)
  })
}
