import * as React from "react"
import { DataTable } from "@/components/ui/data-table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { useTranslations } from 'next-intl'

interface UserManagementTableProps {
  users?: any[]
}

export function UserManagementTable({ users = [] }: UserManagementTableProps) {
  const t = useTranslations('admin')
  const tCommon = useTranslations('common')
  
  const columns = [
    { key: 'email', header: 'Email' },
    { key: 'plan', header: t('plan') },
    { key: 'creditsRemaining', header: t('credits') },
    { key: 'isActive', header: tCommon('status') },
    { key: 'actions', header: t('actions') }
  ]

  const formattedUsers = users.map(user => ({
    ...user,
    plan: <Badge>{user.plan}</Badge>,
    isActive: <Badge variant={user.isActive ? 'default' : 'destructive'}>
      {user.isActive ? tCommon('active') : tCommon('inactive')}
    </Badge>,
    actions: (
      <div className="flex gap-2">
        <Button size="sm" variant="outline">{tCommon('edit')}</Button>
        <Button size="sm" variant="destructive">{t('suspend')}</Button>
      </div>
    )
  }))

  return <DataTable data={formattedUsers} columns={columns} />
}