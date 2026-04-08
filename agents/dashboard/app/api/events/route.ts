import { NextRequest } from 'next/server'

const CORE_URL = process.env.HYPERCODE_CORE_URL ?? 'http://hypercode-core:8000'

export const dynamic = 'force-dynamic'

export async function GET(_req: NextRequest) {
  const encoder = new TextEncoder()

  const stream = new ReadableStream({
    async start(controller) {
      // Proxy the SSE stream from the backend
      try {
        const res = await fetch(`${CORE_URL}/api/v1/events`, { cache: 'no-store' })
        if (!res.body) { controller.close(); return }
        const reader = res.body.getReader()
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          controller.enqueue(value)
        }
      } catch {
        // Send keep-alive on disconnect
        controller.enqueue(encoder.encode(': keep-alive\n\n'))
      }
      controller.close()
    },
  })

  return new Response(stream, {
    headers: {
      'Content-Type':  'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection':    'keep-alive',
    },
  })
}
