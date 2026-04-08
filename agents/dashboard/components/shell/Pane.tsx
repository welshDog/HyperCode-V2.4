'use client'

import React from 'react'

export interface PaneProps {
  id:            string
  title:         string
  gridArea:      string
  focused:       boolean
  onFocusToggle: () => void
  children:      React.ReactNode
}

export function Pane({
  id, title, gridArea, focused, onFocusToggle, children
}: PaneProps): React.JSX.Element {
  return (
    <div
      className={`pane${focused ? ' focused' : ''}`}
      style={{ gridArea }}
      data-testid={`pane-${id}`}
      role="region"
      aria-label={title}
    >
      <div className="pane-header">
        <span>{title}</span>
        <button
          className={`btn${focused ? ' active' : ''}`}
          onClick={onFocusToggle}
          aria-label={focused ? 'Exit focus mode' : 'Focus this pane'}
          title={focused ? 'Exit focus' : 'Focus'}
        >
          {focused ? '\u2715 Exit Focus' : '\u26F6 Focus'}
        </button>
      </div>
      <div className="pane-body">
        {children}
      </div>
    </div>
  )
}
