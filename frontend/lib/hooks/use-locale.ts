'use client'

import { useLocale } from 'next-intl'
import { enUS, ptBR, es } from 'date-fns/locale'
import type { Locale } from 'date-fns'

const localeMap: Record<string, Locale> = {
  en: enUS,
  pt: ptBR,
  es: es
}

export function useLocaleForDateFns(): Locale {
  try {
    const locale = useLocale()
    return localeMap[locale] || enUS
  } catch {
    return enUS
  }
}

export function useCurrentLocale(): string {
  try {
    return useLocale()
  } catch {
    return 'en'
  }
}