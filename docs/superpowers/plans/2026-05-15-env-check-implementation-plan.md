# Env Check Script (Command-Based) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `scripts/env-check.sh` that validates required `.env` keys and `secrets/*.txt` files for the exact compose files/profiles the operator is about to run, printing keys only (never values).

**Architecture:** A Bash entrypoint does CLI parsing and dispatches to an embedded Python helper that parses `.env`, scans compose files for `${VARS}` references, and scans `docker-compose.secrets.yml` for referenced secret files. Output is key/path oriented with clear error/warn summary and non-zero exit code on errors.

**Tech Stack:** Bash, Python 3 (embedded), Docker Compose file scanning (regex line scan).

---

## File Map

**Create**
- `h:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4/scripts/env-check.sh`
- `h:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4/docs/superpowers/plans/2026-05-15-env-check-implementation-plan.md` (this file)

**Modify**
- None required by spec.

**Reference**
- `h:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4/docs/superpowers/specs/2026-05-15-env-check-design.md`
- `h:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4/docker-compose.secrets.yml`

---

### Task 1: Create `scripts/env-check.sh` skeleton + CLI parsing

**Files:**
- Create: `h:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4/scripts/env-check.sh`

- [ ] **Step 1: Create the script with usage + argument parsing (no logic yet)**

Create:

```bash
#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  bash scripts/env-check.sh [--files <compose...>] [--profile <name>...]
  bash scripts/env-check.sh [--core] [--secrets] [--brain] [--grafana-cloud] [--profile <name>...]

Defaults:
  If no --files and no convenience flags are provided, defaults to docker-compose.yml.
USAGE
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
declare -a FILES=()
declare -a PROFILES=()

FLAG_CORE=false
FLAG_SECRETS=false
FLAG_BRAIN=false
FLAG_GRAFANA_CLOUD=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h) usage; exit 0 ;;
    --files)
      shift
      while [[ $# -gt 0 && "${1:-}" != --* ]]; do
        FILES+=("$1")
        shift
      done
      ;;
    --profile)
      shift
      PROFILES+=("${1:-}")
      shift
      ;;
    --core) FLAG_CORE=true; shift ;;
    --secrets) FLAG_SECRETS=true; shift ;;
    --brain) FLAG_BRAIN=true; shift ;;
    --grafana-cloud) FLAG_GRAFANA_CLOUD=true; shift ;;
    *)
      echo "Unknown arg: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ ${#FILES[@]} -eq 0 ]]; then
  if [[ "$FLAG_CORE" == "true" ]]; then FILES+=("docker-compose.yml"); fi
  if [[ "$FLAG_SECRETS" == "true" ]]; then FILES+=("docker-compose.secrets.yml"); fi
  if [[ "$FLAG_BRAIN" == "true" ]]; then FILES+=("docker-compose.brain.yml"); fi
  if [[ "$FLAG_GRAFANA_CLOUD" == "true" ]]; then FILES+=("docker-compose.grafana-cloud.yml"); fi
fi

if [[ ${#FILES[@]} -eq 0 ]]; then
  FILES=("docker-compose.yml")
fi

python - <<'PY'
raise SystemExit("not implemented")
PY
```

- [ ] **Step 2: Run it to confirm it executes and shows “not implemented”**

Run (from repo root):

```bash
bash scripts/env-check.sh --core
```

Expected: exits non-zero with `not implemented`.

- [ ] **Step 3: Commit**

```bash
git add scripts/env-check.sh
git commit -m "feat: add env-check.sh skeleton"
```

---

### Task 2: Implement `.env` parsing + duplicate detection (keys-only)

**Files:**
- Modify: `h:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4/scripts/env-check.sh`

- [ ] **Step 1: Replace the Python placeholder with helper functions**

Replace the embedded Python section with code that:

- Loads root `.env` (`$ROOT_DIR/.env`)
- Parses `KEY=VALUE` lines (ignore blank/comments, tolerate `export `)
- Returns:
  - `env_keys` set
  - `duplicates` list
  - `empty_keys` list (value empty string)

Use this Python snippet (keys-only output):

```python
import os
import sys
from collections import Counter

root_dir = os.environ["ENV_CHECK_ROOT"]
env_path = os.path.join(root_dir, ".env")

def parse_env(path: str):
    entries = []
    if not os.path.exists(path):
        return entries
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            if s.startswith("export "):
                s = s[len("export "):]
            if "=" not in s:
                continue
            k, v = s.split("=", 1)
            entries.append((k.strip(), v.strip()))
    return entries

entries = parse_env(env_path)
keys = [k for k, _ in entries]
dup_keys = sorted([k for k, c in Counter(keys).items() if c > 1])
env_kv = {}
for k, v in entries:
    env_kv[k] = v
env_keys = set(env_kv.keys())
empty_keys = sorted([k for k, v in env_kv.items() if v == ""])

errors = []
warnings = []

if not os.path.exists(env_path):
    errors.append(f"missing_root_env:{env_path}")

for k in dup_keys:
    warnings.append(f"duplicate_key:{k}")

print("Env Check — keys only")
print(f"Root: {root_dir}")
print("")

if errors:
    print("ERRORS:")
    for e in errors:
        print(f"- {e}")

if warnings:
    print("WARNINGS:")
    for w in warnings:
        print(f"- {w}")

sys.exit(1 if errors else 0)
```

Wire `ENV_CHECK_ROOT` from Bash:

```bash
ENV_CHECK_ROOT="$ROOT_DIR" python - <<'PY'
...
PY
```

- [ ] **Step 2: Run and verify**

Run:

```bash
bash scripts/env-check.sh --core
```

Expected:
- If `.env` exists: exit `0`, warnings may include duplicates (keys only).
- If `.env` missing: exit non-zero with missing path error.

- [ ] **Step 3: Commit**

```bash
git add scripts/env-check.sh
git commit -m "feat: parse .env and report duplicate keys"
```

---

### Task 3: Extract `${VARS}` from selected compose files and validate required/optional vars

**Files:**
- Modify: `h:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4/scripts/env-check.sh`

- [ ] **Step 1: Pass selected compose files + profiles into Python**

In Bash, export:

```bash
ENV_CHECK_ROOT="$ROOT_DIR" \
ENV_CHECK_FILES="$(IFS=$'\n'; echo "${FILES[*]}")" \
ENV_CHECK_PROFILES="$(IFS=$'\n'; echo "${PROFILES[*]:-}")" \
python - <<'PY'
...
PY
```

- [ ] **Step 2: Implement compose scanning**

Implement a regex scan for `${NAME}`, `${NAME:-default}`, `${NAME:?msg}`:

```python
import re
var_re = re.compile(r"\$\{([A-Z0-9_]+)(?::([?\-])([^}]*))?\}")
```

Classification rules:
- If any occurrence is required (`mod` not `-`), treat as required.
- Otherwise optional.

For each selected compose file:
- Ensure the file exists (error if missing).
- Record which vars are referenced and whether they are required/optional.

Validation:
- Error: required var missing from root `.env`.
- Warning: optional var missing from root `.env`.

- [ ] **Step 3: Run and verify**

Run:

```bash
bash scripts/env-check.sh --files docker-compose.yml
```

Expected:
- No secret values printed.
- A summary of missing required vars for the chosen file set (if any).

- [ ] **Step 4: Commit**

```bash
git add scripts/env-check.sh
git commit -m "feat: validate compose env vars against root .env"
```

---

### Task 4: Secrets checks when `docker-compose.secrets.yml` is selected

**Files:**
- Modify: `h:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4/scripts/env-check.sh`

- [ ] **Step 1: Detect whether secrets compose is included**

In Python, treat secrets mode as enabled when any selected compose file basename equals `docker-compose.secrets.yml`.

- [ ] **Step 2: Parse `secrets:` block and check each `file:`**

Perform a line-oriented scan:
- When inside `secrets:` section at indent 0:
  - Track secret name and its `file: <path>` field.
- For each `file:` path:
  - Resolve relative to repo root.
  - Error if missing or empty.
  - Warn if content matches placeholder patterns (do not print content).

Placeholder patterns (case-insensitive substring match):
- `PASTE_`, `YOUR_`, `CHANGEME`, `your_`, `paste_`

- [ ] **Step 3: Run and verify**

Run:

```bash
bash scripts/env-check.sh --core --secrets
```

Expected:
- If secret files exist: no missing-file errors.
- If placeholder secrets exist: warnings only (keys + paths only).

- [ ] **Step 4: Commit**

```bash
git add scripts/env-check.sh
git commit -m "feat: validate docker secrets files without leaking values"
```

---

### Task 5: Profile-aware broski-bot `.env` checks for `--profile discord`

**Files:**
- Modify: `h:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4/scripts/env-check.sh`
- Reference: `h:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4/agents/broski-bot/.env.example`

- [ ] **Step 1: Detect discord profile**

In Python, treat `discord` as enabled when any provided profile equals `discord`.

- [ ] **Step 2: Validate `agents/broski-bot/.env` keys vs `.env.example`**

Rules:
- Error if `agents/broski-bot/.env` missing.
- Compare keys:
  - Error for missing keys from `.env.example`.
  - If secrets mode enabled: allow missing `DISCORD_TOKEN` in the bot `.env` (entrypoint can load from secrets).

- [ ] **Step 3: Run and verify**

Run:

```bash
bash scripts/env-check.sh --core --secrets --profile discord
```

Expected:
- Keys-only output.
- Missing keys in `agents/broski-bot/.env` are listed by name (no values).

- [ ] **Step 4: Commit**

```bash
git add scripts/env-check.sh
git commit -m "feat: add profile-aware broski-bot env checks"
```

---

### Task 6: Final polish (output format + exit codes) + verification

**Files:**
- Modify: `h:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4/scripts/env-check.sh`

- [ ] **Step 1: Standardize output sections**

Ensure output includes:
- Selected files list (basenames)
- Selected profiles list
- Errors section (if any)
- Warnings section (if any)
- Summary counts

- [ ] **Step 2: Exit code correctness**

- Exit non-zero if any errors exist.
- Exit `0` when errors empty (even if warnings exist).

- [ ] **Step 3: Run quick matrix**

Run:

```bash
bash scripts/env-check.sh --core
bash scripts/env-check.sh --core --secrets
bash scripts/env-check.sh --files docker-compose.yml docker-compose.secrets.yml docker-compose.brain.yml --profile discord
```

Expected:
- No secret values printed.
- Correct detection of missing keys / missing secret files based on selected mode.

- [ ] **Step 4: Commit**

```bash
git add scripts/env-check.sh
git commit -m "chore: finalize env-check output and exit codes"
```

---

## Plan Self-Review

- Spec coverage: Tasks 1–6 cover CLI inputs, `.env` parsing, compose scanning, secrets checks, profile-aware checks, output requirements.
- Placeholder scan: No TBD/TODO markers.
- Type consistency: Single script, consistent env var names for passing arguments.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-15-env-check-implementation-plan.md`.

Two execution options:

1. Subagent-Driven (recommended) — I dispatch a fresh subagent per task, review between tasks, fast iteration
2. Inline Execution — Execute tasks in this session, batch execution with checkpoints

Which approach?
