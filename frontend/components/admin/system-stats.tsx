'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { adminApi } from '@/lib/api/client'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  Users,
  DollarSign,
  Activity,
  Server,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Settings,
  Database,
  Cpu,
  HardDrive,
  Wifi,
} from 'lucide-react'

interface SystemStats {
  total_users: number
  active_users: number
  total_revenue: number
  monthly_revenue: number
  daily_requests: number
  total_requests: number
  active_endpoints: number
  total_endpoints: number
  system_health: {
    status: 'healthy' | 'warning' | 'critical'
    uptime: string
    cpu_usage: number
    memory_usage: number
    disk_usage: number
    database_status: 'connected' | 'disconnected'
  }
  maintenance_mode: boolean
}

export function SystemStats() {
  const queryClient = useQueryClient()

  const { data: stats, isLoading } = useQuery({
    queryKey: ['admin-system-stats'],
    queryFn: adminApi.getSystemStats,
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  const toggleMaintenanceMutation = useMutation({
    mutationFn: adminApi.toggleMaintenanceMode,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-system-stats'] })
      toast.success('Modo de manutenção alterado!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Erro ao alterar modo de manutenção')
    },
  })

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'USD',
    }).format(value)
  }

  const formatNumber = (value: number) => {
    return value.toLocaleString()
  }

  const formatPercentage = (value: number) => {
    return `${value.toFixed(1)}%`
  }

  const getHealthStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'text-green-600'
      case 'warning':
        return 'text-yellow-600'
      case 'critical':
        return 'text-red-600'
      default:
        return 'text-gray-600'
    }
  }

  const getHealthStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="h-5 w-5 text-green-600" />
      case 'warning':
        return <AlertTriangle className="h-5 w-5 text-yellow-600" />
      case 'critical':
        return <XCircle className="h-5 w-5 text-red-600" />
      default:
        return <Server className="h-5 w-5 text-gray-600" />
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(8)].map((_, i) => (
            <Card key={i}>
              <CardContent className="p-6">
                <div className="animate-pulse">
                  <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                  <div className="h-8 bg-gray-200 rounded w-1/2"></div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  if (!stats) {
    return (
      <div className="text-center py-8">
        <p className="text-muted-foreground">Erro ao carregar estatísticas do sistema</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Maintenance Mode Toggle */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center">
              <Settings className="h-5 w-5 mr-2" />
              Controle do Sistema
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-sm">Modo de Manutenção</span>
              <Switch
                checked={stats.maintenance_mode}
                onCheckedChange={() => toggleMaintenanceMutation.mutate()}
              />
              <Badge variant={stats.maintenance_mode ? 'destructive' : 'default'}>
                {stats.maintenance_mode ? 'Ativo' : 'Inativo'}
              </Badge>
            </div>
          </CardTitle>
        </CardHeader>
      </Card>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <Users className="h-8 w-8 text-blue-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-muted-foreground">Total de Usuários</p>
                <p className="text-2xl font-bold">{formatNumber(stats.total_users)}</p>
                <p className="text-xs text-muted-foreground">
                  {formatNumber(stats.active_users)} ativos
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <DollarSign className="h-8 w-8 text-green-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-muted-foreground">Receita Total</p>
                <p className="text-2xl font-bold">{formatCurrency(stats.total_revenue)}</p>
                <p className="text-xs text-muted-foreground">
                  {formatCurrency(stats.monthly_revenue)} este mês
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <Activity className="h-8 w-8 text-purple-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-muted-foreground">Requisições</p>
                <p className="text-2xl font-bold">{formatNumber(stats.total_requests)}</p>
                <p className="text-xs text-muted-foreground">
                  {formatNumber(stats.daily_requests)} hoje
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <Server className="h-8 w-8 text-orange-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-muted-foreground">Endpoints</p>
                <p className="text-2xl font-bold">{formatNumber(stats.total_endpoints)}</p>
                <p className="text-xs text-muted-foreground">
                  {formatNumber(stats.active_endpoints)} ativos
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* System Health */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            {getHealthStatusIcon(stats.system_health.status)}
            <span className="ml-2">Status do Sistema</span>
            <Badge
              variant={stats.system_health.status === 'healthy' ? 'default' : 'destructive'}
              className="ml-2"
            >
              {stats.system_health.status === 'healthy' ? 'Saudável' : 
               stats.system_health.status === 'warning' ? 'Atenção' : 'Crítico'}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="flex items-center space-x-3">
              <Cpu className="h-5 w-5 text-blue-600" />
              <div>
                <p className="text-sm font-medium">CPU</p>
                <p className="text-lg font-bold">
                  {formatPercentage(stats.system_health.cpu_usage)}
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <Database className="h-5 w-5 text-green-600" />
              <div>
                <p className="text-sm font-medium">Memória</p>
                <p className="text-lg font-bold">
                  {formatPercentage(stats.system_health.memory_usage)}
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <HardDrive className="h-5 w-5 text-purple-600" />
              <div>
                <p className="text-sm font-medium">Disco</p>
                <p className="text-lg font-bold">
                  {formatPercentage(stats.system_health.disk_usage)}
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <Wifi className="h-5 w-5 text-orange-600" />
              <div>
                <p className="text-sm font-medium">Database</p>
                <p className="text-lg font-bold flex items-center">
                  {stats.system_health.database_status === 'connected' ? (
                    <CheckCircle className="h-4 w-4 text-green-600 mr-1" />
                  ) : (
                    <XCircle className="h-4 w-4 text-red-600 mr-1" />
                  )}
                  {stats.system_health.database_status === 'connected' ? 'Online' : 'Offline'}
                </p>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-6 border-t">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Uptime do Sistema</p>
                <p className="text-lg font-bold">{stats.system_health.uptime}</p>
              </div>
              <Button
                variant="outline"
                onClick={() => queryClient.invalidateQueries({ queryKey: ['admin-system-stats'] })}
              >
                Atualizar
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}