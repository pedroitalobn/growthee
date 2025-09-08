'use client'

import React from 'react'
import { NextIntlClientProvider } from 'next-intl'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState, useEffect } from 'react'
import { useAuthStore } from '@/lib/store/auth-store'
import { usePathname, useRouter } from 'next/navigation'
import { Sidebar } from '@/components/ui/sidebar'
import { ThemeProvider } from 'next-themes'

export function LocaleLayoutClient({
  children,
  locale,
  messages
}: {
  children: React.ReactNode
  locale: string
  messages: any
}) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000,
        refetchOnWindowFocus: false,
        retry: 1,
      },
    },
  }))

  const isAuthenticated = useAuthStore(state => state.isAuthenticated)
  const checkAuth = useAuthStore(state => state.checkAuth)
  const pathname = usePathname()
  const router = useRouter()

  useEffect(() => {
    checkAuth()
    // Set the document lang attribute dynamically to avoid hydration mismatch
    if (typeof document !== 'undefined') {
      document.documentElement.lang = locale
    }
  }, [checkAuth, locale])

  const publicPaths = ['/login', '/signup', '/billing', '/']
  const basePathname = pathname.split('/').slice(2).join('/') || '/'
  const isPublicPath = publicPaths.includes(`/${basePathname}`) || publicPaths.includes(basePathname)

  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <NextIntlClientProvider locale={locale} messages={messages}>
        <QueryClientProvider client={queryClient}>
          <div className="flex h-screen bg-background">
            {isAuthenticated && !isPublicPath && <Sidebar />}
            <main className={`flex-1 overflow-auto ${!isAuthenticated || isPublicPath ? 'w-full' : ''}`}>
              {children}
            </main>
          </div>
        </QueryClientProvider>
      </NextIntlClientProvider>
    </ThemeProvider>
  )
}