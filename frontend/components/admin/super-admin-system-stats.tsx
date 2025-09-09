'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { adminApi } from '@/lib/api/client'
import { toast } from 'sonner'
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Database,
  Globe,
  Lock,
  Server,
  Settings,
  Shield,
  TrendingUp,
  Users,
  Zap
} from 'lucide-react'

interface UsageStats {
  total_transactions: number
  total_credits_consumed: number
  top_users: Array<{
    id: string
    name: string
    email: string
    transactions: number
  }>
  api_calls_by_endpoint: Record<string, number>
  error_rate: number
  avg_response_time: number
}

interface SystemHealth {
  database_status: 'healthy' | 'warning' | 'error'
  api_status: 'healthy' | 'warning' | 'error'
  cache_status: 'healthy' | 'warning' | 'error'
  queue_status: 'healthy' | 'warning' | 'error'
  uptime: number
  memory_usage: number
  cpu_usage: number
  disk_usage: number
}

interface SuperAdminSystemStatsProps {
  usageStats?: UsageStats
}

export function SuperAdminSystemStats({ usageStats }: SuperAdminSystemStatsProps) {
  const queryClient = useQueryClient()

  const { data: systemHealth } = useQuery<SystemHealth>({
    queryKey: ['system-health'],
    queryFn: () => adminApi.getSystemHealth(),
    refetchInterval: 10000
  })

  const { data: maintenanceMode, isLoading: maintenanceLoading } = useQuery({
    queryKey: ['maintenance-mode'],
    queryFn: () => adminApi.getMaintenanceMode()
  })

  const toggleMaintenanceMutation = useMutation({
    mutationFn: (enabled: boolean) => adminApi.toggleMaintenanceMode(enabled),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['maintenance-mode'] })
      toast.success('Modo de manutenção alterado com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao alterar modo de manutenção')
    }
  })

  const clearCacheMutation = useMutation({
    mutationFn: () => adminApi.clearSystemCache(),
    onSuccess: () => {
      toast.success('Cache limpo com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao limpar cache')
    }
  })

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'text-green-500'
      case 'warning': return 'text-yellow-500'
      case 'error': return 'text-red-500'
      default: return 'text-gray-500'
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'healthy': return 'default'
      case 'warning': return 'secondary'
      case 'error': return 'destructive'
      default: return 'outline'
    }
  }

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400)
    const hours = Math.floor((seconds % 86400) / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return `${days}d ${hours}h ${minutes}m`
  }

  const getUsageColor = (percentage: number) => {
    if (percentage < 70) return 'text-green-500'
    if (percentage < 90) return 'text-yellow-500'
    return 'text-red-500'
  }

  return (
    <div className="space-y-6">
      {/* System Health Overview */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Database</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${getStatusColor(systemHealth?.database_status || 'healthy')}`}>
              <Badge variant={getStatusBadge(systemHealth?.database_status || 'healthy')}>
                {systemHealth?.database_status || 'healthy'}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">
              Status da base de dados
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">API</CardTitle>
            <Globe className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${getStatusColor(systemHealth?.api_status || 'healthy')}`}>
              <Badge variant={getStatusBadge(systemHealth?.api_status || 'healthy')}>
                {systemHealth?.api_status || 'healthy'}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">
              Status da API
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Cache</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${getStatusColor(systemHealth?.cache_status || 'healthy')}`}>
              <Badge variant={getStatusBadge(systemHealth?.cache_status || 'healthy')}>
                {systemHealth?.cache_status || 'healthy'}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">
              Status do cache
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Queue</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${getStatusColor(systemHealth?.queue_status || 'healthy')}`}>
              <Badge variant={getStatusBadge(systemHealth?.queue_status || 'healthy')}>
                {systemHealth?.queue_status || 'healthy'}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">
              Status da fila
            </p>
          </CardContent>
        </Card>
      </div>

      {/* System Resources */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Uptime</CardTitle>
            <Server className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {systemHealth?.uptime ? formatUptime(systemHealth.uptime) : '0d 0h 0m'}
            </div>
            <p className="text-xs text-muted-foreground">
              Tempo online
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">CPU</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${getUsageColor(systemHealth?.cpu_usage || 0)}`}>
              {systemHealth?.cpu_usage?.toFixed(1) || '0.0'}%
            </div>
            <p className="text-xs text-muted-foreground">
              Uso do processador
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Memória</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${getUsageColor(systemHealth?.memory_usage || 0)}`}>
              {systemHealth?.memory_usage?.toFixed(1) || '0.0'}%
            </div>
            <p className="text-xs text-muted-foreground">
              Uso da memória
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Disco</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${getUsageColor(systemHealth?.disk_usage || 0)}`}>
              {systemHealth?.disk_usage?.toFixed(1) || '0.0'}%
            </div>
            <p className="text-xs text-muted-foreground">
              Uso do disco
            </p>
          </CardContent>
        </Card>
      </div>

      {/* System Controls */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Controles do Sistema
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div className="space-y-1">
                <div className="font-medium flex items-center gap-2">
                  <Lock className="h-4 w-4" />
                  Modo de Manutenção
                </div>
                <div className="text-sm text-muted-foreground">
                  Bloqueia acesso de usuários ao sistema
                </div>
              </div>
              <Switch
                checked={maintenanceMode?.enabled || false}
                onCheckedChange={(checked) => toggleMaintenanceMutation.mutate(checked)}
                disabled={maintenanceLoading || toggleMaintenanceMutation.isPending}
              />
            </div>
            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div className="space-y-1">
                <div className="font-medium flex items-center gap-2">
                  <Zap className="h-4 w-4" />
                  Limpar Cache
                </div>
                <div className="text-sm text-muted-foreground">
                  Remove todos os dados em cache
                </div>
              </div>
              <Button
                variant="outline"
                onClick={() => clearCacheMutation.mutate()}
                disabled={clearCacheMutation.isPending}
              >
                {clearCacheMutation.isPending ? 'Limpando...' : 'Limpar'}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Usage Statistics */}
      {usageStats && (
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5" />
                Estatísticas de Uso
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Total de Transações</span>
                  <Badge variant="outline">{usageStats.total_transactions.toLocaleString()}</Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Créditos Consumidos</span>
                  <Badge variant="outline">{usageStats.total_credits_consumed.toLocaleString()}</Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Taxa de Erro</span>
                  <Badge variant={usageStats.error_rate > 5 ? 'destructive' : 'default'}>
                    {usageStats.error_rate.toFixed(2)}%
                  </Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Tempo Médio de Resposta</span>
                  <Badge variant="outline">{usageStats.avg_response_time.toFixed(0)}ms</Badge>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Users className="h-5 w-5" />
                Top Usuários
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {usageStats.top_users?.slice(0, 5).map((user, index) => (
                  <div key={user.id} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="w-6 h-6 p-0 flex items-center justify-center">
                        {index + 1}
                      </Badge>
                      <div>
                        <div className="text-sm font-medium">{user.name}</div>
                        <div className="text-xs text-muted-foreground">{user.email}</div>
                      </div>
                    </div>
                    <Badge variant="secondary">
                      {user.transactions.toLocaleString()}
                    </Badge>
                  </div>
                )) || (
                  <div className="text-center text-muted-foreground py-4">
                    Nenhum dado disponível
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* API Endpoints Usage */}
      {usageStats?.api_calls_by_endpoint && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Globe className="h-5 w-5" />
              Uso por Endpoint
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Object.entries(usageStats.api_calls_by_endpoint)
                .sort(([,a], [,b]) => b - a)
                .slice(0, 10)
                .map(([endpoint, calls]) => (
                  <div key={endpoint} className="flex items-center justify-between">
                    <div className="text-sm font-mono">{endpoint}</div>
                    <Badge variant="outline">{calls.toLocaleString()}</Badge>
                  </div>
                ))
              }
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}