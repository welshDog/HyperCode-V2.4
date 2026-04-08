/**
 * Feature Flags — ship incremental features safely
 * Extend without touching core layout code
 */

export type FlagName =
  | 'QUANTUM_VIEW'
  | 'MCP_GATEWAY_VIEW'
  | 'HYPERFOCUS_MODE'
  | 'AGENT_DNA_SYSTEM'
  | 'BROSKI_PULSE_V2'
  | 'ACCESSIBILITY_AUDIT'

const ENV_FLAGS: Partial<Record<FlagName, boolean>> = {
  QUANTUM_VIEW:       process.env.NEXT_PUBLIC_FF_QUANTUM_VIEW       === 'true',
  MCP_GATEWAY_VIEW:   process.env.NEXT_PUBLIC_FF_MCP_GATEWAY_VIEW   === 'true',
  HYPERFOCUS_MODE:    process.env.NEXT_PUBLIC_FF_HYPERFOCUS_MODE    === 'true',
  AGENT_DNA_SYSTEM:   process.env.NEXT_PUBLIC_FF_AGENT_DNA_SYSTEM   === 'true',
  BROSKI_PULSE_V2:    process.env.NEXT_PUBLIC_FF_BROSKI_PULSE_V2    === 'true',
  ACCESSIBILITY_AUDIT: process.env.NEXT_PUBLIC_FF_ACCESSIBILITY_AUDIT === 'true',
}

export function isEnabled(flag: FlagName): boolean {
  return ENV_FLAGS[flag] ?? false
}
