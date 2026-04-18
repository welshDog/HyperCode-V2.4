import http from 'k6/http';
import { check } from 'k6';

const BASE = __ENV.BASE_URL || 'http://host.docker.internal:8000';

export const options = {
  vus: 20,
  duration: '45s',
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<500'],
  },
};

export default function () {
  const payload = JSON.stringify({
    price_id: 'starter',
    user_id: `k6_${__VU}_${__ITER}`,
  });

  const res = http.post(`${BASE}/api/stripe/checkout`, payload, {
    headers: { 'Content-Type': 'application/json' },
  });

  check(res, {
    'checkout status ok-ish': (r) => r.status === 200 || r.status === 400 || r.status === 422,
  });
}

