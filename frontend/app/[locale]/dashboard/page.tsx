'use client'

import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams, useRouter, usePathname } from 'next/navigation'
import { useTranslations, useLocale } from 'next-intl'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Button } from '@/components/ui/button'
import { DashboardStatsSkeleton } from '@/components/ui/loading'
import { enrichmentApi } from '@/lib/api/client'
import { useAuthStore } from '@/lib/store/auth-store'
import { CreditCard, TrendingUp, Users, Building, User, Key, FileText, BarChart3 } from 'lucide-react'
import UsageChart from '@/components/dashboard/usage-chart'
import { RecentActivity } from '@/components/dashboard/recent-activity'
import { UserProfile } from '@/components/dashboard/user-profile'
import { ApiKeysManagement } from '@/components/dashboard/api-keys-management'
import { CreditsHistory } from '@/components/dashboard/credits-history'
import { ApiDocumentation } from '@/components/dashboard/api-documentation'
import { ApiTester } from '@/components/dashboard/api-tester'
import { BillingManagement } from '@/components/dashboard/billing-management'
import { ChatInterface } from '@/components/dashboard/chat-interface'

type DashboardTab = 'overview' | 'profile' | 'api-keys' | 'credits' | 'documentation' | 'tester' | 'billing' | 'chat'

export default function DashboardPage() {
  const { user } = useAuthStore()
  const searchParams = useSearchParams()
  const router = useRouter()
  const pathname = usePathname()
  const locale = useLocale()
  const [activeTab, setActiveTab] = useState<DashboardTab>('overview')
  const t = useTranslations('dashboard')
  const tNav = useTranslations('navigation')
  
  useEffect(() => {
    const tab = searchParams.get('tab') as DashboardTab
    if (tab && ['overview', 'profile', 'api-keys', 'credits', 'documentation', 'tester', 'billing', 'chat'].includes(tab)) {
      setActiveTab(tab)
    }
  }, [searchParams])
  
  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: enrichmentApi.getDashboardStats
  })

  if (isLoading) {
    return <DashboardStatsSkeleton />
  }

  const creditsUsedPercentage = user ? 
    ((user.creditsTotal - user.creditsRemaining) / user.creditsTotal) * 100 : 0

  const renderTabContent = () => {
    switch (activeTab) {
      case 'profile':
        return <UserProfile />
      case 'api-keys':
        return <ApiKeysManagement />
      case 'credits':
        return <CreditsHistory />
      case 'documentation':
        return <ApiDocumentation />
      case 'tester':
        return <ApiTester />
      case 'billing':
        return <BillingManagement />
      case 'chat':
        return <ChatInterface />
      default:
        return (
          <div className="space-y-4">
            {/* Cards de Estatísticas */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">{t('creditsRemaining')}</CardTitle>
                  <CreditCard className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{user?.creditsRemaining || 0}</div>
                  <p className="text-xs text-muted-foreground">
                    {t('ofTotalCredits', { total: user?.creditsTotal || 0 })}
                  </p>
                  <Progress value={creditsUsedPercentage} className="mt-2" />
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">{t('requests30Days')}</CardTitle>
                  <TrendingUp className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{stats?.usage.total_requests || 0}</div>
                  <p className="text-xs text-muted-foreground">
                    {t('creditsUsed', { count: stats?.usage.total_credits_used || 0 })}
                  </p>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">{t('companiesEnriched')}</CardTitle>
                  <Building className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {stats?.usage.by_endpoint?.['/enrich/company']?.count || 0}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {t('creditsCount', { count: stats?.usage.by_endpoint?.['/enrich/company']?.credits || 0 })}
                  </p>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">{t('peopleEnriched')}</CardTitle>
                  <Users className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {stats?.usage.by_endpoint?.['/enrich/person']?.count || 0}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {t('creditsCount', { count: stats?.usage.by_endpoint?.['/enrich/person']?.credits || 0 })}
                  </p>
                </CardContent>
              </Card>
            </div>
            
            {/* Gráficos e Atividade */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
              <Card className="col-span-4">
                <CardHeader>
                  <CardTitle>{t('creditsUsage')}</CardTitle>
                  <CardDescription>
                    {t('usageHistory30Days')}
                  </CardDescription>
                </CardHeader>
                <CardContent className="pl-2">
                  <UsageChart data={stats?.usage.recent_transactions || []} />
                </CardContent>
              </Card>
              
              <Card className="col-span-3">
                <CardHeader>
                  <CardTitle>{t('recentActivity')}</CardTitle>
                  <CardDescription>
                    {t('yourLatestRequests')}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <RecentActivity transactions={stats?.usage.recent_transactions || []} />
                </CardContent>
              </Card>
            </div>

            {/* Ações Rápidas */}
            <div className="grid gap-6 lg:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>{t('quickActions')}</CardTitle>
                  <CardDescription>{t('quickActionsDescription')}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <Button 
                    variant="outline" 
                    className="w-full justify-start" 
                    onClick={() => router.push(`/${locale}/dashboard?tab=api-keys`)}
                  >
                    <Key className="h-4 w-4 mr-2" />
                    {t('manageApiKeys')}
                  </Button>
                  <Button 
                    variant="outline" 
                    className="w-full justify-start" 
                    onClick={() => router.push(`/${locale}/dashboard?tab=credits`)}
                  >
                    <CreditCard className="h-4 w-4 mr-2" />
                    {t('viewCreditsHistory')}
                  </Button>
                  <Button 
                    variant="outline" 
                    className="w-full justify-start" 
                    onClick={() => router.push(`/${locale}/dashboard?tab=documentation`)}
                  >
                    <FileText className="h-4 w-4 mr-2" />
                    {t('apiDocumentation')}
                  </Button>
                  <Button 
                    variant="outline" 
                    className="w-full justify-start" 
                    onClick={() => router.push(`/${locale}/dashboard?tab=profile`)}
                  >
                    <User className="h-4 w-4 mr-2" />
                    {t('editProfile')}
                  </Button>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>{t('accountSummary')}</CardTitle>
                  <CardDescription>{t('accountSummaryDescription')}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex justify-between items-center py-2 border-b border-secondary-green">
                    <span className="text-sm font-medium">{t('currentPlan')}:</span>
                    <span className="text-sm">{user?.plan}</span>
                  </div>
                  <div className="flex justify-between items-center py-2 border-b border-secondary-green">
                    <span className="text-sm font-medium">Função:</span>
                    <span className="text-sm">{user?.role}</span>
                  </div>
                  <div className="flex justify-between items-center py-2 border-b border-secondary-green">
                    <span className="text-sm font-medium">Email:</span>
                    <span className="text-sm text-muted-foreground">{user?.email}</span>
                  </div>
                  <div className="flex justify-between items-center py-2">
                    <span className="text-sm font-medium">Créditos Utilizados:</span>
                    <span className="text-sm bg-secondary-green px-2 py-1 rounded">{(user?.creditsTotal || 0) - (user?.creditsRemaining || 0)}</span>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        )
    }
  }

  const getPageTitle = () => {
    switch (activeTab) {
      case 'profile': return tNav('profile')
      case 'api-keys': return tNav('apiKeys')
      case 'credits': return tNav('credits')
      case 'documentation': return tNav('documentation')
      case 'tester': return tNav('playground')
      case 'billing': return tNav('billing')
      case 'chat': return '' // Remove title for chat
      default: return tNav('dashboard')
    }
  }

  return (
    <div className="flex-1 space-y-4 p-8 pt-6 min-h-screen">
      {/* Only show title and navigation for non-chat tabs */}
      {activeTab !== 'chat' && (
        <>
          <div className="flex items-center justify-between space-y-2">
            <h2 className="text-3xl font-bold tracking-tight">{getPageTitle()}</h2>
          </div>
          
          {/* Navigation Tabs */}
          <div className="mb-6">
            <div className="flex space-x-1 rounded-lg bg-accent p-1">
              {[
                { id: 'overview', name: t('overview'), icon: BarChart3 },
                { id: 'profile', name: tNav('profile'), icon: User },
                { id: 'api-keys', name: tNav('apiKeys'), icon: Key },
                { id: 'credits', name: tNav('credits'), icon: CreditCard },
                { id: 'documentation', name: tNav('documentation'), icon: FileText },
                { id: 'tester', name: tNav('playground'), icon: TrendingUp },
                { id: 'billing', name: tNav('billing'), icon: Building },
                { id: 'chat', name: 'Chat', icon: Users }
              ].map((tab) => {
                const Icon = tab.icon
                return (
                  <button
                    key={tab.id}
                    onClick={() => {
                      setActiveTab(tab.id as DashboardTab)
                      const params = new URLSearchParams(searchParams.toString())
                      params.set('tab', tab.id)
                      router.push(`${pathname}?${params.toString()}`)
                    }}
                    className={`flex items-center space-x-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                      activeTab === tab.id
                        ? 'bg-primary text-primary-foreground'
                        : 'text-muted-foreground hover:text-foreground hover:bg-background'
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                    <span>{tab.name}</span>
                  </button>
                )
              })}
            </div>
          </div>
        </>
      )}
      
      {/* Content */}
      {renderTabContent()}
    </div>
  )
}