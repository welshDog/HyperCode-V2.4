import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE = __ENV.BASE_URL || 'http://host.docker.internal:8000';

export const options = {
  scenarios: {
    agents_status_polling: {
      executor: 'constant-vus',
      vus: 50,
      duration: '60s',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.005'],
    http_req_duration: ['p(95)<250'],
  },
};

export default function () {
  const res = http.get(`${BASE}/api/v1/agents/status`);
  check(res, {
    'agents status 200': (r) => r.status === 200,
    'has agents key': (r) => {
      try {
        return Array.isArray(r.json('agents'));
      } catch (_) {
        return false;
      }
    },
  });
  sleep(0.1);
}

