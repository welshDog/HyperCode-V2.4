/**
 * k6 Load Test — HyperCode API
 * Run: k6 run tests/performance/k6-api-load.js
 * Output: reports/k6-report.json
 */
import http from 'k6/http'
import { check, sleep } from 'k6'
import { Rate, Trend } from 'k6/metrics'

const errorRate    = new Rate('error_rate')
const responseTime = new Trend('response_time')

export const options = {
  stages: [
    { duration: '30s', target: 10  }, // Ramp up
    { duration: '60s', target: 50  }, // Sustain
    { duration: '30s', target: 100 }, // Spike
    { duration: '30s', target: 0   }, // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 95% under 500ms
    http_req_failed:   ['rate<0.05'],  // <5% error rate
    error_rate:        ['rate<0.05'],
  },
  summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(90)', 'p(95)', 'p(99)'],
}

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000'

export default function () {
  // ── Agent list endpoint
  const agentsRes = http.get(`${BASE_URL}/api/v1/agents`)
  const agentsOk = check(agentsRes, {
    'agents status 200': (r) => r.status === 200,
    'agents has body':   (r) => r.body.length > 0,
    'agents < 500ms':    (r) => r.timings.duration < 500,
  })
  errorRate.add(!agentsOk)
  responseTime.add(agentsRes.timings.duration)

  // ── Health endpoint
  const healthRes = http.get(`${BASE_URL}/health`)
  check(healthRes, {
    'health status 200': (r) => r.status === 200,
  })

  // ── Metrics endpoint
  const metricsRes = http.get(`${BASE_URL}/api/v1/metrics`)
  check(metricsRes, {
    'metrics status 200': (r) => r.status === 200,
  })

  sleep(1)
}

export function handleSummary(data) {
  return {
    'reports/k6-report.json': JSON.stringify(data, null, 2),
    'stdout': JSON.stringify({
      scenarios:      data.metrics.http_reqs?.values?.count,
      p95_ms:         data.metrics.http_req_duration?.values['p(95)'],
      error_rate_pct: (data.metrics.http_req_failed?.values?.rate * 100).toFixed(2),
    }),
  }
}
