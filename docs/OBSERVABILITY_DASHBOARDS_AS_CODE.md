# Dashboards-as-Code (Grafana OSS)

## Goal

Make Grafana dashboards reproducible, reviewable, and rollbackable by keeping their JSON in Git and provisioning them into Grafana on startup.

## Source of Truth

- Dashboard JSON files live in `monitoring/grafana/provisioning/dashboards/*.json`
- The provisioning provider lives in `monitoring/grafana/provisioning/dashboards/dashboard.yml`

Provisioned dashboards currently land in the Grafana folder:

- `Mission Control`

## How Provisioning Works

- Grafana reads the provisioning directory on startup and loads the JSON dashboards into the configured folder.
- The provider is configured with `editable: true`, so dashboards can be edited in the UI.
- UI edits are stored in Grafana’s database (`grafana.db`) and do not automatically write back to the JSON files in the repo.

This means “editable” is convenient, but you must export + commit changes to avoid drift.

## Workflow: Edit Safely Without Drift

### Option A (recommended): Edit in UI → Export JSON → Commit

1. Edit the dashboard in Grafana UI.
2. Export JSON from the dashboard:
   - Dashboard → Share → Export → “Save to file”
3. Overwrite the matching file in:
   - `monitoring/grafana/provisioning/dashboards/`
4. Restart Grafana to ensure provisioning matches Git:
   - `docker compose -f docker-compose.core.yml -f docker-compose.observability.yml up -d grafana`
5. Commit the changed JSON file(s).

### Option B: Treat Grafana as read-only (strict Git-first)

If you want strict GitOps, set `editable: false` in the provider and only change dashboards via JSON updates in Git. This removes UI convenience but eliminates drift.

## Common Gotchas

- If you create a dashboard in the UI and don’t export it, it only exists in `grafana.db` and will not survive DB resets.
- If you delete or rename dashboard JSON files without checking duplicates, provisioning can thrash on startup.

## Validation + Recovery

- Validate provisioning inputs:
  - `python scripts/maintenance/grafana_provisioning_doctor.py`
- If Grafana gets stuck restarting or `health: starting` loops:
  - See `docs/grafana_provisioning_recovery.md`

## Security

- Do not store secrets in dashboard JSON.
- Prefer environment variables/secrets for webhook URLs and credentials.
