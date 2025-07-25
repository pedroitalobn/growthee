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
        destination: 'http://$$cap_appname-backend:8000/api/:path*',
      },
      {
        source: '/health',
        destination: 'http://$$cap_appname-backend:8000/health',
      },
      {
        source: '/docs',
        destination: 'http://$$cap_appname-backend:8000/docs',
      },
    ];
  },
}

module.exports = nextConfig