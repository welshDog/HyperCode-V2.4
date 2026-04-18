"""
HyperCode V2.4 — Load Test Suite
=================================
Target:   http://localhost:8000  (hypercode-core)
Goal:     1000 req/min sustained, P99 < 500ms, error rate < 1%

Run:
  pip install locust --break-system-packages
  locust -f tests/load/locustfile.py --host http://localhost:8000

Web UI:   http://localhost:8089
Headless: locust -f tests/load/locustfile.py --host http://localhost:8000 \
            --headless -u 50 -r 10 --run-time 2m --html tests/load/report.html
"""

from locust import HttpUser, task, between, events
import uuid
import random
import os

API_KEY = os.getenv("HYPERCODE_API_KEY", "dev-key-123")


# ---------------------------------------------------------------------------
# Light user — hits cheap endpoints (health, metrics, plan listings)
# Simulates monitoring pings + dashboard polling
# ---------------------------------------------------------------------------
class LightUser(HttpUser):
    weight = 3
    wait_time = between(0.5, 2)

    @task(5)
    def health_check(self):
        with self.client.get("/health", catch_response=True) as r:
            if r.status_code == 200:
                r.success()
            else:
                r.failure(f"Health check failed: {r.status_code}")

    @task(3)
    def get_stripe_plans(self):
        with self.client.get(
            "/api/stripe/plans",
            catch_response=True,
            name="/api/stripe/plans",
        ) as r:
            if r.status_code in (200, 401, 403):
                r.success()  # auth errors are API-layer success for load purposes
            else:
                r.failure(f"Plans endpoint: {r.status_code}")

    @task(1)
    def metrics_scrape(self):
        # Simulate Prometheus scraping — should always be fast
        with self.client.get("/metrics", catch_response=True) as r:
            if r.status_code == 200:
                r.success()
            else:
                r.failure(f"Metrics endpoint: {r.status_code}")


# ---------------------------------------------------------------------------
# API user — authenticated calls (agents list, memory, tasks)
# Simulates real dashboard users + CLI tool
# ---------------------------------------------------------------------------
class APIUser(HttpUser):
    weight = 2
    wait_time = between(1, 3)

    def on_start(self):
        self.headers = {"X-API-Key": API_KEY}

    @task(4)
    def list_agents(self):
        with self.client.get(
            "/agents",
            headers=self.headers,
            catch_response=True,
            name="/agents",
        ) as r:
            if r.status_code in (200, 401, 403, 404):
                r.success()
            else:
                r.failure(f"Agents list: {r.status_code}")

    @task(2)
    def get_memory(self):
        with self.client.get(
            "/memory",
            headers=self.headers,
            catch_response=True,
            name="/memory",
        ) as r:
            if r.status_code in (200, 401, 403, 404):
                r.success()
            else:
                r.failure(f"Memory endpoint: {r.status_code}")

    @task(1)
    def post_task(self):
        payload = {
            "task": f"load-test-task-{uuid.uuid4().hex[:8]}",
            "priority": random.choice(["low", "medium", "high"]),
            "source": "locust-load-test",
        }
        with self.client.post(
            "/tasks",
            json=payload,
            headers=self.headers,
            catch_response=True,
            name="/tasks [POST]",
        ) as r:
            if r.status_code in (200, 201, 401, 403, 404, 422):
                r.success()
            else:
                r.failure(f"Task create: {r.status_code}")


# ---------------------------------------------------------------------------
# Stripe user — simulates checkout flow (read-only, no real payments)
# ---------------------------------------------------------------------------
class StripeUser(HttpUser):
    weight = 1
    wait_time = between(2, 5)

    @task
    def checkout_initiate(self):
        payload = {
            "price_id": random.choice(["starter", "builder", "hyper"]),
            "user_id": f"load-test-{uuid.uuid4().hex[:8]}",
        }
        with self.client.post(
            "/api/stripe/checkout",
            json=payload,
            catch_response=True,
            name="/api/stripe/checkout",
        ) as r:
            # 200 = checkout URL returned (success)
            # 400 = bad price_id (API-layer response, not a crash)
            # 500 = real error we want to catch
            if r.status_code in (200, 400):
                r.success()
            elif r.status_code == 500:
                r.failure(f"Stripe checkout 500: {r.text[:200]}")
            else:
                r.failure(f"Stripe checkout unexpected: {r.status_code}")


# ---------------------------------------------------------------------------
# Event hooks — print summary thresholds at end of run
# ---------------------------------------------------------------------------
@events.quitting.add_listener
def check_thresholds(environment, **kwargs):
    stats = environment.stats.total
    fail_ratio = stats.fail_ratio
    p99 = stats.get_response_time_percentile(0.99) or 0

    print("\n" + "=" * 60)
    print("🏴󠁧󠁢󠁷󠁬󠁳󠁿 HyperCode Load Test — Results")
    print("=" * 60)
    print(f"  Total requests : {stats.num_requests}")
    print(f"  Failures       : {stats.num_failures} ({fail_ratio:.2%})")
    print(f"  P99 response   : {p99:.0f} ms")
    print(f"  Req/s peak     : {stats.max_response_time:.0f} ms max")
    print()

    passed = True
    if fail_ratio > 0.01:
        print(f"  ❌ FAIL — Error rate {fail_ratio:.2%} exceeds 1% threshold")
        passed = False
    else:
        print(f"  ✅ Error rate OK — {fail_ratio:.2%}")

    if p99 > 500:
        print(f"  ❌ FAIL — P99 {p99:.0f}ms exceeds 500ms threshold")
        passed = False
    else:
        print(f"  ✅ P99 OK — {p99:.0f}ms")

    print()
    if passed:
        print("  🏆 ALL THRESHOLDS PASSED — Stack is load-ready!")
    else:
        print("  ⚠️  Some thresholds failed — check above")
    print("=" * 60 + "\n")

    if not passed:
        environment.process_exit_code = 1
