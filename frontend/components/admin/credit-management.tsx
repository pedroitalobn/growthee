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
import { adminApi } from '@/lib/api/client'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Plus, Minus, History, Search } from 'lucide-react'

interface CreditTransaction {
  id: string
  user_id: string
  user_email: string
  amount: number
  type: 'add' | 'remove' | 'usage'
  reason?: string
  created_at: string
  admin_id?: string
}

interface User {
  id: string
  email: string
  username: string
  credits: number
}

export function CreditManagement() {
  const [selectedUserId, setSelectedUserId] = useState('')
  const [selectedUserEmail, setSelectedUserEmail] = useState('')
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false)
  const [isRemoveDialogOpen, setIsRemoveDialogOpen] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const queryClient = useQueryClient()

  const { data: users = [] } = useQuery({
    queryKey: ['admin-users'],
    queryFn: adminApi.getAllUsers,
  })

  const { data: creditHistory = [], isLoading } = useQuery({
    queryKey: ['credit-history'],
    queryFn: () => adminApi.getCreditHistory(),
  })

  const addCreditsMutation = useMutation({
    mutationFn: ({ userId, amount, reason }: { userId: string; amount: number; reason?: string }) =>
      adminApi.addCredits(userId, amount, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['credit-history'] })
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
      setIsAddDialogOpen(false)
      setSelectedUserId('')
      setSelectedUserEmail('')
      toast.success('Créditos adicionados com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Erro ao adicionar créditos')
    },
  })

  const removeCreditsMutation = useMutation({
    mutationFn: ({ userId, amount, reason }: { userId: string; amount: number; reason?: string }) =>
      adminApi.removeCredits(userId, amount, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['credit-history'] })
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
      setIsRemoveDialogOpen(false)
      setSelectedUserId('')
      setSelectedUserEmail('')
      toast.success('Créditos removidos com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Erro ao remover créditos')
    },
  })

  const handleAddCredits = (formData: FormData) => {
    const amount = parseInt(formData.get('amount') as string)
    const reason = formData.get('reason') as string
    addCreditsMutation.mutate({ userId: selectedUserId, amount, reason })
  }

  const handleRemoveCredits = (formData: FormData) => {
    const amount = parseInt(formData.get('amount') as string)
    const reason = formData.get('reason') as string
    removeCreditsMutation.mutate({ userId: selectedUserId, amount, reason })
  }

  const filteredHistory = creditHistory.filter((transaction: CreditTransaction) =>
    transaction.user_email.toLowerCase().includes(searchTerm.toLowerCase()) ||
    transaction.reason?.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('pt-BR')
  }

  const getTransactionBadge = (type: string, amount: number) => {
    switch (type) {
      case 'add':
        return <Badge className="bg-green-100 text-green-800">+{amount}</Badge>
      case 'remove':
        return <Badge className="bg-red-100 text-red-800">-{amount}</Badge>
      case 'usage':
        return <Badge variant="secondary">-{amount}</Badge>
      default:
        return <Badge variant="outline">{amount}</Badge>
    }
  }

  return (
    <div className="space-y-6">
      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Plus className="h-5 w-5 mr-2 text-green-600" />
              Adicionar Créditos
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
              <DialogTrigger asChild>
                <Button className="w-full">
                  Adicionar Créditos
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Adicionar Créditos</DialogTitle>
                  <DialogDescription>
                    Selecione um usuário e adicione créditos à sua conta.
                  </DialogDescription>
                </DialogHeader>
                <form action={handleAddCredits}>
                  <div className="grid gap-4 py-4">
                    <div className="grid grid-cols-4 items-center gap-4">
                      <Label htmlFor="user-select" className="text-right">
                        Usuário
                      </Label>
                      <select
                        id="user-select"
                        className="col-span-3 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background"
                        value={selectedUserId}
                        onChange={(e) => {
                          const userId = e.target.value
                          const user = users.find((u: User) => u.id === userId)
                          setSelectedUserId(userId)
                          setSelectedUserEmail(user?.email || '')
                        }}
                        required
                      >
                        <option value="">Selecionar usuário</option>
                        {users.map((user: User) => (
                          <option key={user.id} value={user.id}>
                            {user.email} ({user.credits} créditos)
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="grid grid-cols-4 items-center gap-4">
                      <Label htmlFor="amount" className="text-right">
                        Quantidade
                      </Label>
                      <Input
                        id="amount"
                        name="amount"
                        type="number"
                        min="1"
                        className="col-span-3"
                        required
                      />
                    </div>
                    <div className="grid grid-cols-4 items-center gap-4">
                      <Label htmlFor="reason" className="text-right">
                        Motivo
                      </Label>
                      <Textarea
                        id="reason"
                        name="reason"
                        placeholder="Motivo da adição de créditos..."
                        className="col-span-3"
                      />
                    </div>
                  </div>
                  <DialogFooter>
                    <Button type="submit" disabled={addCreditsMutation.isPending}>
                      {addCreditsMutation.isPending ? 'Adicionando...' : 'Adicionar Créditos'}
                    </Button>
                  </DialogFooter>
                </form>
              </DialogContent>
            </Dialog>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Minus className="h-5 w-5 mr-2 text-red-600" />
              Remover Créditos
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Dialog open={isRemoveDialogOpen} onOpenChange={setIsRemoveDialogOpen}>
              <DialogTrigger asChild>
                <Button variant="destructive" className="w-full">
                  Remover Créditos
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Remover Créditos</DialogTitle>
                  <DialogDescription>
                    Selecione um usuário e remova créditos de sua conta.
                  </DialogDescription>
                </DialogHeader>
                <form action={handleRemoveCredits}>
                  <div className="grid gap-4 py-4">
                    <div className="grid grid-cols-4 items-center gap-4">
                      <Label htmlFor="user-select-remove" className="text-right">
                        Usuário
                      </Label>
                      <select
                        id="user-select-remove"
                        className="col-span-3 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background"
                        value={selectedUserId}
                        onChange={(e) => {
                          const userId = e.target.value
                          const user = users.find((u: User) => u.id === userId)
                          setSelectedUserId(userId)
                          setSelectedUserEmail(user?.email || '')
                        }}
                        required
                      >
                        <option value="">Selecionar usuário</option>
                        {users.map((user: User) => (
                          <option key={user.id} value={user.id}>
                            {user.email} ({user.credits} créditos)
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="grid grid-cols-4 items-center gap-4">
                      <Label htmlFor="amount-remove" className="text-right">
                        Quantidade
                      </Label>
                      <Input
                        id="amount-remove"
                        name="amount"
                        type="number"
                        min="1"
                        className="col-span-3"
                        required
                      />
                    </div>
                    <div className="grid grid-cols-4 items-center gap-4">
                      <Label htmlFor="reason-remove" className="text-right">
                        Motivo
                      </Label>
                      <Textarea
                        id="reason-remove"
                        name="reason"
                        placeholder="Motivo da remoção de créditos..."
                        className="col-span-3"
                      />
                    </div>
                  </div>
                  <DialogFooter>
                    <Button type="submit" disabled={removeCreditsMutation.isPending}>
                      {removeCreditsMutation.isPending ? 'Removendo...' : 'Remover Créditos'}
                    </Button>
                  </DialogFooter>
                </form>
              </DialogContent>
            </Dialog>
          </CardContent>
        </Card>
      </div>

      {/* Credit History */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <History className="h-5 w-5 mr-2" />
            Histórico de Créditos
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center space-x-2 mb-4">
            <Search className="h-4 w-4" />
            <Input
              placeholder="Buscar por usuário ou motivo..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="max-w-sm"
            />
          </div>
          
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Data</TableHead>
                  <TableHead>Usuário</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Quantidade</TableHead>
                  <TableHead>Motivo</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center">
                      Carregando...
                    </TableCell>
                  </TableRow>
                ) : filteredHistory.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center">
                      Nenhuma transação encontrada
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredHistory.map((transaction: CreditTransaction) => (
                    <TableRow key={transaction.id}>
                      <TableCell>{formatDate(transaction.created_at)}</TableCell>
                      <TableCell>{transaction.user_email}</TableCell>
                      <TableCell>
                        <Badge variant={transaction.type === 'add' ? 'default' : transaction.type === 'remove' ? 'destructive' : 'secondary'}>
                          {transaction.type === 'add' ? 'Adição' : transaction.type === 'remove' ? 'Remoção' : 'Uso'}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {getTransactionBadge(transaction.type, transaction.amount)}
                      </TableCell>
                      <TableCell>
                        {transaction.reason || '-'}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}