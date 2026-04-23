# 🧪 HyperCode V2.4 — Testing Guide

## Test Layers

| Layer | Tool | Command | Report |
|-------|------|---------|--------|
| Python Unit | pytest | `pytest backend/tests/unit/` | `reports/junit-python.xml` |
| Frontend Unit | Vitest | `npm run test` | `reports/junit-frontend.xml` |
| Integration | pytest + httpx | `pytest backend/tests/integration/` | `reports/junit-integration.xml` |
| E2E UI | Playwright | `npx playwright test` | `playwright-report/` |
| Performance | k6 | `k6 run tests/performance/k6-api-load.js` | `reports/k6-report.json` |
| Security | Bandit + pip-audit + npm audit | `bash tests/security/run_security.sh` | `reports/bandit-report.json` |

## Running Tests Locally

### Python Unit Tests
```bash
pip install -r backend/requirements.txt -r backend/requirements-dev.txt
pytest backend/tests/unit/ --asyncio-mode=auto -q
```

### Frontend Unit Tests
```bash
cd agents/dashboard
npm run test          # watch mode
npm run test -- --run  # single run
```

### Integration Tests (requires running Docker stack)
```bash
docker compose up -d redis postgres hypercode-core healer-agent
pytest backend/tests/integration/ --asyncio-mode=auto -q
```

### E2E Tests (requires dashboard running)
```bash
cd "h:\HyperStation zone\HyperCode\HyperCode-V2.4"
npx playwright install chromium
npx playwright test
npx playwright show-report
```

### Performance Tests
```bash
# Install k6: https://k6.io/docs/getting-started/installation/
k6 run tests/performance/k6-api-load.js
# View: reports/k6-report.json
```

### Security Tests
```bash
bash tests/security/run_security.sh
# Check: reports/bandit-report.json + reports/npm-audit.json
```

## Coverage Targets

| Layer | Target | Current |
|-------|--------|------|
| Python Backend | \u226570% (total) | See CI / `quality-gate-thresholds.yml` |
| Frontend Components | \u226570% | See `reports/coverage-frontend/` |
| Integration | All key flows | See CI artifacts |

## Reading Reports

- **JUnit XML**: Import into any CI tool (GitHub Actions, Jenkins, etc.)
- **HTML Coverage**: Open `reports/coverage-html/index.html` in browser
- **k6 Report**: JSON with p95, error rate, throughput stats
- **Bandit Report**: Python security findings by severity
