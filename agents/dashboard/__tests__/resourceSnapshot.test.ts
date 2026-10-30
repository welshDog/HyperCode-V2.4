import { describe, expect, it } from 'vitest'
import { buildSnapshot, limitSeverity, ramVerdict, type PromVector } from '../lib/resourceSnapshot'

const MB = 1024 * 1024
const vec = (rows: Array<[string, number]>): PromVector =>
  rows.map(([name, v]) => ({ metric: { name }, value: [0, String(v)] as [number, string] }))
const scalar = (v: number): PromVector => [{ metric: {}, value: [0, String(v)] }]

describe('ramVerdict (mirrors scripts/ram_guard.py)', () => {
  it.each([
    [1199, 'RED'],
    [1200, 'AMBER'],
    [1499, 'AMBER'],
    [1500, 'GREEN'],
    [4000, 'GREEN'],
  ])('%i MB -> %s', (mb, verdict) => expect(ramVerdict(mb)).toBe(verdict))

  it.each([null, undefined, NaN])('treats %s as UNKNOWN, never GREEN', (v) => {
    expect(ramVerdict(v as number | null)).toBe('UNKNOWN')
  })
})

describe('limitSeverity', () => {
  it('flags 80% as high and 95% as critical', () => {
    expect(limitSeverity(79, 100)).toBe('ok')
    expect(limitSeverity(80, 100)).toBe('warn')
    expect(limitSeverity(94.9, 100)).toBe('warn')
    expect(limitSeverity(95, 100)).toBe('crit')
  })
  it('reports containers without a limit as unbounded', () => {
    expect(limitSeverity(500, null)).toBe('unbounded')
    expect(limitSeverity(500, 0)).toBe('unbounded')
  })
})

describe('buildSnapshot', () => {
  const input = {
    workingSet: vec([['small', 10 * MB], ['big', 450 * MB], ['mid', 100 * MB]]),
    limit: vec([['small', 256 * MB], ['big', 512 * MB], ['mid', 0]]),
    cpu: vec([['big', 0.456]]),
    wslAvailable: scalar(1232 * MB),
    wslTotal: scalar(3917 * MB),
    swapUsed: scalar(1100 * MB),
  }
  const snap = buildSnapshot(input, new Date('2026-10-30T18:00:00Z'))

  it('sorts by memory, biggest first, and computes percentages', () => {
    if (!snap.available) throw new Error('expected data')
    expect(snap.containers.map((c) => c.name)).toEqual(['big', 'mid', 'small'])
    expect(snap.containers[0]).toMatchObject({ workingSetMb: 450, limitMb: 512, pctOfLimit: 87.9, severity: 'warn', cpuCores: 0.46 })
    expect(snap.containers[1]).toMatchObject({ limitMb: null, pctOfLimit: null, severity: 'unbounded' })
  })

  it('totals memory and counts containers near their limit', () => {
    if (!snap.available) throw new Error('expected data')
    expect(snap.totals).toEqual({ count: 3, workingSetMb: 560, nearLimit: 1 })
  })

  it('reports WSL with a verdict', () => {
    if (!snap.available) throw new Error('expected data')
    expect(snap.wsl).toEqual({ availableMb: 1232, totalMb: 3917, swapUsedMb: 1100, verdict: 'AMBER' })
  })

  it('has no WSL block when node-exporter data is missing', () => {
    const s = buildSnapshot({ ...input, wslAvailable: [], wslTotal: [] })
    expect(s.available && s.wsl).toBeNull()
  })

  it('says why when there is no container data, instead of showing zeros', () => {
    const s = buildSnapshot({ ...input, workingSet: [] })
    expect(s).toMatchObject({ available: false })
    expect(s.available === false && s.reason).toMatch(/docker-stats-exporter/)
  })

  it('ignores junk values and unnamed series', () => {
    const s = buildSnapshot({
      ...input,
      workingSet: [...input.workingSet, { metric: {}, value: [0, '5'] }, { metric: { name: 'bad' }, value: [0, 'NaN'] }],
    })
    expect(s.available && s.containers.map((c) => c.name)).toEqual(['big', 'mid', 'small'])
  })
})
