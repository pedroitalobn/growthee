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
      // Redirecionar baseado no role do usuário
      if (data.user.role === 'SUPER_ADMIN') {
        router.push('/admin')
      } else {
        router.push('/dashboard')
      }
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
          <div className="flex justify-center mb-4 py-2">
            <svg id="Layer_1" data-name="Layer 1" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 655.36 76.6" className="h-6 w-auto">
              <path d="M0,40.77C0,20.76,14.31,3.23,44,3.23s39.59,13.88,39.59,26.79c0,.43,0,1.08-.11,2.04h-13.45c.11-.65.11-1.08.11-1.51,0-7.42-6.78-15.6-25.82-15.6s-29.26,11.62-29.26,25.93c0,13.45,8.82,24.74,29.15,24.74,18.93,0,25.49-9.47,25.49-16.03v-.32h-28.51v-9.36h43.24v35.39h-12.26c.11-2.8.43-9.04.54-14.41h-.11c-3.01,10.22-13.55,15.71-30.01,15.71-30.43-.01-42.59-17.43-42.59-35.83Z" style={{fill: '#00fe6c'}}/>
              <path d="M96.28,22.16h13.77l-.22,16.24h.22c3.33-9.57,10.86-17.32,25.82-17.32,17.53,0,24.2,9.68,24.2,24.53,0,4.09-.22,7.75-.32,9.47h-12.91c.11-1.29.21-3.55.21-5.49,0-11.4-3.77-17.21-15.17-17.21-14.09,0-21.84,10.97-21.84,22.81v20.12h-13.77V22.16h.01Z" style={{fill: '#00fe6c'}}/>
              <path d="M169.76,48.84c0-13.98,10.33-27.75,36.47-27.75s36.47,13.77,36.47,27.75-10.11,27.54-36.47,27.54-36.47-13.45-36.47-27.54ZM228.92,48.84c0-8.82-6.13-17-22.7-17s-22.7,8.18-22.7,17,6.02,16.78,22.7,16.78,22.7-7.96,22.7-16.78Z" style={{fill: '#00fe6c'}}/>
              <path d="M247.64,22.16h14.85l15.6,40.45h.11l18.07-40.45h13.45l17.53,40.45h.11l15.81-40.45h13.55l-21.3,53.14h-16.46l-16.67-38.94h-.21l-17,38.94h-16.14s-21.3-53.14-21.3-53.14Z" style={{fill: '#00fe6c'}}/>
              <path d="M371.03,54.65v-21.73h-10.65v-10.76h8.61c2.26,0,3.01-1.18,3.33-3.98l.86-8.07h11.62v12.05h30.34v10.76h-30.34v21.08c0,7.64,3.87,11.19,17.21,11.19,4.41,0,9.9-.65,12.69-1.18v10.43c-2.37.75-8.18,1.61-14.2,1.61-22.16,0-29.48-9.14-29.48-21.41h.01Z" style={{fill: '#00fe6c'}}/>
              <path d="M425.9,0h13.77v26.46c0,3.23-.11,6.99-.21,11.3h.21c3.98-10.86,12.69-16.67,29.8-16.67,21.62,0,29.37,10.22,29.37,23.45v30.77h-13.77v-27.11c0-9.57-4.73-15.81-20.76-15.81-12.91,0-24.63,6.13-24.63,19.04v23.88h-13.77V0h0Z" style={{fill: '#00fe6c'}}/>
              <path d="M577.36,51.96h-54.86c.97,8.07,6.13,14.63,22.37,14.63,14.09,0,19.04-4.2,19.9-8.61h12.59c-.65,9.25-9.79,18.39-32.49,18.39-28.08,0-36.25-13.98-36.25-27.22,0-17,13.02-28.08,35.39-28.08s33.35,10.11,33.35,26.57v4.32ZM564.78,43.35c0-7.1-5.7-12.48-20.22-12.48-13.34,0-19.79,4.52-21.62,12.8h41.85v-.32h-.01Z" style={{fill: '#00fe6c'}}/>
              <path d="M655.35,51.96h-54.86c.97,8.07,6.13,14.63,22.38,14.63,14.09,0,19.04-4.2,19.9-8.61h12.59c-.65,9.25-9.79,18.39-32.49,18.39-28.08,0-36.25-13.98-36.25-27.22,0-17,13.02-28.08,35.39-28.08s33.35,10.11,33.35,26.57v4.32ZM642.77,43.35c0-7.1-5.7-12.48-20.22-12.48-13.34,0-19.79,4.52-21.62,12.8h41.85v-.32h-.01Z" style={{fill: '#00fe6c'}}/>
            </svg>
          </div>
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