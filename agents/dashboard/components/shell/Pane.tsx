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
  const titleId = `pane-${id}-title`
  return (
    <div
      className={`pane${focused ? ' focused' : ''}`}
      style={{ gridArea }}
      data-testid={`pane-${id}`}
      role="region"
      aria-labelledby={titleId}
    >
      <div className="pane-header">
        <h2 className="pane-title" id={titleId}>{title}</h2>
        <button
          className={`btn${focused ? ' active' : ''}`}
          type="button"
          onClick={onFocusToggle}
          aria-label={focused ? 'Exit focus mode' : 'Focus this pane'}
          aria-pressed={focused}
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
