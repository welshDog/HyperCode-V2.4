// Increment 1 — Studio model-picker Layer 1 checks (runbook §6, items 6-9).
// Companion to verify-incr1.mjs. Repo-local playwright, NOT `npx playwright`.
//   node verify-incr1-picker.mjs
import { chromium } from 'playwright';

const base = 'http://127.0.0.1:8088';
const b = await chromium.launch();
const p = await (await b.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
try { await p.goto(base + '/ide', { waitUntil: 'networkidle', timeout: 30000 }); } catch {}
await p.waitForTimeout(5000);

const r = await p.evaluate(() => {
  const sel = document.querySelector('select');
  if (!sel) return { error: 'no <select> on /ide' };
  const groups = [...sel.querySelectorAll('optgroup')].map((g) => ({
    label: g.label,
    options: [...g.querySelectorAll('option')].map((o) => ({ text: o.textContent.trim(), value: o.value, disabled: o.disabled })),
  }));
  const helper = sel.closest('label')?.querySelector('span:last-child')?.textContent?.trim();
  const cs = getComputedStyle(document.documentElement);
  const vars = ['--font-mono', '--pane-border', '--pane-bg', '--text-primary', '--font-display']
    .reduce((o, v) => ((o[v] = cs.getPropertyValue(v).trim()), o), {});
  return { defaultValue: sel.value, groups, helper, vars };
});
await b.close();

if (r.error) { console.error('FAIL  ' + r.error); process.exit(1); }
const need = (n, ok) => console.log(`${ok ? 'PASS' : 'FAIL'}  ${n}`);
const cloud = r.groups.find((g) => /^Cloud/.test(g.label));
const free = r.groups.find((g) => /Free \/ Local/.test(g.label));

console.log('── model-picker Layer 1 (runbook §6.6–§6.8) ──');
need('two groups: "Cloud — Claude" + "Free / Local — needs FCC proxy (coming soon)"',
  cloud?.label === 'Cloud — Claude' && free?.label === 'Free / Local — needs FCC proxy (coming soon)');
need('4 Cloud options, all enabled', cloud?.options.length === 4 && cloud.options.every((o) => !o.disabled));
need('Free options present + all disabled (Nemotron 3 Super 120B, Qwen3 4B)',
  free?.options.length === 2 && free.options.every((o) => o.disabled) &&
  /Nemotron 3 Super 120B/.test(free.options[0].text) && /Qwen3 4B/.test(free.options[1].text));
need('default = claude-sonnet-5 (Sonnet 5)', r.defaultValue === 'claude-sonnet-5');
need('helper line mentions "uses credits" + "wiring in progress"',
  /uses credits/.test(r.helper) && /wiring in progress/.test(r.helper));
need('design-system tokens resolve (--pane-bg #0f1420, --pane-border #1e2a3a)',
  r.vars['--pane-bg'] === '#0f1420' && r.vars['--pane-border'] === '#1e2a3a');
console.log('\nhelper: ' + r.helper);
console.log('vars  : ' + JSON.stringify(r.vars));
console.log('\n§6.9 (Cloud run → RunHeader "Sonnet 5"): needs ANTHROPIC_API_KEY in .env — run-submit');
console.log('      proxy hop is verified (POST /api/studio/sessions → 200, id returned); modelLabel unit-tested.');
