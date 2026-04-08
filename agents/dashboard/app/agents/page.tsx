'use client'

import React, { useState } from 'react'
import { Pane } from '@/components/shell/Pane'
import { AgentSwarmView } from '@/components/views/AgentSwarmView'

export default function AgentsPage(): React.JSX.Element {
  const [focused, setFocused] = useState(false)
  return (
    <div className="hyper-shell" style={{ gridTemplate: `"agents" 1fr / 1fr` }}>
      <Pane
        id="agents"
        title="🤖 Agents Status Board"
        gridArea="agents"
        focused={focused}
        onFocusToggle={() => setFocused(!focused)}
      >
        <AgentSwarmView />
      </Pane>
    </div>
  )
}
