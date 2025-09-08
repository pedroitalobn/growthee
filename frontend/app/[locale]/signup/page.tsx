'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useTranslations } from 'next-intl'

export default function SignupPage() {
  const t = useTranslations('signup');
  const [formData, setFormData] = useState({
    email: '',
    fullName: '',
    companyName: '',
    password: '',
    confirmPassword: ''
  })
  const [error, setError] = useState('')
  const router = useRouter()

  const validatePassword = (password: string) => {
    if (password.length < 8) return t('passwordMinLength')
    if (!/[A-Z]/.test(password)) return t('passwordUppercase')
    if (!/[a-z]/.test(password)) return t('passwordLowercase')
    if (!/[0-9]/.test(password)) return t('passwordNumber')
    return ''
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
    if (name === 'password') {
      const passwordError = validatePassword(value)
      setError(passwordError)
    } else if (name === 'confirmPassword') {
      if (value !== formData.password) {
        setError(t('passwordsDoNotMatch'))
      } else {
        setError('')
      }
    } else {
      setError('')
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    const passwordError = validatePassword(formData.password)
    if (passwordError) {
      setError(passwordError)
      return
    }

    if (formData.password !== formData.confirmPassword) {
      setError(t('passwordsDoNotMatch'))
      return
    }

    // Armazenar dados do registro temporariamente
    sessionStorage.setItem('signupData', JSON.stringify({
      email: formData.email,
      fullName: formData.fullName,
      companyName: formData.companyName,
      password: formData.password
    }))

    // Redirecionar para a página de planos
    router.push('/billing')
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4 bg-background">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold">{t('createAccount')}</CardTitle>
          <CardDescription>
            {t('signupDescription')}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">{t('email')}</Label>
              <Input
                id="email"
                name="email"
                type="email"
                value={formData.email}
                onChange={handleChange}
                required
                className="w-full"
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="fullName">{t('fullName')}</Label>
              <Input
                id="fullName"
                name="fullName"
                type="text"
                value={formData.fullName}
                onChange={handleChange}
                required
                className="w-full"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="companyName">{t('companyName')}</Label>
              <Input
                id="companyName"
                name="companyName"
                type="text"
                value={formData.companyName}
                onChange={handleChange}
                className="w-full"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">{t('password')}</Label>
              <Input
                id="password"
                name="password"
                type="password"
                value={formData.password}
                onChange={handleChange}
                required
                className="w-full"
              />
              <p className="text-xs text-muted-foreground">
                {t('passwordRequirements')}
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirmPassword">{t('confirmPassword')}</Label>
              <Input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                value={formData.confirmPassword}
                onChange={handleChange}
                required
                className="w-full"
              />
            </div>

            {error && (
              <div className="text-sm text-destructive">
                {error}
              </div>
            )}

            <Button type="submit" className="w-full" disabled={!!error}>
              {t('continueToPlan')}
            </Button>
          </form>
        </CardContent>
        <CardFooter className="flex justify-center">
          <p className="text-sm text-muted-foreground">
            {t('alreadyHaveAccount')}{' '}
            <Link href="/login" className="text-primary hover:underline">
              {t('login')}
            </Link>
          </p>
        </CardFooter>
      </Card>
    </div>
  )
}