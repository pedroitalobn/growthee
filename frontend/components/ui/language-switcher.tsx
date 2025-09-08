'use client'

import { useRouter, usePathname } from 'next/navigation'
import { useLocale } from 'next-intl'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Globe } from 'lucide-react'
import { locales } from '@/i18n'

const languageNames = {
  pt: 'Português',
  en: 'English',
  es: 'Español'
}

export function LanguageSwitcher() {
  const router = useRouter()
  const pathname = usePathname()
  
  // Safely get locale with fallback
  let locale: string
  
  try {
    locale = useLocale()
  } catch (error) {
    // Fallback if intl context is not available
    locale = 'en'
  }

  const switchLanguage = (newLocale: string) => {
    // Remove current locale from pathname and add new one
    const pathWithoutLocale = pathname.replace(`/${locale}`, '') || '/'
    const newPath = `/${newLocale}${pathWithoutLocale}`
    router.replace(newPath)
    // Force page reload to ensure locale change takes effect
    window.location.href = newPath
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm" className="h-8 w-8 p-0 transition-all duration-200 ease-out hover:scale-105 hover:bg-accent/50">
          <Globe className="h-4 w-4 transition-transform duration-200 ease-out" />
          <span className="sr-only">Switch language</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {locales.map((lang) => (
          <DropdownMenuItem
            key={lang}
            onClick={() => switchLanguage(lang)}
            className={`transition-colors duration-200 ease-out hover:bg-accent/50 ${locale === lang ? 'bg-accent' : ''}`}
          >
            {languageNames[lang as keyof typeof languageNames]}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}