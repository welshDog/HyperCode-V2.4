// Server-only: service identity for Next → core proxy calls.
// The dashboard has no login UI yet, so browser Authorization is always
// empty. When it is, proxies fall back to this service JWT (env or Docker
// secret file). Empty env = feature off, proxies behave exactly as before.
import { readFileSync } from 'fs'

let cached: string | null = null

export function serviceAuthHeader(): string {
  if (cached !== null) return cached
  let token = (process.env.DASHBOARD_SERVICE_JWT ?? '').trim()
  if (!token && process.env.DASHBOARD_SERVICE_JWT_FILE) {
    try {
      token = readFileSync(process.env.DASHBOARD_SERVICE_JWT_FILE, 'utf-8').trim()
    } catch {
      token = ''
    }
  }
  cached = token ? `Bearer ${token}` : ''
  return cached
}
