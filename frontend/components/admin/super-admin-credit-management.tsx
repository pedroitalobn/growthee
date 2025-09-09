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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
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
import { Plus, Minus, History, Search, CreditCard, TrendingUp, Users } from 'lucide-react'

interface CreditTransaction {
  id: string
  userId: string
  userEmail: string
  userName: string
  type: 'ADD' | 'REMOVE' | 'USAGE' | 'REFUND'
  amount: number
  reason: string
  createdAt: string
  createdBy: string
}

interface User {
  id: string
  email: string
  username: string
  fullName: string
  creditsRemaining: number
  creditsTotal: number
}

export function SuperAdminCreditManagement() {
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedUser, setSelectedUser] = useState<string>('')
  const [isAddCreditsDialogOpen, setIsAddCreditsDialogOpen] = useState(false)
  const [isRemoveCreditsDialogOpen, setIsRemoveCreditsDialogOpen] = useState(false)
  const [creditAmount, setCreditAmount] = useState('')
  const [creditReason, setCreditReason] = useState('')
  const [transactionType, setTransactionType] = useState<'ADD' | 'REMOVE'>('ADD')

  const queryClient = useQueryClient()

  const { data: users = [], isLoading: usersLoading } = useQuery({
    queryKey: ['admin-users'],
    queryFn: () => adminApi.getAllUsers()
  })

  const { data: creditTransactions = [], isLoading: transactionsLoading } = useQuery({
    queryKey: ['credit-transactions'],
    queryFn: () => adminApi.getCreditTransactions()
  })

  const { data: creditStats } = useQuery({
    queryKey: ['credit-stats'],
    queryFn: () => adminApi.getCreditStats()
  })

  const addCreditsMutation = useMutation({
    mutationFn: ({ userId, amount, reason }: { userId: string, amount: number, reason: string }) => 
      adminApi.addCredits(userId, amount, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
      queryClient.invalidateQueries({ queryKey: ['credit-transactions'] })
      queryClient.invalidateQueries({ queryKey: ['credit-stats'] })
      setIsAddCreditsDialogOpen(false)
      setCreditAmount('')
      setCreditReason('')
      setSelectedUser('')
      toast.success('Créditos adicionados com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao adicionar créditos')
    }
  })

  const removeCreditsMutation = useMutation({
    mutationFn: ({ userId, amount, reason }: { userId: string, amount: number, reason: string }) => 
      adminApi.removeCredits(userId, amount, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
      queryClient.invalidateQueries({ queryKey: ['credit-transactions'] })
      queryClient.invalidateQueries({ queryKey: ['credit-stats'] })
      setIsRemoveCreditsDialogOpen(false)
      setCreditAmount('')
      setCreditReason('')
      setSelectedUser('')
      toast.success('Créditos removidos com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao remover créditos')
    }
  })

  const filteredTransactions = creditTransactions.filter((transaction: CreditTransaction) => {
    const matchesSearch = transaction.userEmail.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         transaction.userName.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         transaction.reason.toLowerCase().includes(searchTerm.toLowerCase())
    return matchesSearch
  })

  const handleAddCredits = () => {
    if (!selectedUser || !creditAmount || !creditReason) {
      toast.error('Preencha todos os campos obrigatórios')
      return
    }
    addCreditsMutation.mutate({
      userId: selectedUser,
      amount: parseInt(creditAmount),
      reason: creditReason
    })
  }

  const handleRemoveCredits = () => {
    if (!selectedUser || !creditAmount || !creditReason) {
      toast.error('Preencha todos os campos obrigatórios')
      return
    }
    removeCreditsMutation.mutate({
      userId: selectedUser,
      amount: parseInt(creditAmount),
      reason: creditReason
    })
  }

  const getTransactionBadgeVariant = (type: string) => {
    switch (type) {
      case 'ADD': return 'default'
      case 'REMOVE': return 'destructive'
      case 'USAGE': return 'secondary'
      case 'REFUND': return 'outline'
      default: return 'outline'
    }
  }

  const getTransactionIcon = (type: string) => {
    switch (type) {
      case 'ADD': return '+'
      case 'REMOVE': return '-'
      case 'USAGE': return '→'
      case 'REFUND': return '↩'
      default: return '?'
    }
  }

  return (
    <div className="space-y-6">
      {/* Credit Stats Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total de Créditos</CardTitle>
            <CreditCard className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {creditStats?.totalCredits?.toLocaleString() || '0'}
            </div>
            <p className="text-xs text-muted-foreground">
              Créditos totais no sistema
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Créditos Utilizados</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {creditStats?.usedCredits?.toLocaleString() || '0'}
            </div>
            <p className="text-xs text-muted-foreground">
              Créditos consumidos hoje
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Usuários Ativos</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {creditStats?.activeUsers?.toLocaleString() || '0'}
            </div>
            <p className="text-xs text-muted-foreground">
              Usuários com créditos
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Credit Management */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CreditCard className="h-5 w-5" />
            Gerenciamento de Créditos
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div className="flex flex-1 gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Buscar transações..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-8"
                />
              </div>
            </div>
            <div className="flex gap-2">
              <Dialog open={isAddCreditsDialogOpen} onOpenChange={setIsAddCreditsDialogOpen}>
                <DialogTrigger asChild>
                  <Button>
                    <Plus className="mr-2 h-4 w-4" />
                    Adicionar Créditos
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Adicionar Créditos</DialogTitle>
                    <DialogDescription>
                      Adicione créditos para um usuário específico.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="grid gap-4 py-4">
                    <div className="grid grid-cols-4 items-center gap-4">
                      <Label htmlFor="user" className="text-right">
                        Usuário
                      </Label>
                      <Select value={selectedUser} onValueChange={setSelectedUser}>
                        <SelectTrigger className="col-span-3">
                          <SelectValue placeholder="Selecione um usuário" />
                        </SelectTrigger>
                        <SelectContent>
                          {users.map((user: User) => (
                            <SelectItem key={user.id} value={user.id}>
                              {user.email} - {user.fullName}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="grid grid-cols-4 items-center gap-4">
                      <Label htmlFor="amount" className="text-right">
                        Quantidade
                      </Label>
                      <Input
                        id="amount"
                        type="number"
                        value={creditAmount}
                        onChange={(e) => setCreditAmount(e.target.value)}
                        className="col-span-3"
                        placeholder="Ex: 1000"
                      />
                    </div>
                    <div className="grid grid-cols-4 items-center gap-4">
                      <Label htmlFor="reason" className="text-right">
                        Motivo
                      </Label>
                      <Textarea
                        id="reason"
                        value={creditReason}
                        onChange={(e) => setCreditReason(e.target.value)}
                        className="col-span-3"
                        placeholder="Descreva o motivo da adição de créditos"
                      />
                    </div>
                  </div>
                  <DialogFooter>
                    <Button 
                      onClick={handleAddCredits}
                      disabled={addCreditsMutation.isPending}
                    >
                      {addCreditsMutation.isPending ? 'Adicionando...' : 'Adicionar Créditos'}
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>

              <Dialog open={isRemoveCreditsDialogOpen} onOpenChange={setIsRemoveCreditsDialogOpen}>
                <DialogTrigger asChild>
                  <Button variant="destructive">
                    <Minus className="mr-2 h-4 w-4" />
                    Remover Créditos
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Remover Créditos</DialogTitle>
                    <DialogDescription>
                      Remova créditos de um usuário específico.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="grid gap-4 py-4">
                    <div className="grid grid-cols-4 items-center gap-4">
                      <Label htmlFor="user-remove" className="text-right">
                        Usuário
                      </Label>
                      <Select value={selectedUser} onValueChange={setSelectedUser}>
                        <SelectTrigger className="col-span-3">
                          <SelectValue placeholder="Selecione um usuário" />
                        </SelectTrigger>
                        <SelectContent>
                          {users.map((user: User) => (
                            <SelectItem key={user.id} value={user.id}>
                              {user.email} - {user.creditsRemaining} créditos
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="grid grid-cols-4 items-center gap-4">
                      <Label htmlFor="amount-remove" className="text-right">
                        Quantidade
                      </Label>
                      <Input
                        id="amount-remove"
                        type="number"
                        value={creditAmount}
                        onChange={(e) => setCreditAmount(e.target.value)}
                        className="col-span-3"
                        placeholder="Ex: 500"
                      />
                    </div>
                    <div className="grid grid-cols-4 items-center gap-4">
                      <Label htmlFor="reason-remove" className="text-right">
                        Motivo
                      </Label>
                      <Textarea
                        id="reason-remove"
                        value={creditReason}
                        onChange={(e) => setCreditReason(e.target.value)}
                        className="col-span-3"
                        placeholder="Descreva o motivo da remoção de créditos"
                      />
                    </div>
                  </div>
                  <DialogFooter>
                    <Button 
                      variant="destructive"
                      onClick={handleRemoveCredits}
                      disabled={removeCreditsMutation.isPending}
                    >
                      {removeCreditsMutation.isPending ? 'Removendo...' : 'Remover Créditos'}
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </div>
          </div>

          {/* Transactions Table */}
          <div className="rounded-md border mt-4">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Usuário</TableHead>
                  <TableHead>Quantidade</TableHead>
                  <TableHead>Motivo</TableHead>
                  <TableHead>Data</TableHead>
                  <TableHead>Executado por</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {transactionsLoading ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-8">
                      Carregando transações...
                    </TableCell>
                  </TableRow>
                ) : filteredTransactions.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-8">
                      Nenhuma transação encontrada
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredTransactions.map((transaction: CreditTransaction) => (
                    <TableRow key={transaction.id}>
                      <TableCell>
                        <Badge variant={getTransactionBadgeVariant(transaction.type)}>
                          {getTransactionIcon(transaction.type)} {transaction.type}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div>
                          <div className="font-medium">{transaction.userEmail}</div>
                          <div className="text-sm text-muted-foreground">{transaction.userName}</div>
                        </div>
                      </TableCell>
                      <TableCell className="font-mono">
                        {transaction.type === 'ADD' || transaction.type === 'REFUND' ? '+' : '-'}
                        {transaction.amount.toLocaleString()}
                      </TableCell>
                      <TableCell className="max-w-xs truncate">
                        {transaction.reason}
                      </TableCell>
                      <TableCell>
                        {new Date(transaction.createdAt).toLocaleString('pt-BR')}
                      </TableCell>
                      <TableCell>{transaction.createdBy}</TableCell>
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