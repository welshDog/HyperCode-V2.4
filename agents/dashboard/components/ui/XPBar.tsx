import React from 'react'

export function XPBar({
  xp,
  maxXp,
  level,
}: {
  xp:    number
  maxXp: number
  level: number
}): React.JSX.Element {
  const pct = Math.min(100, Math.round((xp / maxXp) * 100))
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--text-secondary)', marginBottom: 2 }}>
        <span>LVL {level}</span>
        <span>{xp} / {maxXp} XP</span>
      </div>
      <div className="xp-bar" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label={`${pct}% to next level`}>
        <div className="xp-bar-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}
