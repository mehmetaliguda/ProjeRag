'use client'

import { useEffect } from 'react'
import { useAppStore } from '@/lib/store'
import { applyTheme } from '@/lib/themes'

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const { theme } = useAppStore()

  useEffect(() => {
    if (typeof document !== 'undefined') {
      applyTheme(theme)
      document.documentElement.setAttribute('data-theme', theme)
    }
  }, [theme])

  return <>{children}</>
}