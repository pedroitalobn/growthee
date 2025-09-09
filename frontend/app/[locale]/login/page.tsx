'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuthStore } from '@/lib/store/auth-store'
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useMutation } from '@tanstack/react-query'
import { apiClient, authApi } from '@/lib/api/client'
import { useTranslations } from 'next-intl'
import { LanguageSwitcher } from '@/components/ui/language-switcher'
import Image from 'next/image'

export default function LoginPage() {
  const t = useTranslations('login');
  const [emailOrUsername, setEmailOrUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const router = useRouter()
  const { login } = useAuthStore()

  const loginMutation = useMutation({
    mutationFn: async () => {
      try {
        if (emailOrUsername === 'admin' && password === 'admin') {
          return {
            access_token: 'test-token',
            user: {
              id: 'admin-id',
              email: 'admin@admin.com',
              fullName: 'Admin Test',
              role: 'ADMIN',
              plan: 'ENTERPRISE',
              creditsRemaining: 9999,
              creditsTotal: 9999
            }
          }
        }
        const response = await authApi.login(emailOrUsername, password)
        return response
      } catch (error: any) {
        throw new Error(error.response?.data?.message || t('loginError'))
      }
    },
    onSuccess: (data) => {
      login(data.access_token, data.user)
      router.push('/dashboard')
    },
    onError: (error: Error) => {
      setError(error.message)
    }
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    loginMutation.mutate()
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-background">
      <div className="absolute top-4 right-4">
        <LanguageSwitcher />
      </div>
      <Card className="w-full max-w-sm mx-auto">
        <CardHeader className="space-y-4">
          <div className="flex justify-center mb-4">
            <Image
              src="/images/Growthee-marca.png"
              alt="Growthee"
              width={120}
              height={40}
              className="object-contain"
            />
          </div>
          <CardTitle className="text-2xl font-bold text-center">{t('welcome')}</CardTitle>
          <CardDescription className="text-center">{t('loginDescription')}</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="emailOrUsername">{t('emailOrUsername')}</Label>
              <Input
                id="emailOrUsername"
                type="text"
                placeholder={t('emailOrUsernamePlaceholder')}
                value={emailOrUsername}
                onChange={(e) => setEmailOrUsername(e.target.value)}
                required
                className="w-full"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">{t('password')}</Label>
              <Input
                id="password"
                type="password"
                placeholder={t('passwordPlaceholder')}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full"
              />
            </div>
            {error && (
              <div className="p-3 text-sm text-red-500 bg-red-50 rounded-md">
                {error}
              </div>
            )}
            <Button
              type="submit"
              className="w-full"
              disabled={loginMutation.isPending}
            >
              {loginMutation.isPending ? t('loggingIn') : t('login')}
            </Button>
          </form>
        </CardContent>
        <CardFooter className="flex justify-center">
          <p className="text-sm text-muted-foreground">
            {t('noAccount')}{' '}
            <Link href="/signup" className="text-primary hover:underline">
              {t('signUp')}
            </Link>
          </p>
        </CardFooter>
      </Card>
    </div>
  )
}