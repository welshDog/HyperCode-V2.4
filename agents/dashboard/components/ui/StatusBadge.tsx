import React from 'react'

export type Status = 'healthy' | 'warning' | 'error' | 'idle'

export function StatusBadge({ status }: { status: Status }): React.JSX.Element {
  return (
    <span className={`tag ${status}`} role="status" aria-label={`Status: ${status}`}>
      <span className={`status-dot ${status}`} aria-hidden="true" />
      {status}
    </span>
  )
}
