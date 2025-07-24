'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { DataTable } from '@/components/ui/data-table'
import { adminApi } from '@/lib/api/client'
import { Users, CreditCard, TrendingUp, Settings, Plus } from 'lucide-react'
import { CreateEndpointDialog } from '@/components/admin/create-endpoint-dialog'
import { UserManagementTable } from '@/components/admin/user-management-table'

export default function AdminPage() {
  const [showCreateEndpoint, setShowCreateEndpoint] = useState(false)
  const queryClient = useQueryClient()
  
  const { data: adminStats } = useQuery({
    queryKey: ['admin-stats'],
    queryFn: adminApi.getAdminStats,
    refetchInterval: 30000
  })
  
  const { data: users } = useQuery({
    queryKey: ['admin-users'],
    queryFn: adminApi.getAllUsers
  })
  
  const { data: customEndpoints } = useQuery({
    queryKey: ['custom-endpoints'],
    queryFn: adminApi.getCustomEndpoints
  })
  
  return (
    <div className="flex-1 space-y-4 p-8 pt-6">
      <div className="flex items-center justify-between space-y-2">
        <h2 className="text-3xl font-bold tracking-tight">Admin Dashboard</h2>
        <Button onClick={() => setShowCreateEndpoint(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Criar Endpoint
        </Button>
      </div>
      
      {/* Estatísticas Gerais */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total de Usuários</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{adminStats?.totalUsers || 0}</div>
            <p className="text-xs text-muted-foreground">
              +{adminStats?.newUsersThisMonth || 0} este mês
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Receita Mensal</CardTitle>
            <CreditCard className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${adminStats?.monthlyRevenue?.toLocaleString() || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              +{adminStats?.revenueGrowth || 0}% vs mês anterior
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Requisições (24h)</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{adminStats?.dailyRequests || 0}</div>
            <p className="text-xs text-muted-foreground">
              {adminStats?.dailyCreditsUsed || 0} créditos consumidos
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Endpoints Ativos</CardTitle>
            <Settings className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{customEndpoints?.length || 0}</div>
            <p className="text-xs text-muted-foreground">
              {customEndpoints?.filter((e: any) => e.isActive).length || 0} ativos
            </p>
          </CardContent>
        </Card>
      </div>
      
      {/* Gestão de Usuários */}
      <Card>
        <CardHeader>
          <CardTitle>Gestão de Usuários</CardTitle>
          <CardDescription>
            Gerencie usuários, planos e créditos
          </CardDescription>
        </CardHeader>
        <CardContent>
          <UserManagementTable users={users || []} />
        </CardContent>
      </Card>
      
      {/* Endpoints Customizados */}
      <Card>
        <CardHeader>
          <CardTitle>Endpoints Privados</CardTitle>
          <CardDescription>
            Endpoints customizados para clientes enterprise
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {customEndpoints?.map((endpoint: any) => (
              <div key={endpoint.id} className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <h4 className="font-semibold">{endpoint.name}</h4>
                  <p className="text-sm text-muted-foreground">{endpoint.path}</p>
                  <div className="flex gap-2 mt-2">
                    <Badge variant={endpoint.isActive ? "default" : "secondary"}>
                      {endpoint.isActive ? "Ativo" : "Inativo"}
                    </Badge>
                    <Badge variant="outline">
                      {endpoint.creditCost} créditos
                    </Badge>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm">
                    Editar
                  </Button>
                  <Button 
                    variant={endpoint.isActive ? "destructive" : "default"} 
                    size="sm"
                  >
                    {endpoint.isActive ? "Desativar" : "Ativar"}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
      
      <CreateEndpointDialog 
        open={showCreateEndpoint} 
        onOpenChange={setShowCreateEndpoint} 
      />
    </div>
  )
}