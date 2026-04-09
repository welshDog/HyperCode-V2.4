'use client'

import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useToast, type ToastVariant } from '@/components/ui/ToastProvider'

export default function DockerZonePage(): React.JSX.Element {
  const iframeRef = useRef<HTMLIFrameElement | null>(null)
  const [contentHeight, setContentHeight] = useState<number | null>(null)
  const { pushToast } = useToast()

  const iframeStyle = useMemo<React.CSSProperties>(() => {
    const height = contentHeight ? `${contentHeight}px` : '100%'
    return {
      width: '100%',
      minHeight: '100%',
      height,
      border: 0,
      display: 'block',
      overflow: 'hidden',
    }
  }, [contentHeight])

  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      if (event.origin !== window.location.origin) return
      if (iframeRef.current?.contentWindow && event.source !== iframeRef.current.contentWindow) return
      const type = event?.data?.type
      if (type === 'hypercode:docker-dashboard:height') {
        if (typeof event.data.height !== 'number') return
        if (!Number.isFinite(event.data.height)) return
        if (event.data.height < 0) return
        setContentHeight(event.data.height)
        return
      }

      if (type === 'hypercode:docker-dashboard:toast') {
        const variantRaw = event?.data?.variant
        const variant: ToastVariant =
          variantRaw === 'success' || variantRaw === 'error' || variantRaw === 'info' ? variantRaw : 'info'
        const title = typeof event?.data?.title === 'string' ? event.data.title : ''
        const message = typeof event?.data?.message === 'string' ? event.data.message : undefined
        if (!title) return
        pushToast({ variant, title, message })
      }
    }

    window.addEventListener('message', onMessage)
    return () => window.removeEventListener('message', onMessage)
  }, [pushToast])

  return (
    <div style={{ height: '100%', overflow: 'auto' }}>
      <iframe
        ref={iframeRef}
        title="Docker Command Centre"
        src="/hypercode-docker-dashboard.html"
        style={iframeStyle}
        scrolling="no"
      />
    </div>
  )
}

