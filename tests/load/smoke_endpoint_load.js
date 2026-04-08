import http from "k6/http";
import { check } from "k6";
import { Counter, Rate, Trend } from "k6/metrics";

const redisWriteLeaks = new Counter("redis_write_leaks");
const smokePassRate = new Rate("smoke_pass_rate");
const smokeLatency = new Trend("smoke_latency_ms", true);

const baseUrl = __ENV.BASE_URL || "http://127.0.0.1:8081";
const smokeKey = __ENV.SMOKE_KEY || "";
const orchestratorKey = __ENV.ORCHESTRATOR_KEY || "";

export const options = {
  scenarios: {
    ramp_load: {
      executor: "ramping-arrival-rate",
      startRate: 100,
      timeUnit: "1s",
      preAllocatedVUs: 200,
      maxVUs: 800,
      stages: [
        { target: 5000, duration: "15s" },
        { target: 10000, duration: "15s" },
        { target: 10000, duration: "60s" },
        { target: 0, duration: "10s" },
      ],
    },
  },
  thresholds: {
    http_req_duration: ["p(99)<20"],
    http_req_failed: ["rate<0.001"],
    smoke_pass_rate: ["rate>0.999"],
    redis_write_leaks: ["count==0"],
  },
};

function maybeAuthHeaders() {
  if (!orchestratorKey) return {};
  return { "X-API-Key": orchestratorKey };
}

export function setup() {
  const res = http.get(`${baseUrl}/tasks`, { headers: maybeAuthHeaders() });
  let tasksBefore = -1;
  if (res.status === 200) {
    try {
      const body = JSON.parse(res.body);
      if (Array.isArray(body)) tasksBefore = body.length;
    } catch {}
  }
  return { tasksBefore };
}

export default function () {
  const res = http.post(
    `${baseUrl}/execute/smoke`,
    JSON.stringify({ mode: "noop" }),
    {
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": smokeKey,
        "X-Smoke-Mode": "true",
      },
      timeout: "5s",
    }
  );

  const ok = check(res, {
    "status 200": (r) => r.status === 200,
    "smoke=pass": (r) => {
      try {
        return JSON.parse(r.body).smoke === "pass";
      } catch {
        return false;
      }
    },
    "approval_skipped": (r) => {
      try {
        return JSON.parse(r.body).approval_skipped === true;
      } catch {
        return false;
      }
    },
    "redis_writes_skipped_present": (r) => {
      try {
        const v = JSON.parse(r.body).redis_writes_skipped;
        const leaked = typeof v !== "number" || v <= 0;
        if (leaked) redisWriteLeaks.add(1);
        return !leaked;
      } catch {
        redisWriteLeaks.add(1);
        return false;
      }
    },
  });

  smokePassRate.add(ok);
  smokeLatency.add(res.timings.duration);
}

export function teardown(data) {
  const res = http.get(`${baseUrl}/tasks`, { headers: maybeAuthHeaders() });
  if (res.status !== 200) return;
  try {
    const body = JSON.parse(res.body);
    if (!Array.isArray(body)) return;
    const tasksAfter = body.length;
    const delta = tasksAfter - data.tasksBefore;
    if (delta !== 0) {
      redisWriteLeaks.add(1);
    }
  } catch {}
}
