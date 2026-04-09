'use client'

import React, { useEffect, useMemo, useRef, useState } from 'react'

export default function DockerZonePage(): React.JSX.Element {
  const iframeRef = useRef<HTMLIFrameElement | null>(null)
  const [contentHeight, setContentHeight] = useState<number | null>(null)

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
      if (event?.data?.type !== 'hypercode:docker-dashboard:height') return
      if (event.origin !== window.location.origin) return
      if (iframeRef.current?.contentWindow && event.source !== iframeRef.current.contentWindow) return
      if (typeof event.data.height !== 'number') return
      if (!Number.isFinite(event.data.height)) return
      if (event.data.height < 0) return
      setContentHeight(event.data.height)
    }

    window.addEventListener('message', onMessage)
    return () => window.removeEventListener('message', onMessage)
  }, [])

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

