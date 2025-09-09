'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
import { useCurrentLocale } from '@/lib/hooks/use-locale'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useAuthStore } from '@/lib/store/auth-store'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { 
  CreditCard, 
  Check, 
  X, 
  Calendar, 
  DollarSign, 
  TrendingUp, 
  Zap,
  Crown,
  Star,
  ArrowRight,
  Download,
  RefreshCw
} from 'lucide-react'

interface Plan {
  id: string
  name: string
  description: string
  price: number
  currency: string
  interval: 'month' | 'year'
  credits: number
  features: string[]
  popular?: boolean
  current?: boolean
}

interface Subscription {
  id: string
  planId: string
  status: 'active' | 'canceled' | 'past_due' | 'trialing'
  currentPeriodStart: Date
  currentPeriodEnd: Date
  cancelAtPeriodEnd: boolean
  trialEnd?: Date
}

interface Invoice {
  id: string
  number: string
  status: 'paid' | 'pending' | 'failed'
  amount: number
  currency: string
  date: Date
  downloadUrl?: string
}

interface PaymentMethod {
  id: string
  type: 'card'
  brand: string
  last4: string
  expiryMonth: number
  expiryYear: number
  isDefault: boolean
}



export function BillingManagement() {
  const t = useTranslations('billing')
  const tCommon = useTranslations('common')
  const currentLocale = useCurrentLocale()
  const { user } = useAuthStore()
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null)
  
  const AVAILABLE_PLANS: Plan[] = [
    {
      id: 'starter',
      name: 'Starter',
      description: t('starterDescription'),
      price: 29,
      currency: 'USD',
      interval: 'month',
      credits: 1000,
      features: [
        t('starterCredits'),
        t('basicApi'),
        t('emailSupport'),
        t('completeDocumentation')
      ]
    },
    {
      id: 'professional',
      name: 'Professional',
      description: t('professionalDescription'),
      price: 99,
      currency: 'USD',
      interval: 'month',
      credits: 5000,
      features: [
        t('professionalCredits'),
        t('completeApi'),
        t('webhooksIntegrations'),
        t('prioritySupport'),
        t('advancedAnalytics'),
        t('dataExport')
      ],
      popular: true
    },
    {
      id: 'enterprise',
      name: 'Enterprise',
      description: t('enterpriseDescription'),
      price: 299,
      currency: 'USD',
      interval: 'month',
      credits: 20000,
      features: [
        t('enterpriseCredits'),
        t('premiumApi'),
        t('customIntegrations'),
        t('dedicatedSupport'),
        t('guaranteedSla'),
        t('customReports'),
        t('accountManager')
      ]
    }
  ]
  const [showInvoices, setShowInvoices] = useState(false)
  const [showPaymentMethods, setShowPaymentMethods] = useState(false)

  // Fetch real data from API
  const { token } = useAuthStore()
  
  const { data: currentSubscription } = useQuery({
    queryKey: ['subscription'],
    queryFn: async () => {
      const response = await fetch('/api/v1/billing/subscription', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      if (!response.ok) return null
      return response.json()
    },
    enabled: !!token
  })

  const { data: invoices = [] } = useQuery({
    queryKey: ['invoices'],
    queryFn: async () => {
      const response = await fetch('/api/v1/billing/invoices', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      if (!response.ok) return []
      return response.json()
    },
    enabled: !!token
  })

  const { data: paymentMethods = [] } = useQuery({
    queryKey: ['payment-methods'],
    queryFn: async () => {
      const response = await fetch('/api/v1/billing/payment-methods', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      if (!response.ok) return []
      return response.json()
    },
    enabled: !!token
  })

  const upgradeMutation = useMutation({
    mutationFn: async (planId: string) => {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 2000))
      return { success: true, planId }
    },
    onSuccess: () => {
      console.log(tCommon('planUpdatedSuccess'))
      setSelectedPlan(null)
    },
    onError: () => {
      console.error(tCommon('errorUpdatingPlan'))
    }
  })

  const cancelMutation = useMutation({
    mutationFn: async () => {
      await new Promise(resolve => setTimeout(resolve, 1000))
      return { success: true }
    },
    onSuccess: () => {
      console.log(tCommon('subscriptionCanceledSuccess'))
    }
  })

  const currentPlan = currentSubscription ? AVAILABLE_PLANS.find(p => p.id === currentSubscription.planId) : null
  const creditsUsed = user?.creditsTotal ? user.creditsTotal - (user.creditsRemaining || 0) : 0
  const creditsUsagePercent = currentPlan ? (creditsUsed / currentPlan.credits) * 100 : 0

  const formatDate = (date: Date) => {
    const localeMap: Record<string, string> = {
      pt: 'pt-BR',
      en: 'en-US',
      es: 'es-ES'
    }
    return new Intl.DateTimeFormat(localeMap[currentLocale] || 'en-US', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    }).format(date)
  }

  const getStatusBadge = (status: string) => {
    const variants = {
      active: 'default',
      canceled: 'destructive',
      past_due: 'destructive',
      trialing: 'secondary',
      paid: 'default',
      pending: 'secondary',
      failed: 'destructive'
    } as const

    const labels = {
      active: t('active'),
      canceled: t('canceled'),
      past_due: t('overdue'),
      trialing: t('trial'),
      paid: t('paid'),
      pending: t('pending'),
      failed: t('failed')
    } as const

    return (
      <Badge variant={variants[status as keyof typeof variants] || 'secondary'}>
        {labels[status as keyof typeof labels] || status}
      </Badge>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">{t('billingSubscriptions')}</h2>
          <p className="text-muted-foreground">
            {t('managePlanPayments')}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowPaymentMethods(!showPaymentMethods)}
          >
            <CreditCard className="h-4 w-4 mr-2" />
            {t('paymentMethods')}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowInvoices(!showInvoices)}
          >
            <Download className="h-4 w-4 mr-2" />
            {t('invoices')}
          </Button>
        </div>
      </div>

      {/* Current Plan Status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Crown className="h-5 w-5" />
            {t('currentPlan')}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-primary/10 rounded-lg">
                  <TrendingUp className="h-6 w-6 text-primary" />
                </div>
                <div>
                  <h3 className="text-xl font-semibold">{currentPlan?.name}</h3>
                  <p className="text-muted-foreground">{currentPlan?.description}</p>
                </div>
                {currentSubscription && getStatusBadge(currentSubscription.status)}
              </div>
              
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span>{t('currentPeriod')}:</span>
                  <span>{currentSubscription ? `${formatDate(currentSubscription.currentPeriodStart)} - ${formatDate(currentSubscription.currentPeriodEnd)}` : 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span>{t('nextBilling')}:</span>
                  <span>{currentSubscription ? formatDate(currentSubscription.currentPeriodEnd) : 'N/A'}</span>
                </div>
                <div className="flex justify-between font-medium">
                  <span>{t('monthlyValue')}:</span>
                  <span>${currentPlan?.price}/{t('month')}</span>
                </div>
              </div>
            </div>

            <div>
              <div className="mb-4">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-medium">{t('creditsUsage')}</span>
                  <span className="text-sm text-muted-foreground">
                    {creditsUsed.toLocaleString()} / {currentPlan?.credits.toLocaleString()}
                  </span>
                </div>
                <Progress value={creditsUsagePercent} className="h-2" />
                <p className="text-xs text-muted-foreground mt-1">
                  {t('remainingThisMonth', { percent: (100 - creditsUsagePercent).toFixed(1) })}
                </p>
              </div>

              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => cancelMutation.mutate()}
                  disabled={cancelMutation.isPending}
                >
                  {cancelMutation.isPending ? (
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <X className="h-4 w-4 mr-2" />
                  )}
                  {t('cancelPlan')}
                </Button>
                <Button size="sm">
                  <ArrowRight className="h-4 w-4 mr-2" />
                  {t('upgrade')}
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Available Plans */}
      <Card>
        <CardHeader>
          <CardTitle>{t('availablePlans')}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-3 gap-6">
            {AVAILABLE_PLANS.map((plan) => (
              <div
                key={plan.id}
                className={`relative border rounded-lg p-6 ${plan.popular ? 'border-primary shadow-lg' : 'border-border'} ${plan.id === currentPlan?.id ? 'bg-muted/50' : ''}`}
              >
                {plan.popular && (
                  <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                    <Badge className="bg-primary text-primary-foreground">
                      <Star className="h-3 w-3 mr-1" />
                      {t('mostPopular')}
                    </Badge>
                  </div>
                )}
                
                {plan.id === currentPlan?.id && (
                  <div className="absolute -top-3 right-4">
                    <Badge variant="secondary">
                      <Check className="h-3 w-3 mr-1" />
                      {t('current')}
                    </Badge>
                  </div>
                )}

                <div className="text-center mb-6">
                  <h3 className="text-xl font-semibold mb-2">{plan.name}</h3>
                  <p className="text-muted-foreground text-sm mb-4">{plan.description}</p>
                  <div className="mb-4">
                    <span className="text-3xl font-bold">${plan.price}</span>
                    <span className="text-muted-foreground">/{plan.interval === 'month' ? t('month') : t('year')}</span>
                  </div>
                  <div className="flex items-center justify-center gap-1 text-sm text-muted-foreground">
                    <Zap className="h-4 w-4" />
                    {plan.credits.toLocaleString()} {t('credits')}
                  </div>
                </div>

                <ul className="space-y-3 mb-6">
                  {plan.features.map((feature, index) => (
                    <li key={index} className="flex items-start gap-2 text-sm">
                      <Check className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>

                <Button
                  className="w-full"
                  variant={plan.id === currentPlan?.id ? 'secondary' : 'default'}
                  disabled={plan.id === currentPlan?.id || upgradeMutation.isPending}
                  onClick={() => {
                    if (plan.id !== currentPlan?.id) {
                      setSelectedPlan(plan.id)
                      upgradeMutation.mutate(plan.id)
                    }
                  }}
                >
                  {upgradeMutation.isPending && selectedPlan === plan.id ? (
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  ) : plan.id === currentPlan?.id ? (
                    t('currentPlan')
                  ) : (
                    t('selectPlan')
                  )}
                </Button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Payment Methods */}
      {showPaymentMethods && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CreditCard className="h-5 w-5" />
              Métodos de Pagamento
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {paymentMethods.map((method: PaymentMethod) => (
                <div key={method.id} className="flex items-center justify-between p-4 border rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-muted rounded">
                      <CreditCard className="h-4 w-4" />
                    </div>
                    <div>
                      <p className="font-medium capitalize">
                        {method.brand} •••• {method.last4}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {t('expiresIn')} {method.expiryMonth.toString().padStart(2, '0')}/{method.expiryYear}
                      </p>
                    </div>
                    {method.isDefault && (
                      <Badge variant="secondary">{t('default')}</Badge>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm">
                      {t('edit')}
                    </Button>
                    <Button variant="outline" size="sm">
                      {t('remove')}
                    </Button>
                  </div>
                </div>
              ))}
              <Button variant="outline" className="w-full">
                <CreditCard className="h-4 w-4 mr-2" />
                {t('addPaymentMethod')}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Invoices */}
      {showInvoices && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Download className="h-5 w-5" />
              {t('invoiceHistory')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {invoices.map((invoice: Invoice) => (
                <div key={invoice.id} className="flex items-center justify-between p-4 border rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-muted rounded">
                      <DollarSign className="h-4 w-4" />
                    </div>
                    <div>
                      <p className="font-medium">{invoice.number}</p>
                      <p className="text-sm text-muted-foreground">
                        {formatDate(invoice.date)}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <p className="font-medium">${invoice.amount}</p>
                      {getStatusBadge(invoice.status)}
                    </div>
                    {invoice.downloadUrl && (
                      <Button variant="outline" size="sm">
                        <Download className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}