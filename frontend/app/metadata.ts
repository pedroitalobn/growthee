import { Metadata } from 'next'

export const metadata: Metadata = {
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
  alternates: {
    canonical: '/',
  },
  openGraph: {
    type: 'website',
    locale: 'pt_BR',
    url: '/',
    title: 'Growthee - API de Enriquecimento de Dados',
    description: 'Plataforma completa para enriquecimento de dados empresariais com APIs poderosas e interface intuitiva.',
    siteName: 'Growthee',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Growthee - API de Enriquecimento de Dados',
    description: 'Plataforma completa para enriquecimento de dados empresariais com APIs poderosas e interface intuitiva.',
    creator: '@growthee',
  },
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
  verification: {
    google: process.env.GOOGLE_SITE_VERIFICATION,
  },
}