# \uD83E\uDDEA HyperCode V2.0 — Testing Guide

## Test Layers

| Layer | Tool | Command | Report |
|-------|------|---------|--------|
| Python Unit | pytest | `pytest tests/unit/` | `reports/junit-python.xml` |
| Frontend Unit | Vitest | `npm run test` | `reports/junit-frontend.xml` |
| Integration | pytest + httpx | `pytest tests/integration/` | `reports/junit-integration.xml` |
| E2E UI | Playwright | `npx playwright test` | `reports/e2e-html/` |
| Performance | k6 | `k6 run tests/performance/k6-api-load.js` | `reports/k6-report.json` |
| Security | Bandit + npm audit | `bash tests/security/run_security.sh` | `reports/bandit-report.json` |

## Running Tests Locally

### Python Unit Tests
```bash
pip install pytest pytest-asyncio pytest-cov
pytest tests/unit/ --asyncio-mode=auto --cov=backend -v
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
pytest tests/integration/ --asyncio-mode=auto -v -m integration
```

### E2E Tests (requires dashboard running)
```bash
docker compose up -d
npx playwright install
npx playwright test
npx playwright show-report reports/e2e-html
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
| Python Backend | \u226580% | See `reports/coverage-html/` |
| Frontend Components | \u226570% | See `reports/coverage-frontend/` |
| Integration | All key flows | See CI artifacts |

## Reading Reports

- **JUnit XML**: Import into any CI tool (GitHub Actions, Jenkins, etc.)
- **HTML Coverage**: Open `reports/coverage-html/index.html` in browser
- **k6 Report**: JSON with p95, error rate, throughput stats
- **Bandit Report**: Python security findings by severity
