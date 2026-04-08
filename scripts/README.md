# Scripts

Operational and developer utility scripts for HyperCode (PowerShell-first on Windows, shell scripts where appropriate).

## Entry Points

- Boot (profiles): `scripts/boot.ps1`
- Dev up: `scripts/dev-up.ps1`
- Health checks: `scripts/health-check.ps1`, `scripts/comprehensive_health_check.py`, `scripts/hypercode_health_check.py`
- Init/secrets: `scripts/init.ps1`, `scripts/init-secrets.ps1`, `scripts/setup-secrets.ps1`, `scripts/validate_secrets.ps1`
- Backups: `scripts/backup.ps1`, `scripts/backup_postgres.*`, `scripts/backup_volumes.*`, `scripts/backup_hypercode.*`

## Subfolders

- `deployment/` deployment helpers
- `maintenance/` cleanup and quick-fix scripts
- `monitoring/` Grafana/Prometheus helpers
- `nemoclaw/` NIM gateway onboarding, validation, and diagnostics

## Conventions

- Prefer `*.ps1` on Windows; use `*.sh` for Linux/macOS environments and containers.
- Treat anything touching secrets, SSL, or `.env` as sensitive and keep it out of git history.

