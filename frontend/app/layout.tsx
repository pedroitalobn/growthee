import './globals.css'
import { generateStaticMetadata } from '@/lib/metadata'

export const metadata = generateStaticMetadata()

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html suppressHydrationWarning>
      <body>
        {children}
      </body>
    </html>
  )
}