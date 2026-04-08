'use client'

import React, { useState } from 'react'
import { Pane } from '@/components/shell/Pane'
import { HealthView } from '@/components/views/HealthView'

export default function HealthPage(): React.JSX.Element {
  const [focused, setFocused] = useState(false)
  return (
    <div className="hyper-shell" style={{ gridTemplate: `"health" 1fr / 1fr` }}>
      <Pane id="health" title="🧪 Docker + Service Health" gridArea="health" focused={focused} onFocusToggle={() => setFocused(!focused)}>
        <HealthView />
      </Pane>
    </div>
  )
}
