import Link from 'next/link'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { useTranslations, useLocale } from 'next-intl'
import { cn } from '@/lib/utils'
import { Button } from './button'
import { ThemeToggle } from './theme-toggle'
import { LanguageSwitcher } from './language-switcher'
import { useAuthStore } from '@/lib/store/auth-store'
import { Home, Users, CreditCard, Settings, User, Key, FileText, BarChart3, LogOut } from 'lucide-react'

export function Sidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const searchParams = useSearchParams()
  
  // Safely get locale and translations with fallbacks
  let locale: string
  let t: any
  
  try {
    locale = useLocale()
    t = useTranslations('navigation')
  } catch (error) {
    // Fallback if intl context is not available
    locale = 'en'
    t = (key: string) => {
      const fallbacks: Record<string, string> = {
        dashboard: 'Dashboard',
        billing: 'Billing',
        admin: 'Admin',
        logout: 'Logout'
      }
      return fallbacks[key] || key
    }
  }
  
  const { user, logout } = useAuthStore()

  const navigation = [
    {
      name: t('dashboard'),
      href: `/${locale}/dashboard`,
      icon: Home
    },
    {
      name: t('playground'),
      href: `/${locale}/dashboard?tab=tester`,
      icon: BarChart3
    },
    {
      name: t('documentation'),
      href: `/${locale}/dashboard?tab=documentation`,
      icon: FileText
    },
    {
      name: t('apiKeys'),
      href: `/${locale}/dashboard?tab=api-keys`,
      icon: Key
    },
    {
      name: t('credits'),
      href: `/${locale}/dashboard?tab=credits`,
      icon: CreditCard
    },
    {
      name: t('billing'),
      href: `/${locale}/dashboard?tab=billing`,
      icon: Settings
    },
    {
      name: t('profile'),
      href: `/${locale}/dashboard?tab=profile`,
      icon: User
    },
    ...(user?.role === 'ADMIN' ? [{ name: t('admin'), href: `/${locale}/admin`, icon: Users }] : []),
  ]

  const handleLogout = () => {
    logout()
    router.push(`/${locale}/login`)
  }

  return (
    <div className="flex h-full w-64 flex-col border-r bg-card fade-in">
      <div className="flex h-14 items-center border-b px-4">
        <h2 className="text-lg font-semibold">{t('appName')}</h2>
      </div>
      <div className="flex flex-1 flex-col gap-1 p-4">
        {navigation.map((item) => {
          const Icon = item.icon
          const isActive = (() => {
            // For exact path matches (like /admin)
            if (pathname === item.href.split('?')[0]) {
              // If it's a dashboard tab, check the tab parameter
              if (item.href.includes('?tab=')) {
                const expectedTab = item.href.split('?tab=')[1]
                const currentTab = searchParams?.get('tab')
                return currentTab === expectedTab
              }
              // For dashboard overview (no tab or tab=overview)
              if (item.href.includes('/dashboard') && !item.href.includes('?tab=')) {
                const currentTab = searchParams?.get('tab')
                return !currentTab || currentTab === 'overview'
              }
              return true
            }
            return false
          })()
          return (
            <Link key={item.name} href={item.href}>
              <Button
                variant={isActive ? 'secondary' : 'ghost'}
                className="w-full justify-start gap-2 transition-all duration-200 ease-out hover:translate-x-1"
              >
                <Icon className="h-4 w-4 transition-transform duration-200 ease-out" />
                {item.name}
              </Button>
            </Link>
          )
        })}
      </div>
      <div className="border-t p-4 space-y-2">
        <div className="flex items-center gap-2 px-2 py-1 text-sm text-muted-foreground">
          <User className="h-4 w-4" />
          <span className="truncate">{user?.fullName || user?.email}</span>
        </div>
        <Button
          variant="ghost"
          className="w-full justify-start gap-2 text-red-600 hover:text-red-700 hover:bg-red-50"
          onClick={handleLogout}
        >
          <LogOut className="h-4 w-4" />
          {t('logout')}
        </Button>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <LanguageSwitcher />
        </div>
      </div>
    </div>
  )
}