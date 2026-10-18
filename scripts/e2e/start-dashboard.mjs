import { spawn, spawnSync } from 'node:child_process'
import path from 'node:path'
import process from 'node:process'

const port = String(process.env.DASHBOARD_PORT ?? '3010')
const repoRoot = path.resolve(process.cwd())
const dashboardDir = path.join(repoRoot, 'agents', 'dashboard')

let child
if (process.env.CI) {
  // CI serves a production build. Under "next dev" the page was not hydrating
  // in the test browser (HMR websocket handshake fails), so anything that needs
  // a React event handler or effect (clicks, the postMessage toast bridge) never
  // ran. A production build has no HMR and hydrates deterministically.
  const build = spawnSync('npx', ['next', 'build'], { cwd: dashboardDir, stdio: 'inherit', shell: true, env: process.env })
  if (build.status !== 0) process.exit(build.status ?? 1)

  child = spawn(process.execPath, [path.join(dashboardDir, 'scripts', 'start-standalone.mjs')], {
    cwd: dashboardDir,
    stdio: 'inherit',
    env: { ...process.env, PORT: port, HOSTNAME: '127.0.0.1' },
  })
} else {
  child = spawn('npx', ['next', 'dev', '-p', port], {
    cwd: dashboardDir,
    stdio: 'inherit',
    shell: true,
    env: process.env,
  })
}

child.on('exit', (code) => {
  process.exit(code ?? 1)
})
