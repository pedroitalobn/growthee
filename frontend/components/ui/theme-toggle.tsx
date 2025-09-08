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
      className="transition-all duration-200 ease-out hover:scale-105 hover:bg-accent/50"
    >
      <Sun className="h-5 w-5 rotate-0 scale-100 transition-all duration-300 ease-out dark:-rotate-90 dark:scale-0" />
      <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all duration-300 ease-out dark:rotate-0 dark:scale-100" />
      <span className="sr-only">Alternar tema</span>
    </Button>
  )
}