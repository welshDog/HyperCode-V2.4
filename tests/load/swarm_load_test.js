import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Custom Metrics
const failureRate = new Rate('failed_requests');

export let options = {
  scenarios: {
    swarm_load: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 50 }, // Ramp up to 50 VUs
        { duration: '10m', target: 50 }, // Stay at 50 VUs for 10m
        { duration: '10s', target: 0 },  // Ramp down
      ],
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95% of requests must complete below 500ms
    failed_requests: ['rate<0.01'],   // Error rate must be below 1%
  },
};

const BASE_URL = 'http://localhost:8000/api/v1';

export default function () {
  // Scenario Mix Logic
  const rand = Math.random();

  if (rand < 0.7) {
    // 70% Task Submission
    submitTask();
  } else if (rand < 0.9) {
    // 20% Status Query
    queryStatus();
  } else {
    // 10% Agent Termination (Simulated)
    killAgent();
  }

  sleep(1);
}

function submitTask() {
  const payload = JSON.stringify({
    messages: [{ role: 'user', content: 'Print Hello World' }],
    model: 'gpt-4o'
  });
  
  const params = {
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': 'dev-key',
    },
  };

  const res = http.post(`${BASE_URL}/agents/chat`, payload, params);
  
  check(res, {
    'status is 200': (r) => r.status === 200,
  }) || failureRate.add(1);
}

function queryStatus() {
  // Simulating fetching a known agent (mock ID for test)
  const agentId = 'test-agent-id';
  const params = {
    headers: { 'X-API-Key': 'dev-key' },
  };

  const res = http.get(`${BASE_URL}/agents/${agentId}`, params);
  
  // We expect 404 for mock ID, but in load test we check for server stability (not 500)
  check(res, {
    'server handled request': (r) => r.status !== 500,
  }) || failureRate.add(1);
}

function killAgent() {
  // Simulating kill signal
  const agentId = 'test-agent-id';
  const params = {
    headers: { 'X-API-Key': 'dev-key' },
  };

  const res = http.del(`${BASE_URL}/agents/${agentId}`, null, params);
  
  check(res, {
    'server handled request': (r) => r.status !== 500,
  }) || failureRate.add(1);
}
