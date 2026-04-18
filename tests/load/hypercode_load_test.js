import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const errors = new Rate('errors');
const responseTime = new Trend('response_time_ms', true);
const BASE = __ENV.BASE_URL || 'http://host.docker.internal:8000';

export const options = {
  stages: [
    { duration: '30s', target: 100 },
    { duration: '1m', target: 1000 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(99)<100'],
    http_req_failed: ['rate<0.001'],
    errors: ['rate<0.001'],
  },
};

export default function () {
  const health = http.get(`${BASE}/health`);
  check(health, { 'health 200': (r) => r.status === 200 });
  errors.add(health.status !== 200);
  responseTime.add(health.timings.duration);

  const metrics = http.get(`${BASE}/api/v1/metrics`);
  check(metrics, { 'metrics 200': (r) => r.status === 200 });
  errors.add(metrics.status !== 200);

  sleep(0.01);
}

