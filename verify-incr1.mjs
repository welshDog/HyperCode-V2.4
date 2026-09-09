// Increment 1 GO/NO-GO probe — runbook §6.
// Screenshot baseline can't answer computed-style / document.fonts.check / woff2-200,
// so this does. Repo-local playwright (1.58.2 -> chromium-1234), NOT `npx playwright`.
//
//   node verify-incr1.mjs pre     # run BEFORE the merge/build (clean HEAD live)
//   node verify-incr1.mjs post    # run AFTER  the dashboard rebuild
//   node diff done by eye or:  node -e "..."  (both files printed at end)
//
// Writes scratchpad/incr1-<label>.json and prints PASS/FAIL for the absolute checks.
import { chromium } from 'playwright';
import { mkdirSync, writeFileSync } from 'node:fs';

const label = process.argv[2] || 'run';
const base = 'http://127.0.0.1:8088';
const outDir = 'scratchpad';
const outFile = `${outDir}/incr1-${label}.json`;
mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
const page = await ctx.newPage();

// Capture every woff2 response status.
const woff2 = [];
page.on('response', (r) => {
  const u = r.url();
  if (u.includes('.woff2')) woff2.push({ url: u.replace(base, ''), status: r.status() });
});

try {
  await page.goto(base + '/ide', { waitUntil: 'networkidle', timeout: 30000 });
} catch { /* live-polling pages never reach networkidle */ }
await page.waitForTimeout(5000);

const measure = () => page.evaluate(() => {
  const g = (el) => (el ? getComputedStyle(el) : null);
  const pane = document.querySelector('.pane');
  const btn = document.querySelector('.btn');
  const pick = (cs, props) => props.reduce((o, p) => ((o[p] = cs ? cs[p] : null), o), {});
  return {
    bodyFontFamily: getComputedStyle(document.body).fontFamily,
    htmlNdMode: document.documentElement.getAttribute('data-nd-mode'),
    fontsCheck: {
      inter: document.fonts.check('16px Inter'),
      spaceGrotesk: document.fonts.check('16px "Space Grotesk"'),
      jetbrainsMono: document.fonts.check('16px "JetBrains Mono"'),
      openDyslexic: document.fonts.check('16px OpenDyslexic'),
    },
    pane: pick(g(pane), ['backgroundColor', 'borderTopColor', 'borderTopWidth', 'borderTopLeftRadius', 'boxShadow', 'color']),
    btn: pick(g(btn), ['backgroundColor', 'borderTopColor', 'borderTopWidth', 'borderTopLeftRadius', 'color']),
    cssChunks: [...document.querySelectorAll('link[rel=stylesheet]')].map((l) => l.getAttribute('href')),
  };
});

const beforeToggle = await measure();

// Flip to dyslexia mode exactly as NDToggle does (sets attr on <html>).
await page.evaluate(() => document.documentElement.setAttribute('data-nd-mode', 'dyslexia'));
await page.waitForTimeout(1200);
const afterToggle = await measure();

await browser.close();

const result = { label, capturedAt: new Date().toISOString(), woff2, beforeToggle, afterToggle };
writeFileSync(outFile, JSON.stringify(result, null, 2));

// ── absolute checks (pass/fail without a baseline) ──
const need = (name, ok) => console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}`);
const w = (re) => woff2.filter((x) => re.test(x.url));
const all200 = (arr) => arr.length > 0 && arr.every((x) => x.status === 200);
console.log(`\n── ${label} — runbook §6 absolute checks ──`);
need('woff2 inter-* → 200', all200(w(/inter-/)));
need('woff2 space-grotesk-* → 200', all200(w(/space-grotesk-/)));
need('woff2 jetbrains-mono-* → 200', all200(w(/jetbrains-mono-/)));
need('body fontFamily starts "Inter" (not system-ui)', /^["']?Inter/.test(beforeToggle.bodyFontFamily));
need('document.fonts.check 16px Inter', beforeToggle.fontsCheck.inter);
need('dyslexia toggle → body fontFamily contains OpenDyslexic', /OpenDyslexic/i.test(afterToggle.bodyFontFamily));
need('document.fonts.check 16px OpenDyslexic (after toggle)', afterToggle.fontsCheck.openDyslexic);
console.log(`\npane/btn computed values → compare scratchpad/incr1-pre.json vs incr1-post.json (must be identical)`);
console.log(`cssChunks: ${JSON.stringify(beforeToggle.cssChunks)}`);
console.log(`woff2 seen: ${woff2.length ? JSON.stringify(woff2) : '(none)'}`);
console.log(`\nwrote ${outFile}`);
