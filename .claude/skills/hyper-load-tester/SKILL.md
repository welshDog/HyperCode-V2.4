---
name: hyper-load-tester
description: Load testing and performance benchmarking for HyperCode V2.4. Use when writing k6 or locust load tests, setting up performance baselines, running stress tests against the API, verifying P99 latency targets, or adding load testing to CI. Target: 1000 req/sec, P99 < 100ms.
---

# HyperCode Load Tester Skill

## Target SLOs
```
Throughput:   1000 req/sec (sustained)
P50 latency:  < 20ms
P99 latency:  < 100ms
Error rate:   < 0.1%
```

## Tool: k6 (recommended over locust for this stack)

```bash
# Install
docker run --rm -i grafana/k6 version

# Run a test
docker run --rm -i --network host grafana/k6 run - < tests/load/hypercode_load_test.js
```

## Core Load Test (tests/load/hypercode_load_test.js)

```javascript
import http from 'k6/http'
import { check, sleep } from 'k6'
import { Rate, Trend } from 'k6/metrics'

const errorRate = new Rate('errors')
const responseTime = new Trend('response_time_ms', true)

export const options = {
  stages: [
    { duration: '30s', target: 100 },   // ramp up
    { duration: '1m',  target: 1000 },  // peak load
    { duration: '30s', target: 0 },     // ramp down
  ],
  thresholds: {
    http_req_duration: ['p(99)<100'],   // P99 < 100ms
    http_req_failed: ['rate<0.001'],    // < 0.1% errors
    errors: ['rate<0.001'],
  },
}

const BASE = 'http://localhost:8000'

export default function () {
  // Health endpoint
  const health = http.get(`${BASE}/health`)
  check(health, { 'health 200': r => r.status === 200 })
  errorRate.add(health.status !== 200)
  responseTime.add(health.timings.duration)

  // API endpoint
  const agents = http.get(`${BASE}/api/v1/agents/status`, {
    headers: { 'Content-Type': 'application/json' }
  })
  check(agents, { 'agents 200': r => r.status === 200 })
  errorRate.add(agents.status !== 200)

  sleep(0.01) // 10ms think time
}
```

## Stripe Checkout Load Test (tests/load/stripe_load_test.js)

```javascript
// NOTE: Always use test mode keys for load testing
// NEVER load test against live Stripe

export default function () {
  const payload = JSON.stringify({
    price_id: 'starter',
    user_id: `load_test_${__VU}_${__ITER}`
  })
  
  const res = http.post(`${BASE}/api/v1/stripe/checkout`, payload, {
    headers: { 'Content-Type': 'application/json' }
  })
  
  check(res, {
    'checkout 200': r => r.status === 200,
    'has url': r => r.json('url') !== undefined,
  })
}
```

## Makefile Targets to Add

```makefile
load-test:
    @echo "🔥 Running load test — target: 1000 req/sec, P99 < 100ms"
    @docker run --rm -i --network host grafana/k6 run - < tests/load/hypercode_load_test.js

load-test-smoke:
    @docker run --rm -i --network host grafana/k6 run \
        --vus 10 --duration 30s \
        - < tests/load/hypercode_load_test.js

load-test-stripe:
    @echo "⚠️  Using Stripe TEST mode only"
    @docker run --rm -i --network host grafana/k6 run - < tests/load/stripe_load_test.js
```

## Reading Results

```
✅ PASS:
  http_req_duration............: p(99)=87ms < 100ms ✓
  http_req_failed..............: 0.00% ✓

❌ FAIL — what to check:
  p(99) > 100ms    → Check DB connection pool (pool_size=10 in asyncpg config)
                   → Check Redis cache hit rate
                   → Check hypercode-core memory (> 1GB = GC pressure)
  
  errors > 0.1%   → Check circuit breakers (are they OPEN?)
                  → Check postgres max_connections
                  → Check rate limiter (60/minute per IP — load test hits this!)
```

## Rate Limiter Bypass for Load Testing

```python
# In test, use different IPs or exempt the load test user-agent
# In hypercode-core rate limiter config:
RATE_LIMIT_EXEMPT_IPS = ["127.0.0.1"]  # localhost load tests
```

## DB Connection Pool (already configured)

```python
# backend/app/db/session.py — verify this config:
engine = create_async_engine(
    DATABASE_URL,
    pool_size=10,          # base connections
    max_overflow=20,       # burst connections
    pool_timeout=30,       # wait time before error
    pool_recycle=1800,     # recycle after 30 min
)
```

If P99 spikes under load → increase `pool_size` first before anything else.

## Files to Create

```
tests/load/
  hypercode_load_test.js    ← main API load test
  stripe_load_test.js       ← payment flow test
  agents_load_test.js       ← agent endpoint test
  README.md                 ← how to run + interpret results
```
