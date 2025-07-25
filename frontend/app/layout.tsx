'use client'

import { Inter } from 'next/font/google'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState, useEffect } from 'react'
import { useTheme } from 'next-themes'
import './globals.css'
import { Sidebar } from '@/components/ui/sidebar'

const inter = Inter({ subsets: ['latin'] })

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

  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <head>
        <title>EnrichStory</title>
        <meta name="description" content="Plataforma de enriquecimento de dados" />
      </head>
      <body className={inter.className}>
        <QueryClientProvider client={queryClient}>
          <div className="flex h-screen">
            <Sidebar />
            <main className="flex-1 overflow-auto">
              {children}
            </main>
          </div>
        </QueryClientProvider>
      </body>
    </html>
  )
}