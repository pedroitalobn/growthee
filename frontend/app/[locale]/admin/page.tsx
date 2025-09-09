'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { adminApi } from '@/lib/api/client'
import { 
  Users, 
  CreditCard, 
  TrendingUp, 
  Settings, 
  Plus, 
  Shield, 
  Database,
  Activity,
  AlertTriangle,
  BarChart3,
  UserCheck,
  UserX,
  Zap,
  Globe,
  Lock,
  Monitor
} from 'lucide-react'
import { SuperAdminUserManagement } from '@/components/admin/super-admin-user-management'
import { SuperAdminCreditManagement } from '@/components/admin/super-admin-credit-management'
import { SuperAdminPlanManagement } from '@/components/admin/super-admin-plan-management'
import { SuperAdminEndpointManagement } from '@/components/admin/super-admin-endpoint-management'
import { SuperAdminSystemStats } from '@/components/admin/super-admin-system-stats'
import { APIUsageDashboard } from '@/components/admin/api-usage-dashboard'

export default function SuperAdminPage() {
  const t = useTranslations('admin')
  const [activeTab, setActiveTab] = useState('overview')
  const queryClient = useQueryClient()
  
  const { data: systemStats, isLoading: statsLoading } = useQuery({
    queryKey: ['admin-system-stats'],
    queryFn: () => adminApi.getSystemStats(),
    refetchInterval: 30000
  })
  
  const { data: users } = useQuery({
    queryKey: ['admin-users'],
    queryFn: () => adminApi.getAllUsers()
  })
  
  const { data: systemEndpoints } = useQuery({
    queryKey: ['system-endpoints'],
    queryFn: () => adminApi.getSystemEndpoints()
  })

  const { data: systemFeatures } = useQuery({
    queryKey: ['system-features'],
    queryFn: () => adminApi.getSystemFeatures()
  })

  const { data: usageStats } = useQuery({
    queryKey: ['usage-stats'],
    queryFn: () => adminApi.getUsageStats(7)
  })

  const toggleMaintenanceMode = useMutation({
    mutationFn: (enabled: boolean) => adminApi.toggleMaintenanceMode(enabled),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['system-stats'] })
    }
  })

  return (
    <div className="flex-1 space-y-6 p-8 pt-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <Shield className="h-8 w-8 text-red-500" />
            Super Admin Panel
          </h2>
          <p className="text-muted-foreground">
            Controle total do sistema Growthee
          </p>
        </div>
        <div className="flex gap-2">
          <Button 
            variant={systemStats?.maintenanceMode ? "destructive" : "outline"}
            onClick={() => toggleMaintenanceMode.mutate(!systemStats?.maintenanceMode)}
            disabled={toggleMaintenanceMode.isPending}
          >
            {systemStats?.maintenanceMode ? (
              <>
                <AlertTriangle className="mr-2 h-4 w-4" />
                Desativar Manutenção
              </>
            ) : (
              <>
                <Lock className="mr-2 h-4 w-4" />
                Modo Manutenção
              </>
            )}
          </Button>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="grid w-full grid-cols-6">
          <TabsTrigger value="overview" className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4" />
            Visão Geral
          </TabsTrigger>
          <TabsTrigger value="users" className="flex items-center gap-2">
            <Users className="h-4 w-4" />
            Usuários
          </TabsTrigger>
          <TabsTrigger value="credits" className="flex items-center gap-2">
            <CreditCard className="h-4 w-4" />
            Créditos
          </TabsTrigger>
          <TabsTrigger value="plans" className="flex items-center gap-2">
            <Database className="h-4 w-4" />
            Planos
          </TabsTrigger>
          <TabsTrigger value="endpoints" className="flex items-center gap-2">
            <Globe className="h-4 w-4" />
            Endpoints
          </TabsTrigger>
          <TabsTrigger value="apis" className="flex items-center gap-2">
            <Monitor className="h-4 w-4" />
            APIs
          </TabsTrigger>
          <TabsTrigger value="system" className="flex items-center gap-2">
            <Activity className="h-4 w-4" />
            Sistema
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          {/* Estatísticas Principais */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total de Usuários</CardTitle>
                <Users className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{systemStats?.total_users || 0}</div>
                <p className="text-xs text-muted-foreground">
                  {systemStats?.active_users || 0} ativos, {systemStats?.inactive_users || 0} inativos
                </p>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Receita Estimada</CardTitle>
                <CreditCard className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  ${systemStats?.estimated_monthly_revenue?.toLocaleString() || 0}
                </div>
                <p className="text-xs text-muted-foreground">
                  Receita mensal estimada
                </p>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Créditos Consumidos</CardTitle>
                <Zap className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{systemStats?.total_credits_used || 0}</div>
                <p className="text-xs text-muted-foreground">
                  Total de créditos utilizados
                </p>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Endpoints Ativos</CardTitle>
                <Globe className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {systemEndpoints?.filter((e: any) => e.is_active).length || 0}
                </div>
                <p className="text-xs text-muted-foreground">
                  de {systemEndpoints?.length || 0} endpoints totais
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Distribuição por Roles e Planos */}
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Usuários por Role</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {systemStats?.users_by_role && Object.entries(systemStats.users_by_role).map(([role, count]) => (
                    <div key={role} className="flex justify-between items-center">
                      <span className="capitalize">{role.toLowerCase()}</span>
                      <Badge variant="outline">{count as number}</Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Usuários por Plano</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {systemStats?.users_by_plan && Object.entries(systemStats.users_by_plan).map(([plan, count]) => (
                    <div key={plan} className="flex justify-between items-center">
                      <span className="capitalize">{plan.toLowerCase()}</span>
                      <Badge variant="outline">{count as number}</Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Estatísticas de Uso */}
          {usageStats && (
            <Card>
              <CardHeader>
                <CardTitle>Estatísticas de Uso (Últimos 7 dias)</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-3">
                  <div>
                    <p className="text-sm font-medium">Total de Transações</p>
                    <p className="text-2xl font-bold">{usageStats.total_transactions}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium">Créditos Consumidos</p>
                    <p className="text-2xl font-bold">{usageStats.total_credits_consumed}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium">Top Usuário</p>
                    <p className="text-sm">{usageStats.top_users?.[0]?.name || 'N/A'}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="users">
          <SuperAdminUserManagement users={users || []} />
        </TabsContent>

        <TabsContent value="credits">
          <SuperAdminCreditManagement />
        </TabsContent>

        <TabsContent value="plans">
          <SuperAdminPlanManagement />
        </TabsContent>

        <TabsContent value="endpoints">
          <SuperAdminEndpointManagement />
        </TabsContent>

        <TabsContent value="apis">
          <APIUsageDashboard />
        </TabsContent>

        <TabsContent value="system">
          <SuperAdminSystemStats />
        </TabsContent>
      </Tabs>
    </div>
  )
}