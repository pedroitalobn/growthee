/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY: process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY || '',
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: process.env.NEXT_PUBLIC_API_URL + '/api/:path*' || 'http://localhost:8000/api/:path*',
      },
      {
        source: '/health',
        destination: process.env.NEXT_PUBLIC_API_URL + '/health' || 'http://localhost:8000/health',
      },
      {
        source: '/docs',
        destination: process.env.NEXT_PUBLIC_API_URL + '/docs' || 'http://localhost:8000/docs',
      },
    ];
  },
  poweredByHeader: false,
  compress: true,
}

module.exports = nextConfig