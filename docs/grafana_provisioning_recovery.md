# Grafana Provisioning Loop Recovery (SQLite grafana.db)

## Symptoms

- Grafana container shows `health: starting` forever or keeps restarting.
- Logs include errors like:
  - `UNIQUE constraint failed: alert_rule_version.rule_guid, alert_rule_version.version`
  - `UNIQUE constraint failed: alert_rule.guid`
  - `attempt to write a readonly database`

## Root Causes Seen in HyperCode

- SQLite state drift in `grafana.db` causes provisioning to re-apply resources into an inconsistent DB state.
- Partial provisioning + restart loops can leave alerting tables inconsistent (for example, versions without matching rules).
- File ownership/permissions on `/var/lib/grafana/grafana.db` can make SQLite appear read-only to the Grafana process.

## Safety: Backup + Rollback

### Backup grafana.db (recommended before any fix)

```powershell
docker compose stop grafana

$ts = Get-Date -Format "yyyyMMdd-HHmmss"
$dir = "reports\\grafana\\backup\\$ts"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
docker cp grafana:/var/lib/grafana/grafana.db "$dir\\grafana.db"
```

### Rollback (restore a backup)

```powershell
docker compose stop grafana
docker cp "reports\\grafana\\backup\\<TIMESTAMP>\\grafana.db" grafana:/var/lib/grafana/grafana.db
docker compose up -d grafana
```

## Diagnostic Checklist

### 1) Confirm it is a restart loop

```powershell
docker ps --filter "name=^/grafana$" --format "{{.Names}}  {{.Status}}"
docker inspect -f "{{.RestartCount}}" grafana
docker logs --tail 200 grafana
```

### 2) Confirm the provisioning inputs are sane

```powershell
python scripts/maintenance/grafana_provisioning_doctor.py
```

If it reports duplicates and you want an automated rename:

```powershell
python scripts/maintenance/grafana_provisioning_doctor.py --fix
```

### 3) Optional: Offline SQLite health check

If you copied `grafana.db` out to disk, you can run:

```powershell
python scripts/maintenance/grafana_db_doctor.py --db "reports\\grafana\\backup\\<TIMESTAMP>\\grafana.db"
```

## Remediation Options

### Option A (fastest + most reliable): Regenerate grafana.db

This keeps your provisioning (datasources/dashboards/alerting) as the source of truth and avoids fighting corrupted SQLite state.

```powershell
docker compose stop grafana

$ts = Get-Date -Format "yyyyMMdd-HHmmss"
docker run --rm -v hypercode-v24_grafana-data:/var/lib/grafana alpine:3.20 sh -c "set -e; cd /var/lib/grafana; if [ -f grafana.db ]; then cp -f grafana.db grafana.db.backup-$ts; fi; rm -f grafana.db grafana.db-wal grafana.db-shm"

docker compose up -d grafana
```

Validate:

```powershell
docker ps --filter "name=^/grafana$" --format "{{.Names}}  {{.Status}}"
curl.exe -sS http://localhost:3001/api/health
```

### Option B (surgical): Repair alerting tables only

Use this if you must preserve local Grafana users/config but want to reset alerting state.

1) Backup the DB.
2) Copy DB out and inspect with SQLite (Python sqlite3) for:
   - `alert_rule.guid == ''`
   - `alert_rule_version.rule_guid == ''`
   - versions that have no matching rule record
3) If state is inconsistent, wipe only `alert%` tables and restart Grafana so provisioning recreates alerting.

## Preventing Future Duplicates

- Keep alert rule `uid:` values unique across `monitoring/grafana/provisioning/alerting/alert-rules.yaml`.
- Run the provisioning doctor script whenever alert rules are edited.

## Provisioning Loop Detection (Monitoring)

- Prometheus alert rule added: `GrafanaRestartLoop` based on cAdvisor container start-time changes.
- If it fires, check Grafana logs immediately and use Option A (DB regeneration) for the quickest recovery.

## Performance Impact Notes

- Option A recreates SQLite metadata and re-provisions dashboards/datasources/alerting. This is typically a short spike during startup.
- Option B is less disruptive but still requires a restart and re-provisioning of alerting resources.

## Staging Test Approach (recommended before production)

Run a disposable Grafana with a fresh volume + the same provisioning directory:

```powershell
docker volume rm grafana-staging-data 2>$null
docker volume create grafana-staging-data | Out-Null

docker run -d --name grafana-staging `
  -p 127.0.0.1:13001:3000 `
  -e GF_SECURITY_ADMIN_USER=admin `
  -e GF_SECURITY_ADMIN_PASSWORD=admin `
  -e GF_USERS_ALLOW_SIGN_UP=false `
  -v grafana-staging-data:/var/lib/grafana `
  -v "H:\\HyperStation zone\\HyperCode\\HyperCode-V2.4\\monitoring\\grafana\\provisioning:/etc/grafana/provisioning" `
  grafana/grafana:11.2.0

Start-Sleep -Seconds 20
curl.exe -sS http://localhost:13001/api/health
docker rm -f grafana-staging
docker volume rm grafana-staging-data
```

## Security Note

If alerting contact points include external webhook URLs, store them via environment variables or secrets rather than hardcoding them in provisioning files.
