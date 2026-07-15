# HS-049 — Progressive Health Wait Pattern

> **Extracted from:** `hyperlaunch.py` · HyperCode-V2.4
> **What it is:** How to wait for services to be genuinely ready before starting the next layer

---

## The Core Problem

`docker compose up -d` returns immediately — containers start but aren't necessarily *ready*.
Starting the next service too early = connection refused errors, failed init, cascading failures.

## The Solution: wait_for_service()

```python
async def wait_for_service(spec: ServiceSpec, retry_interval: float = 2.0) -> bool:
    deadline = time.time() + spec.startup_timeout
    while time.time() < deadline:
        if spec.health_url:
            healthy = await check_http_health(spec.health_url)  # HTTP /health
        elif spec.port:
            healthy = await check_tcp_port("localhost", spec.port)  # TCP connect
        else:
            healthy = True  # No check = assume up
        if healthy:
            return True
        await asyncio.sleep(retry_interval)  # 2s between retries
    return False  # Timeout
```

## Two Health Check Strategies

### HTTP Health Check
```python
async def check_http_health(url: str, timeout: float = 5.0) -> bool:
    # urllib only (no external deps)
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.status == 200
```

### TCP Port Check (for Redis/Postgres)
```python
async def check_tcp_port(host: str, port: int, timeout: float = 3.0) -> bool:
    with socket.create_connection((host, port), timeout=timeout):
        return True
```

## Timeout Strategy Per Tier

| Service | `startup_timeout` | Why |
|---|---|---|
| Redis | 30s | Fast start — in-memory only |
| Postgres | 45s | Needs to init data directory first boot |
| Core services | 60s | Model loading + DB connection |
| AI Agents | 90s | LLM init + registration |
| Next.js Dashboard | 90s | First-request compile |

## The Abort Rule

```python
if spec.critical and not tier_results.get(spec.name, False):
    # Abort — don't start next tier
    await publish_launch_event("launch_failed", {"failed_service": spec.name})
    return False
```

- **Critical service fails** → entire launch aborts
- **Non-critical fails** → logged, launch continues
- **All healthy** → next tier starts

## Redis State Sync Integration

Every tier completion publishes an event:
```python
await publish_launch_event(f"tier_{tier.value}_complete", {
    "tier": tier.value,
    "results": tier_results,  # {service_name: bool}
})
```

All modules listening on `hypercode:system` Redis channel get notified instantly.

---

> ⏳ Progressive = patient. Each layer earns the right to start.
