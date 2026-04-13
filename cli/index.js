#!/usr/bin/env node
/**
 * HyperCode CLI
 * Usage:
 *   node cli/index.js logs [--tail N] [--level info|warn|error|success] [--agent NAME]
 *   node cli/index.js health
 *
 * Requires Node 18+ (built-in fetch). No npm install needed.
 */

const BASE_URL = process.env.HYPERCODE_API_URL || 'http://localhost:8000';

// ── Argument parsing ───────────────────────────────────────────────────────────
const argv = process.argv.slice(2);
const command = argv[0];
const flags = {};
for (let i = 1; i < argv.length; i++) {
  if (argv[i].startsWith('--')) {
    const key = argv[i].slice(2);
    const next = argv[i + 1];
    if (next && !next.startsWith('--')) {
      flags[key] = next;
      i++;
    } else {
      flags[key] = true;
    }
  }
}

// ── ANSI colours ──────────────────────────────────────────────────────────────
const C = {
  reset:   '\x1b[0m',
  bold:    '\x1b[1m',
  dim:     '\x1b[2m',
  red:     '\x1b[31m',
  yellow:  '\x1b[33m',
  cyan:    '\x1b[36m',
  green:   '\x1b[32m',
  magenta: '\x1b[35m',
  white:   '\x1b[37m',
};

const LEVEL_COLOR = {
  error:   C.red,
  warn:    C.yellow,
  warning: C.yellow,
  info:    C.cyan,
  success: C.green,
  debug:   C.dim,
};

function levelColor(lvl) {
  return LEVEL_COLOR[(lvl || 'info').toLowerCase()] || C.white;
}

// ── Commands ───────────────────────────────────────────────────────────────────

async function cmdLogs() {
  const limit = flags.tail || flags.limit || 20;
  const params = new URLSearchParams({ limit: String(limit) });
  if (flags.level) params.set('level', flags.level);
  if (flags.agent) params.set('agent', flags.agent);

  let res;
  try {
    res = await fetch(`${BASE_URL}/api/v1/logs?${params}`);
  } catch (e) {
    console.error(`${C.red}Cannot reach ${BASE_URL} — is hypercode-core running?${C.reset}`);
    process.exit(1);
  }

  if (!res.ok) {
    console.error(`${C.red}HTTP ${res.status} ${res.statusText}${C.reset}`);
    process.exit(1);
  }

  const data = await res.json();
  const logs = Array.isArray(data) ? data : (data.logs || []);

  if (!logs.length) {
    console.log(`${C.dim}(no entries yet — make some requests to generate log data)${C.reset}`);
    return;
  }

  console.log(`\n${C.bold}  HyperCode Logs  ${C.dim}(${logs.length} entries)${C.reset}\n`);

  for (const entry of logs) {
    const col   = levelColor(entry.level);
    const time  = (entry.time || entry.timestamp || '').slice(0, 19).replace('T', ' ');
    const level = (entry.level || 'info').toUpperCase().padEnd(7);
    const agent = (entry.agent || 'system').padEnd(18).slice(0, 18);
    const msg   = entry.msg || entry.message || '';
    console.log(`  ${C.dim}${time}${C.reset}  ${col}${level}${C.reset}  ${C.magenta}${agent}${C.reset}  ${msg}`);
  }
  console.log();
}

async function cmdHealth() {
  let res;
  try {
    res = await fetch(`${BASE_URL}/health`);
  } catch (e) {
    console.error(`${C.red}Cannot reach ${BASE_URL}${C.reset}`);
    process.exit(1);
  }
  const data = await res.json();
  const ok = data.status === 'ok';
  const icon = ok ? `${C.green}✔${C.reset}` : `${C.red}✘${C.reset}`;
  console.log(`${icon}  ${data.service || 'api'}  v${data.version || '?'}  [${data.environment || '?'}]`);
  if (!ok) process.exit(1);
}

function cmdHelp() {
  console.log(`
${C.bold}HyperCode CLI${C.reset}

Usage:
  node cli/index.js <command> [options]

Commands:
  ${C.cyan}logs${C.reset}      Show recent log entries from hypercode-core
  ${C.cyan}health${C.reset}    Check hypercode-core health

Options for ${C.cyan}logs${C.reset}:
  --tail N          Show last N entries  (default: 20)
  --limit N         Alias for --tail
  --level LEVEL     Filter by level: info | warn | error | success
  --agent NAME      Filter by agent name (substring match)

Examples:
  node cli/index.js logs --tail 10
  node cli/index.js logs --level error
  node cli/index.js logs --agent hypercode-core --tail 50
  node cli/index.js health
`);
}

// ── Entry point ────────────────────────────────────────────────────────────────
async function main() {
  switch (command) {
    case 'logs':   await cmdLogs();   break;
    case 'health': await cmdHealth(); break;
    default:       cmdHelp();
  }
}

main().catch(e => {
  console.error(`${C.red}${e.message}${C.reset}`);
  process.exit(1);
});
