// Baseline capture — Increment 0, clean HEAD 2f3e1277.
// Uses the repo-local playwright (1.58.2 -> chromium-1234), NOT `npx playwright`
// (which resolved an unmatched older build). Run: node capture-baseline-incr0.mjs
import { chromium } from 'playwright';
import { mkdirSync, writeFileSync, statSync } from 'node:fs';
import { execSync } from 'node:child_process';

const base = 'http://127.0.0.1:8088';
const out = 'docs/reports/baseline-incr0';
const viewport = { width: 1440, height: 900 };
const routes = [
  ['/', 'home'], ['/ide', 'ide'], ['/agents', 'agents'], ['/mission', 'mission'],
  ['/control', 'control'], ['/flows', 'flows'], ['/mcp', 'mcp'],
  ['/docker-zone', 'docker-zone'], ['/health', 'health'], ['/grafana', 'grafana'],
];

mkdirSync(out, { recursive: true });
const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport, deviceScaleFactor: 1 });
const page = await ctx.newPage();
const failed = [];

for (const [path, name] of routes) {
  const file = `${out}/${name}.png`;
  try {
    await page.goto(base + path, { waitUntil: 'networkidle', timeout: 30000 });
  } catch { /* networkidle can never settle on live-polling pages; fall through */ }
  await page.waitForTimeout(5000); // let fleet / safety feed / docker-zone iframe settle
  // App shell is fixed 100vh, overflow:hidden — a viewport shot is the whole page.
  await page.screenshot({ path: file, fullPage: false });
  try {
    const sz = statSync(file).size;
    console.log(`ok  ${name.padEnd(12)} ${sz} bytes`);
    if (sz < 2000) failed.push(name);
  } catch { failed.push(name); console.log(`FAIL ${name}`); }
}

await browser.close();

if (failed.length) {
  console.error(`\nFAILED: ${failed.join(', ')}`);
  process.exit(1);
}

const meta = `# Baseline capture metadata
- Captured: ${new Date().toISOString()}
- Deployed image: a0f531ac9708 (clean HEAD 2f3e1277)
- Viewport: 1440x900, deviceScaleFactor 1, fullPage:false (app shell is fixed 100vh)
- CSS chunk: 0.8ppsn43~8wl.css
- Webfonts loaded: none (see MEASURED_BASELINE.md)
- Tool: repo-local playwright ${execSync('node -e "process.stdout.write(require(\'playwright/package.json\').version)"').toString()} (chromium)
- Note: live panels (clocks, uptime, safety-feed timestamps) differ run-to-run;
  the Increment 1 check is human-reviewed + computed-style, not pixel-diff.
`;
writeFileSync(`${out}/CAPTURE_METADATA.md`, meta);
console.log(`\nAll 10 pages captured to ${out} — baseline locked.`);
