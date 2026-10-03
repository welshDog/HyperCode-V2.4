import type { Metadata } from 'next'
import './globals.css'
import { AppShell } from '@/components/shell/AppShell'
import { SensoryProvider } from '@/components/sensory/SensoryProvider'
import { bootScript } from '@/lib/sensory/settings'

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
    <html lang="en" suppressHydrationWarning data-sensory="calm" data-motion="off" data-density="roomy" data-contrast="normal" data-font="inter" data-progress="hidden" data-layout="calm">
      <head>
        {/* Applies saved Sensory Settings before first paint (no flash). Built from the settings model. */}
        <script dangerouslySetInnerHTML={{ __html: bootScript() }} />
      </head>
      <body className="hyper-root">
        <SensoryProvider>
          <AppShell>{children}</AppShell>
        </SensoryProvider>
      </body>
    </html>
  )
}
