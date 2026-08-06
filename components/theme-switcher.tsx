'use client'

import { useAppStore } from '@/lib/store'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { themes } from '@/lib/themes'
import type { ThemeType } from '@/lib/store'
import { Palette } from 'lucide-react'

export function ThemeSwitcher() {
  const { theme, setTheme } = useAppStore()

  const themeList: Array<{ name: ThemeType; label: string }> = [
    { name: 'light', label: 'Light' },
    { name: 'dark', label: 'Dark' },
    { name: 'dust-pink', label: 'Dust Pink' },
    { name: 'blue', label: 'Blue' },
    { name: 'green', label: 'Green' },
    { name: 'purple', label: 'Purple' },
  ]

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="icon">
          <Palette className="h-4 w-4" />
          <span className="sr-only">Toggle theme</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {themeList.map((t) => (
          <DropdownMenuItem
            key={t.name}
            onClick={() => setTheme(t.name)}
            className="flex items-center justify-between"
          >
            <span>{t.label}</span>
            {theme === t.name && (
              <div className="h-2 w-2 rounded-full bg-primary" />
            )}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
