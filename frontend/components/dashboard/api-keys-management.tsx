'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { ApiKeysSkeleton } from '@/components/ui/loading'
import { apiClient } from '@/lib/api/client'
import { Key, Copy, Trash2, Plus, Eye, EyeOff } from 'lucide-react'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'

interface ApiKey {
  id: string
  name: string
  key: string
  lastUsed?: string
  createdAt: string
  isActive: boolean
  usageCount: number
}

const apiKeysApi = {
  getApiKeys: async (): Promise<ApiKey[]> => {
    const response = await apiClient.get('/api/v1/auth/api-keys')
    return response.data
  },
  createApiKey: async (name: string): Promise<ApiKey> => {
    const response = await apiClient.post('/api/v1/auth/api-keys', { name })
    return response.data
  },
  deleteApiKey: async (id: string): Promise<void> => {
    await apiClient.delete(`/api/v1/auth/api-keys/${id}`)
  },
  toggleApiKey: async (id: string): Promise<void> => {
    await apiClient.patch(`/api/v1/auth/api-keys/${id}/toggle`)
  }
}

export function ApiKeysManagement() {
  const t = useTranslations('apiKeys')
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [newKeyName, setNewKeyName] = useState('')
  const [visibleKeys, setVisibleKeys] = useState<Set<string>>(new Set())
  const [copiedKey, setCopiedKey] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const { data: apiKeys = [], isLoading } = useQuery({
    queryKey: ['api-keys'],
    queryFn: apiKeysApi.getApiKeys
  })

  const createMutation = useMutation({
    mutationFn: apiKeysApi.createApiKey,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] })
      setShowCreateDialog(false)
      setNewKeyName('')
    }
  })

  const deleteMutation = useMutation({
    mutationFn: apiKeysApi.deleteApiKey,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] })
    }
  })

  const toggleMutation = useMutation({
    mutationFn: apiKeysApi.toggleApiKey,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] })
    }
  })

  const copyToClipboard = async (key: string, keyId: string) => {
    try {
      await navigator.clipboard.writeText(key)
      setCopiedKey(keyId)
      setTimeout(() => setCopiedKey(null), 2000)
    } catch (err) {
      console.error('Erro ao copiar:', err)
    }
  }

  const toggleKeyVisibility = (keyId: string) => {
    const newVisible = new Set(visibleKeys)
    if (newVisible.has(keyId)) {
      newVisible.delete(keyId)
    } else {
      newVisible.add(keyId)
    }
    setVisibleKeys(newVisible)
  }

  const maskKey = (key: string) => {
    return `${key.substring(0, 8)}${'*'.repeat(24)}${key.slice(-4)}`
  }

  if (isLoading) {
    return <ApiKeysSkeleton />
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Key className="h-5 w-5" />
              API Keys
            </CardTitle>
            <CardDescription>
              {t('description')}
            </CardDescription>
          </div>
          <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                {t('newApiKey')}
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>{t('createNewApiKey')}</DialogTitle>
                <DialogDescription>
                  {t('createDescription')}
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                <div>
                  <Label htmlFor="keyName">{t('apiKeyName')}</Label>
                  <Input
                    id="keyName"
                    placeholder={t('keyNamePlaceholder')}
                    value={newKeyName}
                    onChange={(e) => setNewKeyName(e.target.value)}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button
                  onClick={() => createMutation.mutate(newKeyName)}
                  disabled={!newKeyName.trim() || createMutation.isPending}
                >
                  {createMutation.isPending ? t('creating') : t('createApiKey')}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </CardHeader>
      <CardContent>
        {apiKeys.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <Key className="mx-auto h-12 w-12 mb-4 opacity-50" />
            <p>{t('noApiKeysFound')}</p>
            <p className="text-sm">{t('createFirstApiKey')}</p>
          </div>
        ) : (
          <div className="space-y-4">
            {apiKeys.map((apiKey) => (
              <div key={apiKey.id} className="border rounded-lg p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <h4 className="font-medium">{apiKey.name}</h4>
                    <Badge variant={apiKey.isActive ? 'default' : 'secondary'}>
                      {apiKey.isActive ? t('active') : t('inactive')}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => toggleMutation.mutate(apiKey.id)}
                    >
                      {apiKey.isActive ? t('deactivate') : t('activate')}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => deleteMutation.mutate(apiKey.id)}
                      className="text-destructive hover:text-destructive"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                
                <div className="flex items-center gap-2">
                  <div className="flex-1 font-mono text-sm bg-muted p-2 rounded">
                    {visibleKeys.has(apiKey.id) ? apiKey.key : maskKey(apiKey.key)}
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => toggleKeyVisibility(apiKey.id)}
                  >
                    {visibleKeys.has(apiKey.id) ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => copyToClipboard(apiKey.key, apiKey.id)}
                  >
                    {copiedKey === apiKey.id ? (
                      <span className="text-green-600">{t('copied')}</span>
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                  </Button>
                </div>
                
                <div className="flex justify-between text-sm text-muted-foreground">
                  <span>{t('createdAt')}: {format(new Date(apiKey.createdAt), 'dd/MM/yyyy HH:mm', { locale: ptBR })}</span>
                  <span>{t('uses')}: {apiKey.usageCount}</span>
                  {apiKey.lastUsed && (
                    <span>{t('lastUsed')}: {format(new Date(apiKey.lastUsed), 'dd/MM/yyyy HH:mm', { locale: ptBR })}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}