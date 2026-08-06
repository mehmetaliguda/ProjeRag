'use client'

import { useEffect } from 'react'
import { useAppStore } from '@/lib/store'
import { applyTheme } from '@/lib/themes'
import type { ThemeType } from '@/lib/store'

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const { theme, setTheme } = useAppStore()

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
      const stored = localStorage.getItem('theme') as ThemeType | null
      const themeToUse = stored || (prefersDark ? 'dark' : 'light')
      setTheme(themeToUse)
    }
  }, [setTheme])

  useEffect(() => {
    if (typeof document !== 'undefined') {
      localStorage.setItem('theme', theme)
      applyTheme(theme)
      document.documentElement.setAttribute('data-theme', theme)
    }
  }, [theme])

  return <>{children}</>
}
