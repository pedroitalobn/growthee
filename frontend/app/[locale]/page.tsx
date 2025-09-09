'use client'

import { useEffect } from 'react'
import { useTranslations } from 'next-intl'
import { useRouter, useParams } from 'next/navigation'
import { useAuthStore } from '@/lib/store/auth-store'

export default function HomePage() {
  const t = useTranslations('common')
  const router = useRouter()
  const params = useParams()
  const locale = params.locale as string
  const { user, isAuthenticated } = useAuthStore()

  useEffect(() => {
    if (isAuthenticated && user) {
      // Redireciona baseado no role do usuário
      if (user.role === 'SUPER_ADMIN') {
        router.push(`/${locale}/admin`)
      } else {
        router.push(`/${locale}/dashboard`)
      }
    } else {
      // Se não está autenticado, redireciona para o login
      router.push(`/${locale}/login`)
    }
  }, [isAuthenticated, user, router, locale])

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-2xl font-bold mb-4">{t('appName')}</h1>
        <p className="text-muted-foreground">{t('redirecting')}</p>
      </div>
    </div>
  )
}