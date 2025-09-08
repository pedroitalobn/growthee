'use client'

import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { UserProfileSkeleton } from '@/components/ui/loading'
import { apiClient } from '@/lib/api/client'
import { useAuthStore } from '@/lib/store/auth-store'
import { 
  User, 
  Mail, 
  Calendar, 
  Shield, 
  Edit, 
  Save, 
  X,
  CreditCard,
  Key,
  Settings,
  Bell,
  Lock
} from 'lucide-react'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { useTranslations } from 'next-intl'

interface UserProfile {
  id: string
  email: string
  fullName: string
  companyName?: string
  role: 'USER' | 'ADMIN' | 'SUPER_ADMIN'
  plan: 'FREE' | 'STARTER' | 'PROFESSIONAL' | 'ENTERPRISE'
  creditsRemaining: number
  creditsTotal: number
  status?: 'ACTIVE' | 'INACTIVE' | 'SUSPENDED'
  createdAt?: string
  lastLogin?: string
  preferences?: {
    notifications: boolean
    newsletter: boolean
    theme: 'light' | 'dark' | 'system'
  }
  stats?: {
    totalRequests: number
    totalCreditsUsed: number
    apiKeysCount: number
  }
}

interface UpdateProfileData {
  fullName: string
  companyName?: string
  preferences?: {
    notifications: boolean
    newsletter: boolean
    theme: 'light' | 'dark' | 'system'
  }
}

const profileApi = {
  updateProfile: async (data: UpdateProfileData): Promise<UserProfile> => {
    const response = await apiClient.put('/api/v1/auth/profile', data)
    return response.data
  },
  changePassword: async (data: { currentPassword: string, newPassword: string }): Promise<void> => {
    await apiClient.post('/api/v1/auth/change-password', data)
  },
  deleteAccount: async (): Promise<void> => {
    await apiClient.delete('/api/v1/auth/account')
  }
}

const toast = {
  success: (message: string) => console.log('Success:', message),
  error: (message: string) => console.error('Error:', message)
}

export function UserProfile() {
  const { user, logout } = useAuthStore()
  const queryClient = useQueryClient()
  const t = useTranslations('profile')
  const tCommon = useTranslations('common')
  const [isEditing, setIsEditing] = useState(false)
  const [isChangingPassword, setIsChangingPassword] = useState(false)
  const [formData, setFormData] = useState({
    fullName: user?.fullName || '',
    companyName: user?.companyName || '',
    notifications: false,
    newsletter: false,
    theme: 'system' as 'light' | 'dark' | 'system'
  })
  const [passwordData, setPasswordData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  })

  const updateProfileMutation = useMutation({
    mutationFn: profileApi.updateProfile,
    onSuccess: () => {
      setIsEditing(false)
      toast.success(t('profileUpdatedSuccess'))
      queryClient.invalidateQueries({ queryKey: ['user-profile'] })
    },
    onError: () => {
      toast.error(t('profileUpdateError'))
    }
  })

  const changePasswordMutation = useMutation({
    mutationFn: profileApi.changePassword,
    onSuccess: () => {
      setIsChangingPassword(false)
      setPasswordData({ currentPassword: '', newPassword: '', confirmPassword: '' })
      toast.success(t('passwordChangedSuccess'))
    },
    onError: () => {
      toast.error(t('passwordChangeError'))
    }
  })

  const deleteAccountMutation = useMutation({
    mutationFn: profileApi.deleteAccount,
    onSuccess: () => {
      logout()
      toast.success(t('accountDeletedSuccess'))
    },
    onError: () => {
      toast.error(t('accountDeleteError'))
    }
  })

  const handleSaveProfile = () => {
    updateProfileMutation.mutate({
      fullName: formData.fullName,
      companyName: formData.companyName,
      preferences: {
        notifications: formData.notifications,
        newsletter: formData.newsletter,
        theme: formData.theme
      }
    })
  }

  const handleChangePassword = () => {
    if (passwordData.newPassword !== passwordData.confirmPassword) {
      toast.error(t('passwordsDoNotMatch'))
      return
    }
    if (passwordData.newPassword.length < 8) {
      toast.error(t('passwordMinLength'))
      return
    }
    
    changePasswordMutation.mutate({
      currentPassword: passwordData.currentPassword,
      newPassword: passwordData.newPassword
    })
  }

  const handleDeleteAccount = () => {
    if (window.confirm(t('confirmDeleteAccount'))) {
      deleteAccountMutation.mutate()
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ACTIVE': return 'bg-green-100 text-green-800 border-green-200'
      case 'INACTIVE': return 'bg-gray-100 text-gray-800 border-gray-200'
      case 'SUSPENDED': return 'bg-red-100 text-red-800 border-red-200'
      default: return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'ACTIVE': return t('statusActive')
      case 'INACTIVE': return t('statusInactive')
      case 'SUSPENDED': return t('statusSuspended')
      default: return status
    }
  }

  if (!user) {
    return <UserProfileSkeleton />
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <User className="h-6 w-6" />
        <h2 className="text-2xl font-bold">{t('userProfile')}</h2>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Informações Básicas */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>{t('basicInformation')}</CardTitle>
              {!isEditing ? (
                <Button variant="outline" size="sm" onClick={() => setIsEditing(true)}>
                  <Edit className="h-4 w-4 mr-2" />
                  {tCommon('edit')}
                </Button>
              ) : (
                <div className="flex gap-2">
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={() => {
                      setIsEditing(false)
                      setFormData({
                        fullName: user.fullName || '',
                        companyName: user.companyName || '',
                        notifications: false,
                        newsletter: false,
                        theme: 'system'
                      })
                    }}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                  <Button 
                    size="sm" 
                    onClick={handleSaveProfile}
                    disabled={updateProfileMutation.isPending}
                  >
                    <Save className="h-4 w-4 mr-2" />
                    {updateProfileMutation.isPending ? t('saving') : tCommon('save')}
                  </Button>
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center">
                <User className="h-8 w-8 text-primary" />
              </div>
              <div>
                <h3 className="font-semibold text-lg">{user.fullName}</h3>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Mail className="h-4 w-4" />
                  {user.email}
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <Key className="h-3 w-3" />
                  <span className="text-muted-foreground">ID:</span>
                  <code className="bg-muted px-2 py-1 rounded text-xs font-mono">{user.id}</code>
                </div>
              </div>
            </div>

            <div className="grid gap-4">
              <div>
                <Label htmlFor="fullName">{t('fullName')}</Label>
                {isEditing ? (
                  <Input
                    id="fullName"
                    value={formData.fullName}
                    onChange={(e) => setFormData(prev => ({ ...prev, fullName: e.target.value }))}
                  />
                ) : (
                  <p className="text-sm mt-1">{user.fullName}</p>
                )}
              </div>

              {(isEditing || user.companyName) && (
                <div>
                  <Label htmlFor="companyName">{t('company')}</Label>
                  {isEditing ? (
                    <Input
                      id="companyName"
                      value={formData.companyName}
                      onChange={(e) => setFormData(prev => ({ ...prev, companyName: e.target.value }))}
                    />
                  ) : (
                    <p className="text-sm mt-1">{user.companyName || t('notInformed')}</p>
                  )}
                </div>
              )}

              <div>
                <Label>{t('email')}</Label>
                <p className="text-sm mt-1 text-muted-foreground">{user.email}</p>
              </div>

              <div className="flex items-center gap-4">
                <div>
                  <Label>{t('role')}</Label>
                  <div className="mt-1">
                    <Badge variant="outline">{user.role}</Badge>
                  </div>
                </div>
                <div>
                  <Label>{t('plan')}</Label>
                  <div className="mt-1">
                    <Badge variant="outline">{user.plan}</Badge>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <Label className="text-muted-foreground">{t('totalCredits')}</Label>
                  <p className="flex items-center gap-1 mt-1">
                    <CreditCard className="h-4 w-4" />
                    {user.creditsTotal}
                  </p>
                </div>
                <div>
                  <Label className="text-muted-foreground">{t('remainingCredits')}</Label>
                  <p className="flex items-center gap-1 mt-1">
                    <CreditCard className="h-4 w-4" />
                    {user.creditsRemaining}
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Estatísticas */}
        <Card>
          <CardHeader>
            <CardTitle>{t('accountStats')}</CardTitle>
            <CardDescription>{t('activitySummary')}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4">
              <div className="flex items-center justify-between p-3 border rounded">
                <div className="flex items-center gap-2">
                  <CreditCard className="h-5 w-5 text-blue-600" />
                  <span>{t('remainingCredits')}</span>
                </div>
                <span className="font-bold text-lg">{user.creditsRemaining}</span>
              </div>
              
              <div className="flex items-center justify-between p-3 border rounded">
                <div className="flex items-center gap-2">
                  <Settings className="h-5 w-5 text-green-600" />
                  <span>{t('totalCredits')}</span>
                </div>
                <span className="font-bold text-lg">{user.creditsTotal}</span>
              </div>
              
              <div className="flex items-center justify-between p-3 border rounded">
                <div className="flex items-center gap-2">
                  <Key className="h-5 w-5 text-purple-600" />
                  <span>{t('role')}</span>
                </div>
                <span className="font-bold text-lg">{user.role}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Preferências */}
        <Card>
          <CardHeader>
            <CardTitle>{t('preferences')}</CardTitle>
            <CardDescription>{t('configurePreferences')}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Bell className="h-4 w-4" />
                <Label>{t('emailNotifications')}</Label>
              </div>
              {isEditing ? (
                <input
                  type="checkbox"
                  checked={formData.notifications}
                  onChange={(e) => setFormData(prev => ({ ...prev, notifications: e.target.checked }))}
                  className="rounded"
                />
              ) : (
                <Badge variant="secondary">{t('disabled')}</Badge>
              )}
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Mail className="h-4 w-4" />
                <Label>{t('newsletter')}</Label>
              </div>
              {isEditing ? (
                <input
                  type="checkbox"
                  checked={formData.newsletter}
                  onChange={(e) => setFormData(prev => ({ ...prev, newsletter: e.target.checked }))}
                  className="rounded"
                />
              ) : (
                <Badge variant="secondary">{t('disabled')}</Badge>
              )}
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Settings className="h-4 w-4" />
                <Label>{t('theme')}</Label>
              </div>
              {isEditing ? (
                <Select
                  value={formData.theme}
                  onValueChange={(value) => setFormData(prev => ({ ...prev, theme: value as 'light' | 'dark' | 'system' }))}
                >
                  <SelectTrigger className="w-32">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="light">{t('light')}</SelectItem>
                    <SelectItem value="dark">{t('dark')}</SelectItem>
                    <SelectItem value="system">{t('system')}</SelectItem>
                  </SelectContent>
                </Select>
              ) : (
                <Badge variant="outline">{t('system')}</Badge>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Segurança */}
        <Card>
          <CardHeader>
            <CardTitle>{t('security')}</CardTitle>
            <CardDescription>{t('manageAccountSecurity')}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {!isChangingPassword ? (
              <Button 
                variant="outline" 
                onClick={() => setIsChangingPassword(true)}
                className="w-full"
              >
                <Lock className="h-4 w-4 mr-2" />
                {t('changePassword')}
              </Button>
            ) : (
              <div className="space-y-3">
                <div>
                  <Label htmlFor="current-password">{t('currentPassword')}</Label>
                  <Input
                    id="current-password"
                    type="password"
                    value={passwordData.currentPassword}
                    onChange={(e) => setPasswordData(prev => ({ ...prev, currentPassword: e.target.value }))}
                  />
                </div>
                <div>
                  <Label htmlFor="new-password">{t('newPassword')}</Label>
                  <Input
                    id="new-password"
                    type="password"
                    value={passwordData.newPassword}
                    onChange={(e) => setPasswordData(prev => ({ ...prev, newPassword: e.target.value }))}
                  />
                </div>
                <div>
                  <Label htmlFor="confirm-password">{t('confirmNewPassword')}</Label>
                  <Input
                    id="confirm-password"
                    type="password"
                    value={passwordData.confirmPassword}
                    onChange={(e) => setPasswordData(prev => ({ ...prev, confirmPassword: e.target.value }))}
                  />
                </div>
                <div className="flex gap-2">
                  <Button 
                    variant="outline" 
                    onClick={() => {
                      setIsChangingPassword(false)
                      setPasswordData({ currentPassword: '', newPassword: '', confirmPassword: '' })
                    }}
                  >
                    {tCommon('cancel')}
                  </Button>
                  <Button 
                    onClick={handleChangePassword}
                    disabled={changePasswordMutation.isPending}
                  >
                    {changePasswordMutation.isPending ? t('changing') : t('changePassword')}
                  </Button>
                </div>
              </div>
            )}

            <div className="border-t pt-4">
              <div className="bg-red-50 border border-red-200 rounded p-4">
                <h4 className="font-medium text-red-800 mb-2">{t('dangerZone')}</h4>
                <p className="text-sm text-red-700 mb-3">
                  {t('deleteAccountWarning')}
                </p>
                <Button 
                  variant="destructive" 
                  size="sm"
                  onClick={handleDeleteAccount}
                  disabled={deleteAccountMutation.isPending}
                >
                  {deleteAccountMutation.isPending ? t('deleting') : t('deleteAccount')}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}