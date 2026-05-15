# Env Check Script (Command-Based) — Design

## Goal

Provide a safe, local preflight checker that validates environment configuration for the exact Docker Compose invocation the operator is about to run.

The checker must:

- Print keys only (never print secret values).
- Catch missing required variables and missing secret files before boot.
- Be usable on Windows (PowerShell + Git Bash/WSL) and Linux/macOS.

## Non-Goals

- Replacing Docker Compose validation.
- Validating third-party key correctness (only presence, basic format, and placeholder detection).
- Modifying `.env` or secret files automatically.

## Location

- Script: `scripts/env-check.sh`
- Spec: `docs/superpowers/specs/2026-05-15-env-check-design.md`

## Inputs

### Invocation Style

The script supports two equivalent input styles:

1. **Explicit files (recommended for accuracy)**
   - `--files <compose...>`: a list of compose files to scan for `${VARS}`.
   - Optional: `--profile <name>` (repeatable).

2. **Convenience flags (mapped to known files)**
   - `--core` → `docker-compose.yml`
   - `--secrets` → `docker-compose.secrets.yml`
   - `--brain` → `docker-compose.brain.yml`
   - `--grafana-cloud` → `docker-compose.grafana-cloud.yml`
   - Optional: `--profile <name>` (repeatable).

If neither `--files` nor any convenience flags are provided, default to `docker-compose.yml`.

### Sources to Validate

- Root `.env` at repo root (required).
- Optional service env files depending on selected profiles and compose references:
  - `agents/broski-bot/.env` when `--profile discord` is active or when a compose file references it.
- Secret files when `docker-compose.secrets.yml` is selected.

## Output Requirements

- Exit code:
  - `0` when no errors were found.
  - Non-zero when errors were found.
- Logging:
  - Show a summary section with counts: errors and warnings.
  - Show keys and paths only.
  - Never print values read from `.env` or secret files.

## Validation Rules

### `.env` Parsing

- Parse lines of the form `KEY=VALUE` (ignore comments and blank lines).
- Detect duplicate keys; report duplicates as warnings.
- Detect empty values for selected keys; report as errors for required keys and warnings for optional keys.

### Compose Variable Extraction

For the selected compose files:

- Extract variable references of the form `${NAME}`, `${NAME:-default}`, `${NAME:?message}`.
- Classification:
  - `required` when referenced as `${NAME}` or `${NAME:?message}` and no default is present.
  - `optional` when referenced as `${NAME:-default}`.
  - If a variable appears as both required and optional across files, treat as required.

### Missing Vars

- Error when a required compose var is not present in root `.env`.
- Warning when an optional compose var is not present in root `.env`.

### Profile-Aware Checks

- When `--profile discord` is set:
  - Ensure `agents/broski-bot/.env` exists.
  - Ensure the keys from `agents/broski-bot/.env.example` are present in `agents/broski-bot/.env`.
  - If `docker-compose.secrets.yml` is included, treat `DISCORD_TOKEN` in `agents/broski-bot/.env` as optional (since it can be sourced from `/run/secrets/discord_token`).

### Secrets File Checks

When `docker-compose.secrets.yml` is included:

- For each secret defined under `secrets: <name>: file: <path>`:
  - Ensure the file exists.
  - Ensure the file is non-empty.
  - Detect obvious placeholders by matching common patterns (e.g., `PASTE_`, `YOUR_`, `CHANGEME`, `your_`); report placeholder detection as warnings.

## CLI Examples

```bash
# Equivalent to: docker compose -f docker-compose.yml up -d
bash scripts/env-check.sh --core

# Equivalent to: docker compose -f docker-compose.yml -f docker-compose.secrets.yml --profile discord up -d
bash scripts/env-check.sh --core --secrets --profile discord

# Fully explicit
bash scripts/env-check.sh --files docker-compose.yml docker-compose.secrets.yml docker-compose.brain.yml --profile discord
```

## Implementation Notes

- Use a Bash entrypoint for cross-platform portability and a small Python helper for robust parsing:
  - `scripts/env-check.sh` (Bash wrapper)
  - `scripts/env_check.py` (implementation)
  - Read `.env` keys and duplicates.
  - Extract `${VARS}` from compose YAML with a regex scan (line-oriented; no YAML evaluation).
  - Parse secrets from `docker-compose.secrets.yml` using line-oriented matching of `secrets:` blocks and `file:` fields.
- The script must tolerate CRLF line endings.

## Success Criteria

- Running the script before compose provides actionable missing-key and missing-file errors without leaking secrets.
- The script can be used as a guard in docs/runbooks before boot commands.
