import { Metadata } from 'next'
import { getTranslations } from 'next-intl/server'

type PageType = 'dashboard' | 'login' | 'signup' | 'admin' | 'billing' | 'home'

export async function generatePageMetadata(
  pageType: PageType,
  locale: string = 'pt'
): Promise<Metadata> {
  const t = await getTranslations({ locale, namespace: 'metadata' })
  const tCommon = await getTranslations({ locale, namespace: 'common' })
  
  const baseUrl = process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'
  const appName = tCommon('appName')
  
  const pageConfig = {
    dashboard: {
      title: t('dashboard.title'),
      description: t('dashboard.description')
    },
    login: {
      title: t('login.title'),
      description: t('login.description')
    },
    signup: {
      title: t('signup.title'),
      description: t('signup.description')
    },
    admin: {
      title: t('admin.title'),
      description: t('admin.description')
    },
    billing: {
      title: t('billing.title'),
      description: t('billing.description')
    },
    home: {
      title: t('home.title'),
      description: t('home.description')
    }
  }
  
  const config = pageConfig[pageType]
  const fullTitle = `${config.title} | ${appName}`
  
  return {
    title: fullTitle,
    description: config.description,
    openGraph: {
      title: fullTitle,
      description: config.description,
      url: `${baseUrl}/${locale}`,
      siteName: appName,
      locale: locale === 'pt' ? 'pt_BR' : 'en_US',
      type: 'website'
    },
    twitter: {
      card: 'summary_large_image',
      title: fullTitle,
      description: config.description
    },
    alternates: {
      canonical: `${baseUrl}/${locale}`
    }
  }
}

export function generateStaticMetadata(): Metadata {
  return {
    title: {
      default: 'Growthee - API de Enriquecimento de Dados',
    template: '%s | Growthee'
    },
    description: 'Plataforma completa para enriquecimento de dados empresariais com APIs poderosas e interface intuitiva.',
    keywords: [
      'enriquecimento de dados',
      'API',
      'dados empresariais',
      'automação',
      'integração',
      'business intelligence'
    ],
    authors: [{ name: 'Growthee Team' }],
  creator: 'Growthee',
  publisher: 'Growthee',
    formatDetection: {
      email: false,
      address: false,
      telephone: false,
    },
    metadataBase: new URL(process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'),
    robots: {
      index: true,
      follow: true,
      googleBot: {
        index: true,
        follow: true,
        'max-video-preview': -1,
        'max-image-preview': 'large',
        'max-snippet': -1,
      },
    },
    ...(process.env.GOOGLE_SITE_VERIFICATION && {
      verification: {
        google: process.env.GOOGLE_SITE_VERIFICATION,
      },
    }),
  }
}