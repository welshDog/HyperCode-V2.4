'use client'

import React, { useState } from 'react'
import { Pane } from '@/components/shell/Pane'
import { MissionGraphPanel } from '@/components/panels/MissionGraphPanel'

export default function FlowsPage(): React.JSX.Element {
  const [focused, setFocused] = useState(false)
  return (
    <div className="hyper-shell" style={{ gridTemplate: `"flows" 1fr / 1fr` }}>
      <Pane
        id="flows"
        title="🕸️ Mission Graph — Active HyperFlow"
        gridArea="flows"
        focused={focused}
        onFocusToggle={() => setFocused(!focused)}
      >
        <MissionGraphPanel />
      </Pane>
    </div>
  )
}
