import type { Metadata } from 'next'
import './globals.css'
import { AppShell } from '@/components/shell/AppShell'

export const metadata: Metadata = {
  title: 'WelshDog HyperCode IDE',
  description: 'Hyper Station — Unified IDE + Mission Control',
  viewport: 'width=device-width, initial-scale=1',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}): React.JSX.Element {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="hyper-root">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  )
}
