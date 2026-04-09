'use client'

import React, { useState } from 'react'
import { Pane } from '@/components/shell/Pane'

export default function DockerZonePage(): React.JSX.Element {
  const [focused, setFocused] = useState(false)
  return (
    <div className="hyper-shell" style={{ gridTemplate: `"docker" 1fr / 1fr` }}>
      <Pane
        id="docker"
        title="🐳 Docker Zone"
        gridArea="docker"
        focused={focused}
        onFocusToggle={() => setFocused(!focused)}
      >
        <iframe
          title="Docker Dashboard"
          src="/hypercode-docker-dashboard.html"
          style={{ width: '100%', height: '100%', border: 0 }}
        />
      </Pane>
    </div>
  )
}

