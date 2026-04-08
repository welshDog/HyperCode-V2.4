'use client'

import React, { useState } from 'react'
import { Pane } from '@/components/shell/Pane'
import { MCPGatewayView } from '@/components/views/MCPGatewayView'

export default function MCPPage(): React.JSX.Element {
  const [focused, setFocused] = useState(false)
  return (
    <div className="hyper-shell" style={{ gridTemplate: `"mcp" 1fr / 1fr` }}>
      <Pane id="mcp" title="🧩 MCP Gateway Status" gridArea="mcp" focused={focused} onFocusToggle={() => setFocused(!focused)}>
        <MCPGatewayView />
      </Pane>
    </div>
  )
}
