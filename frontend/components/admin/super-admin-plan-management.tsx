'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
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
import { Plus, Edit, Trash2, Package, DollarSign, Users, CheckCircle, XCircle } from 'lucide-react'

interface Plan {
  id: string
  name: string
  description: string
  price: number
  credits: number
  features: string[]
  isActive: boolean
  isPopular: boolean
  maxApiCalls: number
  maxEndpoints: number
  supportLevel: string
  createdAt: string
  userCount: number
}

interface Subscription {
  id: string
  userId: string
  userEmail: string
  userName: string
  planId: string
  planName: string
  status: 'ACTIVE' | 'CANCELED' | 'EXPIRED' | 'TRIAL'
  startDate: string
  endDate: string
  autoRenew: boolean
  createdAt: string
}

export function SuperAdminPlanManagement() {
  const [isCreatePlanDialogOpen, setIsCreatePlanDialogOpen] = useState(false)
  const [isEditPlanDialogOpen, setIsEditPlanDialogOpen] = useState(false)
  const [selectedPlan, setSelectedPlan] = useState<Plan | null>(null)
  const [newPlan, setNewPlan] = useState({
    name: '',
    description: '',
    price: '',
    credits: '',
    features: '',
    maxApiCalls: '',
    maxEndpoints: '',
    supportLevel: 'BASIC'
  })

  const queryClient = useQueryClient()

  const { data: plans = [], isLoading: plansLoading } = useQuery({
    queryKey: ['admin-plans'],
    queryFn: () => adminApi.getAllPlans()
  })

  const { data: subscriptions = [], isLoading: subscriptionsLoading } = useQuery({
    queryKey: ['admin-subscriptions'],
    queryFn: () => adminApi.getAllSubscriptions()
  })

  const { data: planStats } = useQuery({
    queryKey: ['plan-stats'],
    queryFn: () => adminApi.getPlanStats()
  })

  const createPlanMutation = useMutation({
    mutationFn: (planData: any) => adminApi.createPlan(planData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-plans'] })
      queryClient.invalidateQueries({ queryKey: ['plan-stats'] })
      setIsCreatePlanDialogOpen(false)
      setNewPlan({
        name: '',
        description: '',
        price: '',
        credits: '',
        features: '',
        maxApiCalls: '',
        maxEndpoints: '',
        supportLevel: 'BASIC'
      })
      toast.success('Plano criado com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao criar plano')
    }
  })

  const updatePlanMutation = useMutation({
    mutationFn: ({ planId, data }: { planId: string, data: any }) => 
      adminApi.updatePlan(planId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-plans'] })
      queryClient.invalidateQueries({ queryKey: ['plan-stats'] })
      setIsEditPlanDialogOpen(false)
      setSelectedPlan(null)
      toast.success('Plano atualizado com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao atualizar plano')
    }
  })

  const togglePlanStatusMutation = useMutation({
    mutationFn: ({ planId, isActive }: { planId: string, isActive: boolean }) => 
      adminApi.togglePlanStatus(planId, isActive),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-plans'] })
      toast.success('Status do plano alterado com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao alterar status do plano')
    }
  })

  const deletePlanMutation = useMutation({
    mutationFn: (planId: string) => adminApi.deletePlan(planId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-plans'] })
      queryClient.invalidateQueries({ queryKey: ['plan-stats'] })
      toast.success('Plano excluído com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao excluir plano')
    }
  })

  const cancelSubscriptionMutation = useMutation({
    mutationFn: (subscriptionId: string) => adminApi.cancelSubscription(subscriptionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-subscriptions'] })
      toast.success('Assinatura cancelada com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao cancelar assinatura')
    }
  })

  const handleCreatePlan = () => {
    const planData = {
      name: newPlan.name,
      description: newPlan.description,
      price: parseFloat(newPlan.price),
      credits: parseInt(newPlan.credits),
      features: newPlan.features.split(',').map(f => f.trim()),
      maxApiCalls: parseInt(newPlan.maxApiCalls),
      maxEndpoints: parseInt(newPlan.maxEndpoints),
      supportLevel: newPlan.supportLevel
    }
    createPlanMutation.mutate(planData)
  }

  const handleUpdatePlan = () => {
    if (selectedPlan) {
      updatePlanMutation.mutate({
        planId: selectedPlan.id,
        data: {
          name: selectedPlan.name,
          description: selectedPlan.description,
          price: selectedPlan.price,
          credits: selectedPlan.credits,
          features: selectedPlan.features,
          maxApiCalls: selectedPlan.maxApiCalls,
          maxEndpoints: selectedPlan.maxEndpoints,
          supportLevel: selectedPlan.supportLevel
        }
      })
    }
  }

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case 'ACTIVE': return 'default'
      case 'TRIAL': return 'secondary'
      case 'CANCELED': return 'destructive'
      case 'EXPIRED': return 'outline'
      default: return 'outline'
    }
  }

  const getSupportLevelBadge = (level: string) => {
    switch (level) {
      case 'PREMIUM': return 'default'
      case 'STANDARD': return 'secondary'
      case 'BASIC': return 'outline'
      default: return 'outline'
    }
  }

  return (
    <div className="space-y-6">
      {/* Plan Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total de Planos</CardTitle>
            <Package className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{plans.length}</div>
            <p className="text-xs text-muted-foreground">
              Planos disponíveis
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Assinaturas Ativas</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {planStats?.activeSubscriptions || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              Usuários com planos ativos
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Receita Mensal</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              R$ {planStats?.monthlyRevenue?.toLocaleString() || '0'}
            </div>
            <p className="text-xs text-muted-foreground">
              Receita recorrente
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Taxa de Conversão</CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {planStats?.conversionRate || '0'}%
            </div>
            <p className="text-xs text-muted-foreground">
              Trial para pago
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Plans Management */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Package className="h-5 w-5" />
              Gerenciamento de Planos
            </CardTitle>
            <Dialog open={isCreatePlanDialogOpen} onOpenChange={setIsCreatePlanDialogOpen}>
              <DialogTrigger asChild>
                <Button>
                  <Plus className="mr-2 h-4 w-4" />
                  Criar Plano
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl">
                <DialogHeader>
                  <DialogTitle>Criar Novo Plano</DialogTitle>
                  <DialogDescription>
                    Configure um novo plano de assinatura para os usuários.
                  </DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="name">Nome do Plano</Label>
                      <Input
                        id="name"
                        value={newPlan.name}
                        onChange={(e) => setNewPlan({ ...newPlan, name: e.target.value })}
                        placeholder="Ex: Pro, Enterprise"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="price">Preço (R$)</Label>
                      <Input
                        id="price"
                        type="number"
                        step="0.01"
                        value={newPlan.price}
                        onChange={(e) => setNewPlan({ ...newPlan, price: e.target.value })}
                        placeholder="99.90"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="description">Descrição</Label>
                    <Textarea
                      id="description"
                      value={newPlan.description}
                      onChange={(e) => setNewPlan({ ...newPlan, description: e.target.value })}
                      placeholder="Descrição do plano e seus benefícios"
                    />
                  </div>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="credits">Créditos</Label>
                      <Input
                        id="credits"
                        type="number"
                        value={newPlan.credits}
                        onChange={(e) => setNewPlan({ ...newPlan, credits: e.target.value })}
                        placeholder="1000"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="maxApiCalls">Max API Calls</Label>
                      <Input
                        id="maxApiCalls"
                        type="number"
                        value={newPlan.maxApiCalls}
                        onChange={(e) => setNewPlan({ ...newPlan, maxApiCalls: e.target.value })}
                        placeholder="10000"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="maxEndpoints">Max Endpoints</Label>
                      <Input
                        id="maxEndpoints"
                        type="number"
                        value={newPlan.maxEndpoints}
                        onChange={(e) => setNewPlan({ ...newPlan, maxEndpoints: e.target.value })}
                        placeholder="5"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="features">Funcionalidades (separadas por vírgula)</Label>
                    <Textarea
                      id="features"
                      value={newPlan.features}
                      onChange={(e) => setNewPlan({ ...newPlan, features: e.target.value })}
                      placeholder="API Access, Priority Support, Custom Integrations"
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button 
                    onClick={handleCreatePlan}
                    disabled={createPlanMutation.isPending}
                  >
                    {createPlanMutation.isPending ? 'Criando...' : 'Criar Plano'}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Plano</TableHead>
                  <TableHead>Preço</TableHead>
                  <TableHead>Créditos</TableHead>
                  <TableHead>Usuários</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Suporte</TableHead>
                  <TableHead>Ações</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {plansLoading ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8">
                      Carregando planos...
                    </TableCell>
                  </TableRow>
                ) : plans.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8">
                      Nenhum plano encontrado
                    </TableCell>
                  </TableRow>
                ) : (
                  plans.map((plan: Plan) => (
                    <TableRow key={plan.id}>
                      <TableCell>
                        <div>
                          <div className="font-medium flex items-center gap-2">
                            {plan.name}
                            {plan.isPopular && (
                              <Badge variant="secondary">Popular</Badge>
                            )}
                          </div>
                          <div className="text-sm text-muted-foreground">
                            {plan.description}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="font-mono">
                        R$ {plan.price.toFixed(2)}
                      </TableCell>
                      <TableCell>{plan.credits.toLocaleString()}</TableCell>
                      <TableCell>{plan.userCount || 0}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Switch
                            checked={plan.isActive}
                            onCheckedChange={(checked) => 
                              togglePlanStatusMutation.mutate({ planId: plan.id, isActive: checked })
                            }
                            disabled={togglePlanStatusMutation.isPending}
                          />
                          <Badge variant={plan.isActive ? 'default' : 'secondary'}>
                            {plan.isActive ? 'Ativo' : 'Inativo'}
                          </Badge>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={getSupportLevelBadge(plan.supportLevel)}>
                          {plan.supportLevel}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setSelectedPlan(plan)
                              setIsEditPlanDialogOpen(true)
                            }}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              if (confirm('Tem certeza que deseja excluir este plano?')) {
                                deletePlanMutation.mutate(plan.id)
                              }
                            }}
                            disabled={deletePlanMutation.isPending || plan.userCount > 0}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Subscriptions Management */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            Assinaturas Ativas
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Usuário</TableHead>
                  <TableHead>Plano</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Início</TableHead>
                  <TableHead>Vencimento</TableHead>
                  <TableHead>Auto Renovar</TableHead>
                  <TableHead>Ações</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {subscriptionsLoading ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8">
                      Carregando assinaturas...
                    </TableCell>
                  </TableRow>
                ) : subscriptions.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8">
                      Nenhuma assinatura encontrada
                    </TableCell>
                  </TableRow>
                ) : (
                  subscriptions.map((subscription: Subscription) => (
                    <TableRow key={subscription.id}>
                      <TableCell>
                        <div>
                          <div className="font-medium">{subscription.userEmail}</div>
                          <div className="text-sm text-muted-foreground">{subscription.userName}</div>
                        </div>
                      </TableCell>
                      <TableCell>{subscription.planName}</TableCell>
                      <TableCell>
                        <Badge variant={getStatusBadgeVariant(subscription.status)}>
                          {subscription.status}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {new Date(subscription.startDate).toLocaleDateString('pt-BR')}
                      </TableCell>
                      <TableCell>
                        {new Date(subscription.endDate).toLocaleDateString('pt-BR')}
                      </TableCell>
                      <TableCell>
                        {subscription.autoRenew ? (
                          <CheckCircle className="h-4 w-4 text-green-500" />
                        ) : (
                          <XCircle className="h-4 w-4 text-red-500" />
                        )}
                      </TableCell>
                      <TableCell>
                        {subscription.status === 'ACTIVE' && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              if (confirm('Tem certeza que deseja cancelar esta assinatura?')) {
                                cancelSubscriptionMutation.mutate(subscription.id)
                              }
                            }}
                            disabled={cancelSubscriptionMutation.isPending}
                          >
                            Cancelar
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Edit Plan Dialog */}
      <Dialog open={isEditPlanDialogOpen} onOpenChange={setIsEditPlanDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Editar Plano</DialogTitle>
            <DialogDescription>
              Altere as configurações do plano selecionado.
            </DialogDescription>
          </DialogHeader>
          {selectedPlan && (
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="edit-name">Nome do Plano</Label>
                  <Input
                    id="edit-name"
                    value={selectedPlan.name}
                    onChange={(e) => setSelectedPlan({ ...selectedPlan, name: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit-price">Preço (R$)</Label>
                  <Input
                    id="edit-price"
                    type="number"
                    step="0.01"
                    value={selectedPlan.price}
                    onChange={(e) => setSelectedPlan({ ...selectedPlan, price: parseFloat(e.target.value) })}
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-description">Descrição</Label>
                <Textarea
                  id="edit-description"
                  value={selectedPlan.description}
                  onChange={(e) => setSelectedPlan({ ...selectedPlan, description: e.target.value })}
                />
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="edit-credits">Créditos</Label>
                  <Input
                    id="edit-credits"
                    type="number"
                    value={selectedPlan.credits}
                    onChange={(e) => setSelectedPlan({ ...selectedPlan, credits: parseInt(e.target.value) })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit-maxApiCalls">Max API Calls</Label>
                  <Input
                    id="edit-maxApiCalls"
                    type="number"
                    value={selectedPlan.maxApiCalls}
                    onChange={(e) => setSelectedPlan({ ...selectedPlan, maxApiCalls: parseInt(e.target.value) })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit-maxEndpoints">Max Endpoints</Label>
                  <Input
                    id="edit-maxEndpoints"
                    type="number"
                    value={selectedPlan.maxEndpoints}
                    onChange={(e) => setSelectedPlan({ ...selectedPlan, maxEndpoints: parseInt(e.target.value) })}
                  />
                </div>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button 
              onClick={handleUpdatePlan}
              disabled={updatePlanMutation.isPending}
            >
              {updatePlanMutation.isPending ? 'Salvando...' : 'Salvar Alterações'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}