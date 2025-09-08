import { getRequestConfig } from 'next-intl/server';

// Supported locales
export const locales = ['en', 'pt', 'es'] as const;
export type Locale = typeof locales[number];

export default getRequestConfig(async ({ locale }) => {
  return {
    messages: (await import(`./messages/${locale}.json`)).default,
    timeZone: 'America/Sao_Paulo',
    locale
  };
});

export const defaultLocale: Locale = 'pt';