import Link from 'next/link'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { useTranslations, useLocale } from 'next-intl'
import { cn } from '@/lib/utils'
import { Button } from './button'
import { ThemeToggle } from './theme-toggle'
import { LanguageSwitcher } from './language-switcher'
import { useAuthStore } from '@/lib/store/auth-store'
import { Home, Users, CreditCard, Settings, User, Key, FileText, BarChart3, LogOut, MessageSquare } from 'lucide-react'
import Image from 'next/image'

export function Sidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const searchParams = useSearchParams()
  
  // Safely get locale and translations with fallbacks
  const locale = useLocale() || 'en'
  const t = useTranslations('navigation')
  
  const { user, logout } = useAuthStore()

  const navigation = [
    {
      name: t('chat'),
      href: `/${locale}/dashboard?tab=chat`,
      icon: MessageSquare
    },
    {
      name: t('dashboard'),
      href: `/${locale}/dashboard?tab=overview`,
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
    ...((user?.role === 'ADMIN' || user?.role === 'SUPER_ADMIN') ? [{ name: t('admin'), href: `/${locale}/admin`, icon: Users }] : []),
  ]

  const handleLogout = () => {
    logout()
    router.push(`/${locale}/login`)
  }

  return (
    <div className="flex h-full w-64 flex-col border-r">
      <div className="flex h-16 items-center justify-center border-b px-4">
        <div className="flex items-center justify-center">
          <svg id="Layer_1" data-name="Layer 1" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 655.36 76.6" className="h-6 w-auto">
            <path d="M0,40.77C0,20.76,14.31,3.23,44,3.23s39.59,13.88,39.59,26.79c0,.43,0,1.08-.11,2.04h-13.45c.11-.65.11-1.08.11-1.51,0-7.42-6.78-15.6-25.82-15.6s-29.26,11.62-29.26,25.93c0,13.45,8.82,24.74,29.15,24.74,18.93,0,25.49-9.47,25.49-16.03v-.32h-28.51v-9.36h43.24v35.39h-12.26c.11-2.8.43-9.04.54-14.41h-.11c-3.01,10.22-13.55,15.71-30.01,15.71-30.43-.01-42.59-17.43-42.59-35.83Z" style={{fill: '#00fe6c'}}/>
            <path d="M96.28,22.16h13.77l-.22,16.24h.22c3.33-9.57,10.86-17.32,25.82-17.32,17.53,0,24.2,9.68,24.2,24.53,0,4.09-.22,7.75-.32,9.47h-12.91c.11-1.29.21-3.55.21-5.49,0-11.4-3.77-17.21-15.17-17.21-14.09,0-21.84,10.97-21.84,22.81v20.12h-13.77V22.16h.01Z" style={{fill: '#00fe6c'}}/>
            <path d="M169.76,48.84c0-13.98,10.33-27.75,36.47-27.75s36.47,13.77,36.47,27.75-10.11,27.54-36.47,27.54-36.47-13.45-36.47-27.54ZM228.92,48.84c0-8.82-6.13-17-22.7-17s-22.7,8.18-22.7,17,6.02,16.78,22.7,16.78,22.7-7.96,22.7-16.78Z" style={{fill: '#00fe6c'}}/>
            <path d="M247.64,22.16h14.85l15.6,40.45h.11l18.07-40.45h13.45l17.53,40.45h.11l15.81-40.45h13.55l-21.3,53.14h-16.46l-16.67-38.94h-.21l-17,38.94h-16.14s-21.3-53.14-21.3-53.14Z" style={{fill: '#00fe6c'}}/>
            <path d="M371.03,54.65v-21.73h-10.65v-10.76h8.61c2.26,0,3.01-1.18,3.33-3.98l.86-8.07h11.62v12.05h30.34v10.76h-30.34v21.08c0,7.64,3.87,11.19,17.21,11.19,4.41,0,9.9-.65,12.69-1.18v10.43c-2.37.75-8.18,1.61-14.2,1.61-22.16,0-29.48-9.14-29.48-21.41h.01Z" style={{fill: '#00fe6c'}}/>
            <path d="M425.9,0h13.77v26.46c0,3.23-.11,6.99-.21,11.3h.21c3.98-10.86,12.69-16.67,29.8-16.67,21.62,0,29.37,10.22,29.37,23.45v30.77h-13.77v-27.11c0-9.57-4.73-15.81-20.76-15.81-12.91,0-24.63,6.13-24.63,19.04v23.88h-13.77V0h0Z" style={{fill: '#00fe6c'}}/>
            <path d="M577.36,51.96h-54.86c.97,8.07,6.13,14.63,22.37,14.63,14.09,0,19.04-4.2,19.9-8.61h12.59c-.65,9.25-9.79,18.39-32.49,18.39-28.08,0-36.25-13.98-36.25-27.22,0-17,13.02-28.08,35.39-28.08s33.35,10.11,33.35,26.57v4.32ZM564.78,43.35c0-7.1-5.7-12.48-20.22-12.48-13.34,0-19.79,4.52-21.62,12.8h41.85v-.32h-.01Z" style={{fill: '#00fe6c'}}/>
            <path d="M655.35,51.96h-54.86c.97,8.07,6.13,14.63,22.38,14.63,14.09,0,19.04-4.2,19.9-8.61h12.59c-.65,9.25-9.79,18.39-32.49,18.39-28.08,0-36.25-13.98-36.25-27.22,0-17,13.02-28.08,35.39-28.08s33.35,10.11,33.35,26.57v4.32ZM642.77,43.35c0-7.1-5.7-12.48-20.22-12.48-13.34,0-19.79,4.52-21.62,12.8h41.85v-.32h-.01Z" style={{fill: '#00fe6c'}}/>
          </svg>
        </div>
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
                className={cn(
                  "w-full justify-start gap-2",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                )}
              >
                <Icon className="h-4 w-4" />
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
          className="w-full justify-start gap-2 text-red-400 hover:bg-accent hover:text-red-300"
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