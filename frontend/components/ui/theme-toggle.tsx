'use client'

import * as React from 'react'
import { Moon, Sun } from 'lucide-react'
import { useTheme } from 'next-themes'
import { Button } from '@/components/ui/button'

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
      className="hover:bg-accent"
    >
      <Sun className="h-5 w-5 dark:hidden" />
      <Moon className="h-5 w-5 hidden dark:block" />
      <span className="sr-only">Alternar tema</span>
    </Button>
  )
}