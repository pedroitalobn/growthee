import { Metadata } from 'next'

export const metadata: Metadata = {
  title: {
    default: 'EnrichStory - API de Enriquecimento de Dados',
    template: '%s | EnrichStory'
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
  authors: [{ name: 'EnrichStory Team' }],
  creator: 'EnrichStory',
  publisher: 'EnrichStory',
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
    title: 'EnrichStory - API de Enriquecimento de Dados',
    description: 'Plataforma completa para enriquecimento de dados empresariais com APIs poderosas e interface intuitiva.',
    siteName: 'EnrichStory',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'EnrichStory - API de Enriquecimento de Dados',
    description: 'Plataforma completa para enriquecimento de dados empresariais com APIs poderosas e interface intuitiva.',
    creator: '@enrichstory',
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