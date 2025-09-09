'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Switch } from '@/components/ui/switch'
import { adminApi } from '@/lib/api/client'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Settings, BarChart3, DollarSign } from 'lucide-react'

interface Endpoint {
  id: string
  name: string
  path: string
  method: string
  is_active: boolean
  credit_cost: number
  usage_count: number
  description?: string
}

interface Feature {
  id: string
  name: string
  key: string
  is_active: boolean
  description?: string
}

export function EndpointManagement() {
  const [selectedEndpoint, setSelectedEndpoint] = useState<Endpoint | null>(null)
  const [isCostDialogOpen, setIsCostDialogOpen] = useState(false)
  const queryClient = useQueryClient()

  const { data: endpoints = [], isLoading: endpointsLoading } = useQuery({
    queryKey: ['admin-endpoints'],
    queryFn: adminApi.getEndpoints,
  })

  const { data: features = [], isLoading: featuresLoading } = useQuery({
    queryKey: ['admin-features'],
    queryFn: adminApi.getFeatures,
  })

  const { data: usageStats = {}, isLoading: statsLoading } = useQuery({
    queryKey: ['admin-usage-stats'],
    queryFn: adminApi.getUsageStats,
  })

  const toggleEndpointMutation = useMutation({
    mutationFn: adminApi.toggleEndpoint,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-endpoints'] })
      toast.success('Status do endpoint alterado!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Erro ao alterar status')
    },
  })

  const toggleFeatureMutation = useMutation({
    mutationFn: adminApi.toggleFeature,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-features'] })
      toast.success('Status da funcionalidade alterado!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Erro ao alterar status')
    },
  })

  const updateCreditCostMutation = useMutation({
    mutationFn: ({ endpointId, cost }: { endpointId: string; cost: number }) =>
      adminApi.updateEndpointCreditCost(endpointId, cost),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-endpoints'] })
      setIsCostDialogOpen(false)
      setSelectedEndpoint(null)
      toast.success('Custo de crédito atualizado!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Erro ao atualizar custo')
    },
  })

  const handleUpdateCreditCost = (formData: FormData) => {
    if (!selectedEndpoint) return
    
    const cost = parseFloat(formData.get('cost') as string)
    updateCreditCostMutation.mutate({ endpointId: selectedEndpoint.id, cost })
  }

  const formatUsage = (count: number) => {
    return count.toLocaleString()
  }

  return (
    <div className="space-y-6">
      {/* Usage Statistics */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <BarChart3 className="h-5 w-5 mr-2" />
            Estatísticas de Uso
          </CardTitle>
        </CardHeader>
        <CardContent>
          {statsLoading ? (
            <div className="text-center">Carregando estatísticas...</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold">
                  {formatUsage(usageStats.total_requests || 0)}
                </div>
                <div className="text-sm text-muted-foreground">Total de Requisições</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold">
                  {formatUsage(usageStats.daily_requests || 0)}
                </div>
                <div className="text-sm text-muted-foreground">Requisições Hoje</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold">
                  {formatUsage(usageStats.active_endpoints || 0)}
                </div>
                <div className="text-sm text-muted-foreground">Endpoints Ativos</div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Endpoints Management */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Settings className="h-5 w-5 mr-2" />
            Gerenciamento de Endpoints
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Endpoint</TableHead>
                  <TableHead>Método</TableHead>
                  <TableHead>Custo (Créditos)</TableHead>
                  <TableHead>Uso Total</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Ações</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {endpointsLoading ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center">
                      Carregando...
                    </TableCell>
                  </TableRow>
                ) : endpoints.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center">
                      Nenhum endpoint encontrado
                    </TableCell>
                  </TableRow>
                ) : (
                  endpoints.map((endpoint: Endpoint) => (
                    <TableRow key={endpoint.id}>
                      <TableCell>
                        <div>
                          <div className="font-medium">{endpoint.name}</div>
                          <div className="text-sm text-muted-foreground">
                            {endpoint.path}
                          </div>
                          {endpoint.description && (
                            <div className="text-xs text-muted-foreground">
                              {endpoint.description}
                            </div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{endpoint.method}</Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center space-x-2">
                          <span>{endpoint.credit_cost}</span>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setSelectedEndpoint(endpoint)
                              setIsCostDialogOpen(true)
                            }}
                          >
                            <DollarSign className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                      <TableCell>{formatUsage(endpoint.usage_count)}</TableCell>
                      <TableCell>
                        <div className="flex items-center space-x-2">
                          <Switch
                            checked={endpoint.is_active}
                            onCheckedChange={() => toggleEndpointMutation.mutate(endpoint.id)}
                          />
                          <Badge variant={endpoint.is_active ? 'default' : 'secondary'}>
                            {endpoint.is_active ? 'Ativo' : 'Inativo'}
                          </Badge>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setSelectedEndpoint(endpoint)
                            setIsCostDialogOpen(true)
                          }}
                        >
                          Editar Custo
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Features Management */}
      <Card>
        <CardHeader>
          <CardTitle>Gerenciamento de Funcionalidades</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Funcionalidade</TableHead>
                  <TableHead>Chave</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Ações</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {featuresLoading ? (
                  <TableRow>
                    <TableCell colSpan={4} className="text-center">
                      Carregando...
                    </TableCell>
                  </TableRow>
                ) : features.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4} className="text-center">
                      Nenhuma funcionalidade encontrada
                    </TableCell>
                  </TableRow>
                ) : (
                  features.map((feature: Feature) => (
                    <TableRow key={feature.id}>
                      <TableCell>
                        <div>
                          <div className="font-medium">{feature.name}</div>
                          {feature.description && (
                            <div className="text-sm text-muted-foreground">
                              {feature.description}
                            </div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <code className="text-sm bg-muted px-2 py-1 rounded">
                          {feature.key}
                        </code>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center space-x-2">
                          <Switch
                            checked={feature.is_active}
                            onCheckedChange={() => toggleFeatureMutation.mutate(feature.id)}
                          />
                          <Badge variant={feature.is_active ? 'default' : 'secondary'}>
                            {feature.is_active ? 'Ativo' : 'Inativo'}
                          </Badge>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => toggleFeatureMutation.mutate(feature.id)}
                        >
                          {feature.is_active ? 'Desativar' : 'Ativar'}
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Update Credit Cost Dialog */}
      <Dialog open={isCostDialogOpen} onOpenChange={setIsCostDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Atualizar Custo de Crédito</DialogTitle>
            <DialogDescription>
              Altere o custo em créditos para o endpoint selecionado.
            </DialogDescription>
          </DialogHeader>
          {selectedEndpoint && (
            <form action={handleUpdateCreditCost}>
              <div className="grid gap-4 py-4">
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label className="text-right">Endpoint:</Label>
                  <div className="col-span-3">
                    <div className="font-medium">{selectedEndpoint.name}</div>
                    <div className="text-sm text-muted-foreground">
                      {selectedEndpoint.path}
                    </div>
                  </div>
                </div>
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="cost" className="text-right">
                    Custo (Créditos)
                  </Label>
                  <Input
                    id="cost"
                    name="cost"
                    type="number"
                    min="0"
                    step="0.1"
                    defaultValue={selectedEndpoint.credit_cost}
                    className="col-span-3"
                    required
                  />
                </div>
              </div>
              <DialogFooter>
                <Button type="submit" disabled={updateCreditCostMutation.isPending}>
                  {updateCreditCostMutation.isPending ? 'Salvando...' : 'Salvar'}
                </Button>
              </DialogFooter>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}