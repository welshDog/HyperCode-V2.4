import http from 'k6/http'
import { check, sleep } from 'k6'
import { Rate, Trend } from 'k6/metrics'

const errorRate = new Rate('error_rate')
const responseTime = new Trend('response_time')

export const options = {
  stages: [
    { duration: '10s', target: 5 },
    { duration: '30s', target: 25 },
    { duration: '20s', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<250'],
    http_req_failed: ['rate<0.01'],
    error_rate: ['rate<0.01'],
  },
  summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(90)', 'p(95)', 'p(99)'],
}

const BASE_URL = __ENV.BASE_URL || 'http://host.docker.internal:8000'

export default function () {
  const res = http.get(`${BASE_URL}/health`, { timeout: '5s' })
  const ok = check(res, {
    'health status 200': (r) => r.status === 200,
    'health has ok': (r) => r.body?.includes('"ok"') ?? false,
  })

  errorRate.add(!ok)
  responseTime.add(res.timings.duration)
  sleep(0.2)
}

export function handleSummary(data) {
  return {
    'reports/k6-health-report.json': JSON.stringify(data, null, 2),
    stdout: JSON.stringify(
      {
        http_reqs: data.metrics.http_reqs?.values?.count,
        p95_ms: data.metrics.http_req_duration?.values['p(95)'],
        failed_rate_pct: (data.metrics.http_req_failed?.values?.rate * 100).toFixed(3),
      },
      null,
      2,
    ),
  }
}
