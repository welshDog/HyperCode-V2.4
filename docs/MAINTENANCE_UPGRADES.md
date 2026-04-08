# \uD83D\uDD27 HyperCode V2.0 — Maintenance & Upgrades

## Weekly Maintenance Checklist

- [ ] Check `reports/bandit-report.json` for new HIGH severity items
- [ ] Run `npm audit` in `agents/dashboard/`
- [ ] Review Grafana dashboards for error rate spikes
- [ ] Check agent XP ledger for stalled agents (no XP gain in 7 days)
- [ ] Verify `.secrets.baseline` is up to date

## Adding a New Agent

1. Create folder: `agents/my-new-agent/`
2. Copy base agent structure from `agents/base-agent/`
3. Implement FastAPI app on a unique port
4. Import `AgentMessage` from `agents/shared/agent_message.py`
5. Publish events to Redis event bus on start/success/failure
6. Add service entry to `docker-compose.yml`
7. Add health check at `/health`
8. Write unit tests in `tests/unit/test_my_new_agent.py`

## Adding a New Dashboard View

1. Create component: `agents/dashboard/components/views/MyView.tsx`
2. Register in `agents/dashboard/lib/view-registry.ts`
3. Add to `VIEW_REGISTRY` in `HyperShellLayout.tsx`
4. Add `PaneConfig` to `DEFAULT_PANES` array
5. Write tests in `agents/dashboard/__tests__/MyView.test.tsx`

## Upgrading Python Dependencies

```bash
# Check outdated packages
pip list --outdated

# Upgrade safely (test after each major version)
pip install --upgrade <package>
pytest tests/unit/ tests/integration/ --asyncio-mode=auto
```

## Upgrading Node Dependencies

```bash
cd agents/dashboard
npx npm-check-updates -u  # Show available updates
npm install
npm run test -- --run     # Verify nothing broke
```

## Docker Image Updates

```bash
# Pull latest base images
docker compose pull

# Rebuild all services
docker compose build --no-cache

# Test with nano stack first
docker compose -f docker-compose.nano.yml up -d
```

## API Versioning Policy

- All backend endpoints are under `/api/v1/`
- Breaking changes require a new version: `/api/v2/`
- Old versions deprecated with a sunset header: `Sunset: <date>`
- Frontend API client (`lib/api-client.ts`) must be updated when versions change
