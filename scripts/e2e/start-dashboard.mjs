import { spawn } from 'node:child_process'
import path from 'node:path'
import process from 'node:process'

const port = String(process.env.DASHBOARD_PORT ?? '3010')
const repoRoot = path.resolve(process.cwd())
const dashboardDir = path.join(repoRoot, 'agents', 'dashboard')

const child = spawn('npx', ['next', 'dev', '-p', port], {
  cwd: dashboardDir,
  stdio: 'inherit',
  shell: true,
  env: process.env,
})

child.on('exit', (code) => {
  process.exit(code ?? 1)
})

