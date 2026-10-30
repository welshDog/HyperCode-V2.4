// Turns Prometheus instant-query results into the Stack Resources view model.
// Pure functions only (no I/O), so the thresholds and sorting are unit-tested.

// Same lines as scripts/ram_guard.py: WSL available RED < 1200 MB, AMBER < 1500 MB.
export const RAM_RED_MB = 1200
export const RAM_AMBER_MB = 1500

export type RamVerdict = 'GREEN' | 'AMBER' | 'RED' | 'UNKNOWN'
export type Severity = 'ok' | 'warn' | 'crit' | 'unbounded'

export type PromVector = Array<{ metric: Record<string, string>; value: [number, string] }>

export type SnapshotInput = {
  workingSet: PromVector
  limit: PromVector
  cpu: PromVector
  wslAvailable: PromVector
  wslTotal: PromVector
  swapUsed: PromVector
}

export type ContainerRow = {
  name: string
  workingSetMb: number
  limitMb: number | null
  pctOfLimit: number | null
  cpuCores: number
  severity: Severity
}

export type ResourceSnapshot =
  | {
      available: true
      collectedAt: string
      wsl: { availableMb: number; totalMb: number; swapUsedMb: number; verdict: RamVerdict } | null
      containers: ContainerRow[]
      totals: { count: number; workingSetMb: number; nearLimit: number }
    }
  | { available: false; reason: string; collectedAt: string }

const MB = 1024 * 1024

export function ramVerdict(availableMb: number | null | undefined): RamVerdict {
  if (availableMb == null || !Number.isFinite(availableMb)) return 'UNKNOWN'
  if (availableMb < RAM_RED_MB) return 'RED'
  if (availableMb < RAM_AMBER_MB) return 'AMBER'
  return 'GREEN'
}

export function limitSeverity(usedMb: number, limitMb: number | null): Severity {
  if (limitMb == null || limitMb <= 0) return 'unbounded'
  const pct = (usedMb / limitMb) * 100
  if (pct >= 95) return 'crit'
  if (pct >= 80) return 'warn'
  return 'ok'
}

function num(raw: string | undefined): number | null {
  const n = Number(raw)
  return raw !== undefined && Number.isFinite(n) ? n : null
}

function byName(vector: PromVector): Map<string, number> {
  const out = new Map<string, number>()
  for (const item of vector) {
    const name = item.metric?.name
    const value = num(item.value?.[1])
    if (name && value !== null) out.set(name, (out.get(name) ?? 0) + value)
  }
  return out
}

function scalar(vector: PromVector): number | null {
  return vector.length ? num(vector[0].value?.[1]) : null
}

const round1 = (n: number): number => Math.round(n * 10) / 10

export function buildSnapshot(input: SnapshotInput, now: Date = new Date()): ResourceSnapshot {
  const collectedAt = now.toISOString()
  const workingSet = byName(input.workingSet)
  if (workingSet.size === 0) {
    return { available: false, reason: 'No per-container metrics yet (is docker-stats-exporter running?)', collectedAt }
  }
  const limits = byName(input.limit)
  const cpu = byName(input.cpu)

  const containers: ContainerRow[] = [...workingSet.entries()]
    .map(([name, bytes]) => {
      const workingSetMb = round1(bytes / MB)
      const limitBytes = limits.get(name)
      const limitMb = limitBytes && limitBytes > 0 ? round1(limitBytes / MB) : null
      return {
        name,
        workingSetMb,
        limitMb,
        pctOfLimit: limitMb ? round1((workingSetMb / limitMb) * 100) : null,
        cpuCores: Math.round((cpu.get(name) ?? 0) * 100) / 100,
        severity: limitSeverity(workingSetMb, limitMb),
      }
    })
    .sort((a, b) => b.workingSetMb - a.workingSetMb || a.name.localeCompare(b.name))

  const availBytes = scalar(input.wslAvailable)
  const totalBytes = scalar(input.wslTotal)
  const swapBytes = scalar(input.swapUsed)
  const wsl =
    availBytes !== null && totalBytes !== null
      ? {
          availableMb: Math.round(availBytes / MB),
          totalMb: Math.round(totalBytes / MB),
          swapUsedMb: Math.round((swapBytes ?? 0) / MB),
          verdict: ramVerdict(availBytes / MB),
        }
      : null

  return {
    available: true,
    collectedAt,
    wsl,
    containers,
    totals: {
      count: containers.length,
      workingSetMb: round1(containers.reduce((sum, c) => sum + c.workingSetMb, 0)),
      nearLimit: containers.filter((c) => c.severity === 'warn' || c.severity === 'crit').length,
    },
  }
}
