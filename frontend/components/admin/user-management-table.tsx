import * as React from "react"
import { DataTable } from "@/components/ui/data-table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

interface UserManagementTableProps {
  users?: any[]
}

export function UserManagementTable({ users = [] }: UserManagementTableProps) {
  const columns = [
    { key: 'email', header: 'Email' },
    { key: 'plan', header: 'Plano' },
    { key: 'creditsRemaining', header: 'Créditos' },
    { key: 'isActive', header: 'Status' },
    { key: 'actions', header: 'Ações' }
  ]

  const formattedUsers = users.map(user => ({
    ...user,
    plan: <Badge>{user.plan}</Badge>,
    isActive: <Badge variant={user.isActive ? 'default' : 'destructive'}>
      {user.isActive ? 'Ativo' : 'Inativo'}
    </Badge>,
    actions: (
      <div className="flex gap-2">
        <Button size="sm" variant="outline">Editar</Button>
        <Button size="sm" variant="destructive">Suspender</Button>
      </div>
    )
  }))

  return <DataTable data={formattedUsers} columns={columns} />
}