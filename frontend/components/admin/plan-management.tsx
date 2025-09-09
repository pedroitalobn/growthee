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
import { adminApi, billingApi } from '@/lib/api/client'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Plus, Edit, Trash2, ToggleLeft, ToggleRight } from 'lucide-react'

interface Plan {
  id: string
  name: string
  description?: string
  price: number
  credits: number
  is_active: boolean
  features: string[]
  created_at: string
  updated_at: string
}

export function PlanManagement() {
  const [selectedPlan, setSelectedPlan] = useState<Plan | null>(null)
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false)
  const queryClient = useQueryClient()

  const { data: plans = [], isLoading } = useQuery({
    queryKey: ['billing-plans'],
    queryFn: billingApi.getPlans,
  })

  const createPlanMutation = useMutation({
    mutationFn: adminApi.createPlan,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['billing-plans'] })
      setIsCreateDialogOpen(false)
      toast.success('Plano criado com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Erro ao criar plano')
    },
  })

  const updatePlanMutation = useMutation({
    mutationFn: ({ planId, planData }: { planId: string; planData: any }) =>
      adminApi.updatePlan(planId, planData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['billing-plans'] })
      setIsEditDialogOpen(false)
      setSelectedPlan(null)
      toast.success('Plano atualizado com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Erro ao atualizar plano')
    },
  })

  const deletePlanMutation = useMutation({
    mutationFn: adminApi.deletePlan,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['billing-plans'] })
      toast.success('Plano excluído com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Erro ao excluir plano')
    },
  })

  const togglePlanMutation = useMutation({
    mutationFn: adminApi.togglePlan,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['billing-plans'] })
      toast.success('Status do plano alterado!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Erro ao alterar status')
    },
  })

  const handleCreatePlan = (formData: FormData) => {
    const features = (formData.get('features') as string)
      .split('\n')
      .filter(f => f.trim())
      .map(f => f.trim())

    const planData = {
      name: formData.get('name') as string,
      description: formData.get('description') as string,
      price: parseFloat(formData.get('price') as string),
      credits: parseInt(formData.get('credits') as string),
      features,
      is_active: true,
    }
    createPlanMutation.mutate(planData)
  }

  const handleUpdatePlan = (formData: FormData) => {
    if (!selectedPlan) return
    
    const features = (formData.get('features') as string)
      .split('\n')
      .filter(f => f.trim())
      .map(f => f.trim())

    const planData = {
      name: formData.get('name') as string,
      description: formData.get('description') as string,
      price: parseFloat(formData.get('price') as string),
      credits: parseInt(formData.get('credits') as string),
      features,
    }
    updatePlanMutation.mutate({ planId: selectedPlan.id, planData })
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('pt-BR')
  }

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'USD',
    }).format(price)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          Gerenciamento de Planos
          <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Criar Plano
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle>Criar Novo Plano</DialogTitle>
                <DialogDescription>
                  Preencha os dados para criar um novo plano de assinatura.
                </DialogDescription>
              </DialogHeader>
              <form action={handleCreatePlan}>
                <div className="grid gap-4 py-4">
                  <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="name" className="text-right">
                      Nome
                    </Label>
                    <Input id="name" name="name" className="col-span-3" required />
                  </div>
                  <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="description" className="text-right">
                      Descrição
                    </Label>
                    <Textarea id="description" name="description" className="col-span-3" />
                  </div>
                  <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="price" className="text-right">
                      Preço (USD)
                    </Label>
                    <Input
                      id="price"
                      name="price"
                      type="number"
                      step="0.01"
                      min="0"
                      className="col-span-3"
                      required
                    />
                  </div>
                  <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="credits" className="text-right">
                      Créditos
                    </Label>
                    <Input
                      id="credits"
                      name="credits"
                      type="number"
                      min="0"
                      className="col-span-3"
                      required
                    />
                  </div>
                  <div className="grid grid-cols-4 items-start gap-4">
                    <Label htmlFor="features" className="text-right pt-2">
                      Funcionalidades
                    </Label>
                    <Textarea
                      id="features"
                      name="features"
                      placeholder="Uma funcionalidade por linha"
                      className="col-span-3"
                      rows={5}
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button type="submit" disabled={createPlanMutation.isPending}>
                    {createPlanMutation.isPending ? 'Criando...' : 'Criar Plano'}
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nome</TableHead>
                <TableHead>Preço</TableHead>
                <TableHead>Créditos</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Criado em</TableHead>
                <TableHead>Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center">
                    Carregando...
                  </TableCell>
                </TableRow>
              ) : plans.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center">
                    Nenhum plano encontrado
                  </TableCell>
                </TableRow>
              ) : (
                plans.map((plan: Plan) => (
                  <TableRow key={plan.id}>
                    <TableCell>
                      <div>
                        <div className="font-medium">{plan.name}</div>
                        {plan.description && (
                          <div className="text-sm text-muted-foreground">
                            {plan.description}
                          </div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>{formatPrice(plan.price)}</TableCell>
                    <TableCell>{plan.credits.toLocaleString()}</TableCell>
                    <TableCell>
                      <div className="flex items-center space-x-2">
                        <Switch
                          checked={plan.is_active}
                          onCheckedChange={() => togglePlanMutation.mutate(plan.id)}
                        />
                        <Badge variant={plan.is_active ? 'default' : 'secondary'}>
                          {plan.is_active ? 'Ativo' : 'Inativo'}
                        </Badge>
                      </div>
                    </TableCell>
                    <TableCell>{formatDate(plan.created_at)}</TableCell>
                    <TableCell>
                      <div className="flex items-center space-x-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setSelectedPlan(plan)
                            setIsEditDialogOpen(true)
                          }}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            if (confirm('Tem certeza que deseja excluir este plano?')) {
                              deletePlanMutation.mutate(plan.id)
                            }
                          }}
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

      {/* Edit Plan Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Editar Plano</DialogTitle>
            <DialogDescription>
              Altere os dados do plano selecionado.
            </DialogDescription>
          </DialogHeader>
          {selectedPlan && (
            <form action={handleUpdatePlan}>
              <div className="grid gap-4 py-4">
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="edit-name" className="text-right">
                    Nome
                  </Label>
                  <Input
                    id="edit-name"
                    name="name"
                    defaultValue={selectedPlan.name}
                    className="col-span-3"
                    required
                  />
                </div>
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="edit-description" className="text-right">
                    Descrição
                  </Label>
                  <Textarea
                    id="edit-description"
                    name="description"
                    defaultValue={selectedPlan.description}
                    className="col-span-3"
                  />
                </div>
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="edit-price" className="text-right">
                    Preço (USD)
                  </Label>
                  <Input
                    id="edit-price"
                    name="price"
                    type="number"
                    step="0.01"
                    min="0"
                    defaultValue={selectedPlan.price}
                    className="col-span-3"
                    required
                  />
                </div>
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="edit-credits" className="text-right">
                    Créditos
                  </Label>
                  <Input
                    id="edit-credits"
                    name="credits"
                    type="number"
                    min="0"
                    defaultValue={selectedPlan.credits}
                    className="col-span-3"
                    required
                  />
                </div>
                <div className="grid grid-cols-4 items-start gap-4">
                  <Label htmlFor="edit-features" className="text-right pt-2">
                    Funcionalidades
                  </Label>
                  <Textarea
                    id="edit-features"
                    name="features"
                    placeholder="Uma funcionalidade por linha"
                    defaultValue={selectedPlan.features?.join('\n') || ''}
                    className="col-span-3"
                    rows={5}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button type="submit" disabled={updatePlanMutation.isPending}>
                  {updatePlanMutation.isPending ? 'Salvando...' : 'Salvar Alterações'}
                </Button>
              </DialogFooter>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </Card>
  )
}