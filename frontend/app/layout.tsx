'use client'

import { Inter } from 'next/font/google'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState, useEffect } from 'react'
import { ThemeProvider } from 'next-themes'
import './globals.css'
import { Sidebar } from '@/components/ui/sidebar'
import { useAuthStore } from '@/lib/store/auth-store'
import { usePathname } from 'next/navigation'

const inter = Inter({ subsets: ['latin'] })

const publicPaths = ['/login', '/signup', '/billing']

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
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

  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  const isPublicPath = publicPaths.includes(pathname)

  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <head>
        <title>EnrichStory</title>
        <meta name="description" content="Plataforma de enriquecimento de dados" />
      </head>
      <body className={inter.className}>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          <QueryClientProvider client={queryClient}>
            <div className="flex h-screen bg-background">
              {isAuthenticated && !isPublicPath && <Sidebar />}
              <main className={`flex-1 overflow-auto ${!isAuthenticated || isPublicPath ? 'w-full' : ''}`}>
                {children}
              </main>
            </div>
          </QueryClientProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}