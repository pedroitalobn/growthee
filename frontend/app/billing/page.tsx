'use client'

import { useState, useEffect } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { billingApi, authApi } from '@/lib/api/client'
import { useAuthStore } from '@/lib/store/auth-store'
import { Check, Crown, Zap, Rocket } from 'lucide-react'
import { loadStripe } from '@stripe/stripe-js'
import { useRouter } from 'next/navigation'

const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY!)

export default function BillingPage() {
  const { user } = useAuthStore()
  const [loading, setLoading] = useState<string | null>(null)
  const router = useRouter()
  const [signupData, setSignupData] = useState<any>(null)
  
  useEffect(() => {
    // Recuperar dados do registro se existirem
    const data = sessionStorage.getItem('signupData')
    if (data) {
      setSignupData(JSON.parse(data))
    }
  }, [])

  const { data: plans } = useQuery({
    queryKey: ['billing-plans'],
    queryFn: billingApi.getPlans
  })
  
  const registerMutation = useMutation({
    mutationFn: authApi.register,
    onSuccess: (data) => {
      // Limpar dados do registro
      sessionStorage.removeItem('signupData')
      // Redirecionar para checkout
      handleUpgrade(data.planId)
    }
  })

  const checkoutMutation = useMutation({
    mutationFn: billingApi.createCheckoutSession,
    onSuccess: async (data) => {
      const stripe = await stripePromise
      if (stripe) {
        await stripe.redirectToCheckout({ sessionId: data.sessionId })
      }
    },
    onSettled: () => setLoading(null)
  })
  
  const handleUpgrade = async (planId: string) => {
    setLoading(planId)
    if (signupData) {
      // Se temos dados de registro, criar a conta primeiro
      registerMutation.mutate({
        ...signupData,
        planId
      })
    } else {
      // Se já estamos logados, ir direto para o checkout
      checkoutMutation.mutate(planId)
    }
  }
  
  const planIcons = {
    FREE: null,
    STARTER: <Zap className="h-5 w-5" />,
    PROFESSIONAL: <Crown className="h-5 w-5" />,
    ENTERPRISE: <Rocket className="h-5 w-5" />
  }
  
  return (
    <div className="container mx-auto py-8">
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold mb-4">Escolha seu Plano</h1>
        <p className="text-xl text-muted-foreground">
          Desbloqueie todo o potencial do EnrichStory
        </p>
      </div>
      
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {plans?.map((plan: any) => (
          <Card 
            key={plan.id} 
            className={`relative ${user?.plan === plan.type ? 'ring-2 ring-primary' : ''}`}
          >
            {user?.plan === plan.type && (
              <Badge className="absolute -top-2 left-1/2 transform -translate-x-1/2">
                Plano Atual
              </Badge>
            )}
            
            <CardHeader className="text-center">
              <div className="flex justify-center mb-2">
                {planIcons[plan.type as keyof typeof planIcons]}
              </div>
              <CardTitle className="text-2xl">{plan.name}</CardTitle>
              <CardDescription>
                <span className="text-3xl font-bold">
                  ${plan.priceMonthly}
                </span>
                <span className="text-muted-foreground">/mês</span>
              </CardDescription>
            </CardHeader>
            
            <CardContent>
              <div className="space-y-4">
                <div className="text-center">
                  <p className="text-lg font-semibold">
                    {plan.creditsIncluded.toLocaleString()} créditos/mês
                  </p>
                </div>
                
                <ul className="space-y-2">
                  {plan.features.map((feature: string, index: number) => (
                    <li key={index} className="flex items-center">
                      <Check className="h-4 w-4 text-green-500 mr-2" />
                      <span className="text-sm">{feature}</span>
                    </li>
                  ))}
                </ul>
                
                <Button 
                  className="w-full" 
                  variant={user?.plan === plan.type ? "outline" : "default"}
                  disabled={user?.plan === plan.type || loading === plan.id}
                  onClick={() => handleUpgrade(plan.id)}
                >
                  {loading === plan.id ? 'Processando...' : 
                   user?.plan === plan.type ? 'Plano Atual' : 
                   plan.type === 'FREE' ? 'Gratuito' : 'Fazer Upgrade'}
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}