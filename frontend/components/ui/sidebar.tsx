import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { Button } from './button'
import { ThemeToggle } from './theme-toggle'
import { Home, Users, CreditCard, Settings } from 'lucide-react'

export function Sidebar() {
  const pathname = usePathname()

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: Home },
    { name: 'Billing', href: '/billing', icon: CreditCard },
    { name: 'Admin', href: '/admin', icon: Settings },
  ]

  return (
    <div className="flex h-full w-64 flex-col border-r bg-card">
      <div className="flex h-14 items-center border-b px-4">
        <h2 className="text-lg font-semibold">EnrichStory</h2>
      </div>
      <div className="flex flex-1 flex-col gap-1 p-4">
        {navigation.map((item) => {
          const Icon = item.icon
          return (
            <Link key={item.name} href={item.href}>
              <Button
                variant={pathname === item.href ? 'secondary' : 'ghost'}
                className="w-full justify-start gap-2"
              >
                <Icon className="h-4 w-4" />
                {item.name}
              </Button>
            </Link>
          )
        })}
      </div>
      <div className="border-t p-4">
        <ThemeToggle />
      </div>
    </div>
  )
}