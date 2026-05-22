# HS-048 — Preflight Checks System

> **Extracted from:** `hyperlaunch.py` · HyperCode-V2.4
> **What it is:** The pre-launch validation gate that stops bad launches before they happen

---

## What Gets Checked

| Check | Critical? | What It Validates |
|---|---|---|
| Docker daemon | ✅ Yes | Docker is installed + running |
| Docker Compose | ✅ Yes | `docker compose` command available |
| Compose file | ✅ Yes | At least one compose file exists in CWD |
| `.env` file | ⚠️ No | `.env` present (warns if missing) |
| Required env vars | ✅ Yes | `OPENAI_API_KEY`, `REDIS_URL`, `DATABASE_URL` set |
| Optional env vars | ⚠️ No | `ANTHROPIC_API_KEY`, `OLLAMA_HOST`, `DISCORD_TOKEN` |
| Disk space | ⚠️ No | At least 2 GB free |
| Port scan | ⚠️ No | Reports on critical ports (6379, 5432, 8000, 8080, 8081) |

## The CheckResult Pattern

```python
@dataclass
class CheckResult:
    name: str
    passed: bool
    message: str
    critical: bool = True  # If True + not passed → abort launch
```

## Run In Isolation

```bash
python hyperlaunch.py --dry-run
# Runs all preflight checks + prints plan, launches NOTHING
```

## What Happens On Failure

- **Critical fail** → prints `❌` + message, aborts immediately
- **Non-critical fail** → prints `⚠️` + message, continues
- All passing → prints `✅ Pre-flight complete`, proceeds to tier launch

## Required Env Vars Reference

```bash
# Must be set (critical)
OPENAI_API_KEY=sk-...
REDIS_URL=redis://localhost:6379
DATABASE_URL=postgresql://user:pass@localhost:5432/db

# Optional (warnings only)
ANTHROPIC_API_KEY=sk-ant-...
OLLAMA_HOST=http://localhost:11434
DISCORD_TOKEN=...
```

---

> 🛡️ Preflight = saves you from a broken half-launched stack. Run it. Always.
