'use client'

import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { CreditsHistorySkeleton } from '@/components/ui/loading'
import { apiClient } from '@/lib/api/client'
import { useAuthStore } from '@/lib/store/auth-store'
import { CreditCard, TrendingDown, TrendingUp, Calendar, Activity } from 'lucide-react'
import { format } from 'date-fns'
import { useLocaleForDateFns } from '@/lib/hooks/use-locale'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts'
import { useTranslations } from 'next-intl'

interface CreditTransaction {
  id: string
  type: 'PURCHASE' | 'USAGE' | 'REFUND' | 'BONUS'
  amount: number
  description: string
  createdAt: string
  metadata?: {
    endpoint?: string
    apiKey?: string
    planName?: string
  }
}

interface UsageStats {
  totalCreditsUsed: number
  totalRequests: number
  averageCreditsPerRequest: number
  mostUsedEndpoint: string
  dailyUsage: Array<{
    date: string
    credits: number
    requests: number
  }>
  endpointUsage: Array<{
    endpoint: string
    credits: number
    requests: number
    percentage: number
  }>
}

const creditsApi = {
  getCreditHistory: async (): Promise<CreditTransaction[]> => {
    const response = await apiClient.get('/api/v1/auth/credits/history')
    return response.data
  },
  getUsageStats: async (): Promise<UsageStats> => {
    const response = await apiClient.get('/api/v1/auth/credits/usage-stats')
    return response.data
  }
}

export function CreditsHistory() {
  const t = useTranslations('creditsHistory')
  const locale = useLocaleForDateFns();
  const { user } = useAuthStore()
  
  const { data: creditHistory = [], isLoading: historyLoading } = useQuery({
    queryKey: ['credit-history'],
    queryFn: creditsApi.getCreditHistory
  })

  const { data: usageStats, isLoading: statsLoading } = useQuery({
    queryKey: ['usage-stats'],
    queryFn: creditsApi.getUsageStats
  })

  const creditsUsedPercentage = user ? 
    ((user.creditsTotal - user.creditsRemaining) / user.creditsTotal) * 100 : 0

  const getTransactionIcon = (type: string) => {
    switch (type) {
      case 'PURCHASE':
      case 'BONUS':
        return <TrendingUp className="h-4 w-4 text-green-600" />
      case 'USAGE':
        return <TrendingDown className="h-4 w-4 text-red-600" />
      case 'REFUND':
        return <TrendingUp className="h-4 w-4 text-blue-600" />
      default:
        return <Activity className="h-4 w-4" />
    }
  }

  const getTransactionColor = (type: string) => {
    switch (type) {
      case 'PURCHASE':
      case 'BONUS':
        return 'text-green-600'
      case 'USAGE':
        return 'text-red-600'
      case 'REFUND':
        return 'text-blue-600'
      default:
        return 'text-muted-foreground'
    }
  }

  const getTransactionLabel = (type: string) => {
    switch (type) {
      case 'PURCHASE':
        return t('purchase')
      case 'USAGE':
        return t('usage')
      case 'REFUND':
        return t('refund')
      case 'BONUS':
        return t('bonus')
      default:
        return type
    }
  }

  if (historyLoading || statsLoading) {
    return <CreditsHistorySkeleton />
  }

  return (
    <div className="space-y-6">
      {/* Resumo de Créditos */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{t('remainingCredits')}</CardTitle>
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

        {usageStats && (
          <>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">{t('totalUsed')}</CardTitle>
                <TrendingDown className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{usageStats.totalCreditsUsed}</div>
                <p className="text-xs text-muted-foreground">
                  {t('inRequests', { count: usageStats.totalRequests })}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">{t('averagePerRequest')}</CardTitle>
                <Activity className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{usageStats.averageCreditsPerRequest.toFixed(1)}</div>
                <p className="text-xs text-muted-foreground">
                  {t('creditsPerRequest')}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">{t('mostUsedEndpoint')}</CardTitle>
                <Calendar className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-lg font-bold truncate">{usageStats.mostUsedEndpoint}</div>
                <p className="text-xs text-muted-foreground">
                  {t('mainEndpoint')}
                </p>
              </CardContent>
            </Card>
          </>
        )}
      </div>

      {/* Daily Usage Chart */}
      {usageStats?.dailyUsage && usageStats.dailyUsage.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>{t('dailyCreditsUsage')}</CardTitle>
            <CardDescription>
              {t('trackCreditsConsumption')}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={usageStats.dailyUsage}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="date" 
                  tickFormatter={(value) => format(new Date(value), 'dd/MM', { locale })}
                />
                <YAxis />
                <Tooltip 
                  labelFormatter={(value) => format(new Date(value), 'dd/MM/yyyy', { locale })}
                  formatter={(value, name) => [
                    value,
                    name === 'credits' ? t('credits') : t('requests')
                  ]}
                />
                <Line 
                  type="monotone" 
                  dataKey="credits" 
                  stroke="#8884d8" 
                  strokeWidth={2}
                  name="credits"
                />
                <Line 
                  type="monotone" 
                  dataKey="requests" 
                  stroke="#82ca9d" 
                  strokeWidth={2}
                  name="requests"
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Usage by Endpoint */}
      {usageStats?.endpointUsage && usageStats.endpointUsage.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>{t('usageByEndpoint')}</CardTitle>
            <CardDescription>
              {t('creditDistributionByEndpoint')}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={usageStats.endpointUsage}>
                <CartesianGrid strokeDasharray="3 3" className="opacity-30 transition-opacity duration-300" />
                <XAxis dataKey="endpoint" className="text-xs" />
                <YAxis className="text-xs" />
                <Tooltip 
                  formatter={(value, name) => [
                    value,
                    name === 'credits' ? t('credits') : t('requests')
                  ]}
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '6px'
                  }}
                />
                <Bar 
                  dataKey="credits" 
                  fill="hsl(var(--primary))" 
                  name="credits" 
                  animationDuration={600}
                  animationEasing="ease-out"
                />
                <Bar 
                  dataKey="requests" 
                  fill="hsl(var(--secondary))" 
                  name="requests" 
                  animationDuration={600}
                  animationEasing="ease-out"
                />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Histórico de Transações */}
      <Card>
        <CardHeader>
          <CardTitle>{t('transactionHistory')}</CardTitle>
          <CardDescription>
            {t('allCreditMovements')}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {creditHistory.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <CreditCard className="mx-auto h-12 w-12 mb-4 opacity-50" />
              <p>{t('noTransactionsFound')}</p>
            </div>
          ) : (
            <div className="space-y-4">
              {creditHistory.map((transaction) => (
                <div key={transaction.id} className="flex items-center justify-between border-b pb-4">
                  <div className="flex items-center gap-3">
                    {getTransactionIcon(transaction.type)}
                    <div>
                      <p className="font-medium">{transaction.description}</p>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Badge variant="outline">
                          {getTransactionLabel(transaction.type)}
                        </Badge>
                        <span>{format(new Date(transaction.createdAt), 'dd/MM/yyyy HH:mm', { locale })}</span>
                        {transaction.metadata?.endpoint && (
                          <span>• {transaction.metadata.endpoint}</span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className={`text-right ${getTransactionColor(transaction.type)}`}>
                    <p className="font-bold">
                      {transaction.type === 'USAGE' ? '-' : '+'}{Math.abs(transaction.amount)} {t('credits')}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}