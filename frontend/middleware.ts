import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import createIntlMiddleware from 'next-intl/middleware'
import { locales, defaultLocale } from './i18n'

// Create the internationalization middleware
const intlMiddleware = createIntlMiddleware({
  locales,
  defaultLocale,
  localeDetection: true,
  localePrefix: 'as-needed'
})

export function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname
  
  // Check if pathname has locale
  const pathnameHasLocale = locales.some(
    (locale) => pathname.startsWith(`/${locale}/`) || pathname === `/${locale}`
  )
  
  // If pathname doesn't have locale, apply intl middleware first
  if (!pathnameHasLocale) {
    return intlMiddleware(request)
  }
  
  const authCookie = request.cookies.get('auth-storage')
  
  // Get the base pathname without locale
  const basePathname = pathname.split('/').slice(2).join('/') || '/'
  const isPublicPage = ['/login', '/signup'].includes(basePathname)
  const isHomePage = basePathname === '/'
  const isDashboardPage = basePathname.startsWith('/dashboard')
  const isAdminPage = basePathname.startsWith('/admin')

  // Verifica se tem token válido
  let hasValidToken = false
  if (authCookie?.value) {
    try {
      const authData = JSON.parse(authCookie.value)
      hasValidToken = !!(authData?.state?.token && authData?.state?.isAuthenticated)
    } catch {
      hasValidToken = false
    }
  }

  // Se não tem token válido e está tentando acessar dashboard ou admin, redireciona para login
  if (!hasValidToken && (isDashboardPage || isAdminPage)) {
    const locale = pathname.split('/')[1]
    const validLocale = locales.includes(locale as any) ? locale : defaultLocale
    return NextResponse.redirect(new URL(`/${validLocale}/login`, request.url))
  }

  // Se tem token válido e está em página de auth, redireciona baseado no role
  if (hasValidToken && isPublicPage) {
    const locale = pathname.split('/')[1]
    const validLocale = locales.includes(locale as any) ? locale : defaultLocale
    
    // Verificar role do usuário para redirecionamento
    if (authCookie?.value) {
      try {
        const authData = JSON.parse(authCookie.value)
        const userRole = authData?.state?.user?.role
        
        if (userRole === 'SUPER_ADMIN') {
          return NextResponse.redirect(new URL(`/${validLocale}/admin`, request.url))
        } else {
          return NextResponse.redirect(new URL(`/${validLocale}/dashboard`, request.url))
        }
      } catch {
        return NextResponse.redirect(new URL(`/${validLocale}/dashboard`, request.url))
      }
    } else {
      return NextResponse.redirect(new URL(`/${validLocale}/dashboard`, request.url))
    }
  }

  // Continue with the request
  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
}