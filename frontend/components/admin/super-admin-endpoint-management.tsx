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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { adminApi } from '@/lib/api/client'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Plus, Edit, Trash2, Globe, Activity, AlertTriangle, CheckCircle, XCircle, BarChart3 } from 'lucide-react'

interface Endpoint {
  id: string
  name: string
  path: string
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'
  description: string
  isActive: boolean
  requiresAuth: boolean
  rateLimit: number
  rateLimitWindow: number
  allowedPlans: string[]
  category: string
  version: string
  createdAt: string
  totalCalls: number
  errorRate: number
  avgResponseTime: number
}

interface EndpointStats {
  totalEndpoints: number
  activeEndpoints: number
  totalCalls: number
  errorRate: number
  avgResponseTime: number
  topEndpoints: Array<{
    id: string
    name: string
    calls: number
    errorRate: number
  }>
}

export function SuperAdminEndpointManagement() {
  const [isCreateEndpointDialogOpen, setIsCreateEndpointDialogOpen] = useState(false)
  const [isEditEndpointDialogOpen, setIsEditEndpointDialogOpen] = useState(false)
  const [selectedEndpoint, setSelectedEndpoint] = useState<Endpoint | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [filterCategory, setFilterCategory] = useState('all')
  const [filterStatus, setFilterStatus] = useState('all')
  const [newEndpoint, setNewEndpoint] = useState({
    name: '',
    path: '',
    method: 'GET' as const,
    description: '',
    requiresAuth: true,
    rateLimit: '100',
    rateLimitWindow: '60',
    allowedPlans: [] as string[],
    category: 'API',
    version: 'v1'
  })

  const queryClient = useQueryClient()

  const { data: endpoints = [], isLoading: endpointsLoading } = useQuery({
    queryKey: ['admin-endpoints'],
    queryFn: () => adminApi.getAllEndpoints()
  })

  const { data: endpointStats } = useQuery<EndpointStats>({
    queryKey: ['admin-endpoint-stats'],
    queryFn: () => adminApi.getEndpointStats()
  })

  const { data: plans = [] } = useQuery({
    queryKey: ['admin-plans'],
    queryFn: () => adminApi.getAllPlans()
  })

  const createEndpointMutation = useMutation({
    mutationFn: (endpointData: any) => adminApi.createEndpoint(endpointData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-endpoints'] })
      queryClient.invalidateQueries({ queryKey: ['admin-endpoint-stats'] })
      setIsCreateEndpointDialogOpen(false)
      setNewEndpoint({
        name: '',
        path: '',
        method: 'GET',
        description: '',
        requiresAuth: true,
        rateLimit: '100',
        rateLimitWindow: '60',
        allowedPlans: [],
        category: 'API',
        version: 'v1'
      })
      toast.success('Endpoint criado com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao criar endpoint')
    }
  })

  const updateEndpointMutation = useMutation({
    mutationFn: ({ endpointId, data }: { endpointId: string, data: any }) => 
      adminApi.updateEndpoint(endpointId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-endpoints'] })
      queryClient.invalidateQueries({ queryKey: ['admin-endpoint-stats'] })
      setIsEditEndpointDialogOpen(false)
      setSelectedEndpoint(null)
      toast.success('Endpoint atualizado com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao atualizar endpoint')
    }
  })

  const toggleEndpointStatusMutation = useMutation({
    mutationFn: ({ endpointId, isActive }: { endpointId: string, isActive: boolean }) => 
      adminApi.toggleEndpointStatus(endpointId, isActive),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-endpoints'] })
      queryClient.invalidateQueries({ queryKey: ['admin-endpoint-stats'] })
      toast.success('Status do endpoint alterado com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao alterar status do endpoint')
    }
  })

  const deleteEndpointMutation = useMutation({
    mutationFn: (endpointId: string) => adminApi.deleteEndpoint(endpointId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-endpoints'] })
      queryClient.invalidateQueries({ queryKey: ['admin-endpoint-stats'] })
      toast.success('Endpoint excluído com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao excluir endpoint')
    }
  })

  const handleCreateEndpoint = () => {
    const endpointData = {
      name: newEndpoint.name,
      path: newEndpoint.path,
      method: newEndpoint.method,
      description: newEndpoint.description,
      requiresAuth: newEndpoint.requiresAuth,
      rateLimit: parseInt(newEndpoint.rateLimit),
      rateLimitWindow: parseInt(newEndpoint.rateLimitWindow),
      allowedPlans: newEndpoint.allowedPlans,
      category: newEndpoint.category,
      version: newEndpoint.version
    }
    createEndpointMutation.mutate(endpointData)
  }

  const handleUpdateEndpoint = () => {
    if (selectedEndpoint) {
      updateEndpointMutation.mutate({
        endpointId: selectedEndpoint.id,
        data: {
          name: selectedEndpoint.name,
          path: selectedEndpoint.path,
          method: selectedEndpoint.method,
          description: selectedEndpoint.description,
          requiresAuth: selectedEndpoint.requiresAuth,
          rateLimit: selectedEndpoint.rateLimit,
          rateLimitWindow: selectedEndpoint.rateLimitWindow,
          allowedPlans: selectedEndpoint.allowedPlans,
          category: selectedEndpoint.category,
          version: selectedEndpoint.version
        }
      })
    }
  }

  const getMethodBadgeVariant = (method: string) => {
    switch (method) {
      case 'GET': return 'default'
      case 'POST': return 'secondary'
      case 'PUT': return 'outline'
      case 'DELETE': return 'destructive'
      case 'PATCH': return 'secondary'
      default: return 'outline'
    }
  }

  const getStatusColor = (errorRate: number) => {
    if (errorRate < 1) return 'text-green-500'
    if (errorRate < 5) return 'text-yellow-500'
    return 'text-red-500'
  }

  const filteredEndpoints = endpoints.filter((endpoint: Endpoint) => {
    const matchesSearch = endpoint.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         endpoint.path.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesCategory = filterCategory === 'all' || endpoint.category === filterCategory
    const matchesStatus = filterStatus === 'all' || 
                         (filterStatus === 'active' && endpoint.isActive) ||
                         (filterStatus === 'inactive' && !endpoint.isActive)
    
    return matchesSearch && matchesCategory && matchesStatus
  })

  const categories = [...new Set(endpoints.map((e: Endpoint) => e.category))]

  return (
    <div className="space-y-6">
      {/* Endpoint Stats */}
      <div className="grid gap-4 md:grid-cols-5">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Endpoints</CardTitle>
            <Globe className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{endpointStats?.totalEndpoints || 0}</div>
            <p className="text-xs text-muted-foreground">
              Endpoints registrados
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Endpoints Ativos</CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{endpointStats?.activeEndpoints || 0}</div>
            <p className="text-xs text-muted-foreground">
              Disponíveis para uso
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total de Chamadas</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {endpointStats?.totalCalls?.toLocaleString() || '0'}
            </div>
            <p className="text-xs text-muted-foreground">
              Chamadas realizadas
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Taxa de Erro</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${getStatusColor(endpointStats?.errorRate || 0)}`}>
              {endpointStats?.errorRate?.toFixed(2) || '0.00'}%
            </div>
            <p className="text-xs text-muted-foreground">
              Média de erros
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Tempo Resposta</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {endpointStats?.avgResponseTime?.toFixed(0) || '0'}ms
            </div>
            <p className="text-xs text-muted-foreground">
              Tempo médio
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Endpoints Management */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Globe className="h-5 w-5" />
              Gerenciamento de Endpoints
            </CardTitle>
            <Dialog open={isCreateEndpointDialogOpen} onOpenChange={setIsCreateEndpointDialogOpen}>
              <DialogTrigger asChild>
                <Button>
                  <Plus className="mr-2 h-4 w-4" />
                  Criar Endpoint
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-3xl">
                <DialogHeader>
                  <DialogTitle>Criar Novo Endpoint</DialogTitle>
                  <DialogDescription>
                    Configure um novo endpoint da API para disponibilizar aos usuários.
                  </DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="name">Nome do Endpoint</Label>
                      <Input
                        id="name"
                        value={newEndpoint.name}
                        onChange={(e) => setNewEndpoint({ ...newEndpoint, name: e.target.value })}
                        placeholder="Ex: Get User Profile"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="path">Caminho</Label>
                      <Input
                        id="path"
                        value={newEndpoint.path}
                        onChange={(e) => setNewEndpoint({ ...newEndpoint, path: e.target.value })}
                        placeholder="/api/v1/users/{id}"
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="method">Método HTTP</Label>
                      <Select
                        value={newEndpoint.method}
                        onValueChange={(value: any) => setNewEndpoint({ ...newEndpoint, method: value })}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="GET">GET</SelectItem>
                          <SelectItem value="POST">POST</SelectItem>
                          <SelectItem value="PUT">PUT</SelectItem>
                          <SelectItem value="DELETE">DELETE</SelectItem>
                          <SelectItem value="PATCH">PATCH</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="category">Categoria</Label>
                      <Input
                        id="category"
                        value={newEndpoint.category}
                        onChange={(e) => setNewEndpoint({ ...newEndpoint, category: e.target.value })}
                        placeholder="API, Webhook, etc."
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="version">Versão</Label>
                      <Input
                        id="version"
                        value={newEndpoint.version}
                        onChange={(e) => setNewEndpoint({ ...newEndpoint, version: e.target.value })}
                        placeholder="v1, v2, etc."
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="description">Descrição</Label>
                    <Textarea
                      id="description"
                      value={newEndpoint.description}
                      onChange={(e) => setNewEndpoint({ ...newEndpoint, description: e.target.value })}
                      placeholder="Descrição do que este endpoint faz"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="rateLimit">Rate Limit (req/min)</Label>
                      <Input
                        id="rateLimit"
                        type="number"
                        value={newEndpoint.rateLimit}
                        onChange={(e) => setNewEndpoint({ ...newEndpoint, rateLimit: e.target.value })}
                        placeholder="100"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="rateLimitWindow">Janela (segundos)</Label>
                      <Input
                        id="rateLimitWindow"
                        type="number"
                        value={newEndpoint.rateLimitWindow}
                        onChange={(e) => setNewEndpoint({ ...newEndpoint, rateLimitWindow: e.target.value })}
                        placeholder="60"
                      />
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="requiresAuth"
                      checked={newEndpoint.requiresAuth}
                      onChange={(e) => setNewEndpoint({ ...newEndpoint, requiresAuth: e.target.checked })}
                      className="rounded"
                    />
                    <Label htmlFor="requiresAuth">Requer Autenticação</Label>
                  </div>
                </div>
                <DialogFooter>
                  <Button 
                    onClick={handleCreateEndpoint}
                    disabled={createEndpointMutation.isPending}
                  >
                    {createEndpointMutation.isPending ? 'Criando...' : 'Criar Endpoint'}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </CardHeader>
        <CardContent>
          {/* Filters */}
          <div className="flex gap-4 mb-6">
            <div className="flex-1">
              <Input
                placeholder="Buscar endpoints..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <Select value={filterCategory} onValueChange={setFilterCategory}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Categoria" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas Categorias</SelectItem>
                {categories.map((category) => (
                  <SelectItem key={category} value={category}>{category}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={filterStatus} onValueChange={setFilterStatus}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos Status</SelectItem>
                <SelectItem value="active">Ativos</SelectItem>
                <SelectItem value="inactive">Inativos</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Endpoint</TableHead>
                  <TableHead>Método</TableHead>
                  <TableHead>Categoria</TableHead>
                  <TableHead>Rate Limit</TableHead>
                  <TableHead>Chamadas</TableHead>
                  <TableHead>Taxa Erro</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Ações</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {endpointsLoading ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center py-8">
                      Carregando endpoints...
                    </TableCell>
                  </TableRow>
                ) : filteredEndpoints.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center py-8">
                      Nenhum endpoint encontrado
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredEndpoints.map((endpoint: Endpoint) => (
                    <TableRow key={endpoint.id}>
                      <TableCell>
                        <div>
                          <div className="font-medium">{endpoint.name}</div>
                          <div className="text-sm text-muted-foreground font-mono">
                            {endpoint.path}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={getMethodBadgeVariant(endpoint.method)}>
                          {endpoint.method}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{endpoint.category}</Badge>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm">
                          {endpoint.rateLimit}/{endpoint.rateLimitWindow}s
                        </div>
                      </TableCell>
                      <TableCell>{endpoint.totalCalls?.toLocaleString() || '0'}</TableCell>
                      <TableCell>
                        <span className={getStatusColor(endpoint.errorRate || 0)}>
                          {endpoint.errorRate?.toFixed(2) || '0.00'}%
                        </span>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Switch
                            checked={endpoint.isActive}
                            onCheckedChange={(checked) => 
                              toggleEndpointStatusMutation.mutate({ endpointId: endpoint.id, isActive: checked })
                            }
                            disabled={toggleEndpointStatusMutation.isPending}
                          />
                          <Badge variant={endpoint.isActive ? 'default' : 'secondary'}>
                            {endpoint.isActive ? 'Ativo' : 'Inativo'}
                          </Badge>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setSelectedEndpoint(endpoint)
                              setIsEditEndpointDialogOpen(true)
                            }}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              if (confirm('Tem certeza que deseja excluir este endpoint?')) {
                                deleteEndpointMutation.mutate(endpoint.id)
                              }
                            }}
                            disabled={deleteEndpointMutation.isPending}
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

      {/* Edit Endpoint Dialog */}
      <Dialog open={isEditEndpointDialogOpen} onOpenChange={setIsEditEndpointDialogOpen}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>Editar Endpoint</DialogTitle>
            <DialogDescription>
              Altere as configurações do endpoint selecionado.
            </DialogDescription>
          </DialogHeader>
          {selectedEndpoint && (
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="edit-name">Nome do Endpoint</Label>
                  <Input
                    id="edit-name"
                    value={selectedEndpoint.name}
                    onChange={(e) => setSelectedEndpoint({ ...selectedEndpoint, name: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit-path">Caminho</Label>
                  <Input
                    id="edit-path"
                    value={selectedEndpoint.path}
                    onChange={(e) => setSelectedEndpoint({ ...selectedEndpoint, path: e.target.value })}
                  />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="edit-method">Método HTTP</Label>
                  <Select
                    value={selectedEndpoint.method}
                    onValueChange={(value: any) => setSelectedEndpoint({ ...selectedEndpoint, method: value })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="GET">GET</SelectItem>
                      <SelectItem value="POST">POST</SelectItem>
                      <SelectItem value="PUT">PUT</SelectItem>
                      <SelectItem value="DELETE">DELETE</SelectItem>
                      <SelectItem value="PATCH">PATCH</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit-category">Categoria</Label>
                  <Input
                    id="edit-category"
                    value={selectedEndpoint.category}
                    onChange={(e) => setSelectedEndpoint({ ...selectedEndpoint, category: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit-version">Versão</Label>
                  <Input
                    id="edit-version"
                    value={selectedEndpoint.version}
                    onChange={(e) => setSelectedEndpoint({ ...selectedEndpoint, version: e.target.value })}
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-description">Descrição</Label>
                <Textarea
                  id="edit-description"
                  value={selectedEndpoint.description}
                  onChange={(e) => setSelectedEndpoint({ ...selectedEndpoint, description: e.target.value })}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="edit-rateLimit">Rate Limit (req/min)</Label>
                  <Input
                    id="edit-rateLimit"
                    type="number"
                    value={selectedEndpoint.rateLimit}
                    onChange={(e) => setSelectedEndpoint({ ...selectedEndpoint, rateLimit: parseInt(e.target.value) })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit-rateLimitWindow">Janela (segundos)</Label>
                  <Input
                    id="edit-rateLimitWindow"
                    type="number"
                    value={selectedEndpoint.rateLimitWindow}
                    onChange={(e) => setSelectedEndpoint({ ...selectedEndpoint, rateLimitWindow: parseInt(e.target.value) })}
                  />
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="edit-requiresAuth"
                  checked={selectedEndpoint.requiresAuth}
                  onChange={(e) => setSelectedEndpoint({ ...selectedEndpoint, requiresAuth: e.target.checked })}
                  className="rounded"
                />
                <Label htmlFor="edit-requiresAuth">Requer Autenticação</Label>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button 
              onClick={handleUpdateEndpoint}
              disabled={updateEndpointMutation.isPending}
            >
              {updateEndpointMutation.isPending ? 'Salvando...' : 'Salvar Alterações'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}