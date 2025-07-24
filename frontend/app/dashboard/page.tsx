'use client'

import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { enrichmentApi } from '@/lib/api/client'
import { useAuthStore } from '@/lib/store/auth-store'
import { CreditCard, TrendingUp, Users, Building } from 'lucide-react'
import { UsageChart } from '@/components/dashboard/usage-chart'
import { RecentActivity } from '@/components/dashboard/recent-activity'

export default function DashboardPage() {
  const { user } = useAuthStore()
  
  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: enrichmentApi.getDashboardStats,
    refetchInterval: 30000 // Atualiza a cada 30s
  })

  if (isLoading) {
    return <div className="flex items-center justify-center h-screen">Carregando...</div>
  }

  const creditsUsedPercentage = user ? 
    ((user.creditsTotal - user.creditsRemaining) / user.creditsTotal) * 100 : 0

  return (
    <div className="flex-1 space-y-4 p-8 pt-6">
      <div className="flex items-center justify-between space-y-2">
        <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
      </div>
      
      {/* Cards de Estatísticas */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Créditos Restantes</CardTitle>
            <CreditCard className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{user?.creditsRemaining || 0}</div>
            <p className="text-xs text-muted-foreground">
              de {user?.creditsTotal || 0} créditos totais
            </p>
            <Progress value={creditsUsedPercentage} className="mt-2" />
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Requisições (30 dias)</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.usage.total_requests || 0}</div>
            <p className="text-xs text-muted-foreground">
              {stats?.usage.total_credits_used || 0} créditos usados
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Empresas Enriquecidas</CardTitle>
            <Building className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats?.usage.by_endpoint?.['/enrich/company']?.count || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              {stats?.usage.by_endpoint?.['/enrich/company']?.credits || 0} créditos
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pessoas Enriquecidas</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats?.usage.by_endpoint?.['/enrich/person']?.count || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              {stats?.usage.by_endpoint?.['/enrich/person']?.credits || 0} créditos
            </p>
          </CardContent>
        </Card>
      </div>
      
      {/* Gráficos e Atividade */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        <Card className="col-span-4">
          <CardHeader>
            <CardTitle>Uso de Créditos</CardTitle>
            <CardDescription>
              Histórico de consumo dos últimos 30 dias
            </CardDescription>
          </CardHeader>
          <CardContent className="pl-2">
            <UsageChart data={stats?.usage.recent_transactions || []} />
          </CardContent>
        </Card>
        
        <Card className="col-span-3">
          <CardHeader>
            <CardTitle>Atividade Recente</CardTitle>
            <CardDescription>
              Suas últimas requisições
            </CardDescription>
          </CardHeader>
          <CardContent>
            <RecentActivity transactions={stats?.usage.recent_transactions || []} />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}