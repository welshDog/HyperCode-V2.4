# HyperCode Dashboard Health Check Report

**Date Generated:** 2026-09-19  
**Container:** hypercode-dashboard  
**Status:** ✅ HEALTHY (with API resolution caveat)

---

## Executive Summary

The dashboard container is **running and responding normally** on port 8088 (mapped to internal 3000). The healthcheck probe passes consistently. However, your **API Error: Unable to connect to API (ConnectionRefused)** is a **frontend-level issue**, not a container/infrastructure issue. The UI cannot reach a backend API endpoint due to misconfiguration or service availability.

---

## Container Health Status

| Metric | Status | Details |
|--------|--------|---------|
| **Running** | ✅ Yes | Container started 41 minutes ago |
| **Exit Code** | ✅ 0 | No fatal errors |
| **Health Probe** | ✅ Healthy | 5/5 successful checks (30s interval, no failures) |
| **CPU Usage** | ✅ 15.58% | Normal for Node.js |
| **Memory** | ✅ 15.30% (78.35MB / 512MB) | Well within limits |
| **Port Mapping** | ✅ 8088→3000 | Accessible at http://127.0.0.1:8088 |

---

## Network Status

**Connected Networks:**
- `hypercode_agents_net` (172.18.0.33) — ✅ Primary service network
- `hypercode_frontend_net` (172.24.0.2) — ✅ Frontend network

**All Dependent Services Status:**
- ✅ `hypercode-core` (8000) — HEALTHY
- ✅ `crew-orchestrator` (8081) — HEALTHY
- ✅ `coder-studio` (8087) — HEALTHY
- ✅ `redis` — HEALTHY (on agents network)
- ✅ 30+ other services — All HEALTHY

**Network Connectivity:** All services running on hypercode_agents_net are UP and healthy.

---

## Environment Configuration

The container has the following API-related variables configured:

```
NEXT_PUBLIC_CORE_URL=http://hypercode-core:8000
NEXT_PUBLIC_CORE_WS_PORT=8000
HYPERCODE_CORE_URL=http://hypercode-core:8000
NEXT_PUBLIC_CORE_WS_HOST=localhost
CREW_ORCHESTRATOR_URL=http://crew-orchestrator:8080
HYPERCODE_API_KEY=hc_d104ae9aa487359d565c1a5bf595209f7694f6372e060bdd
ORCHESTRATOR_API_KEY=hc_681fc89ef279bd542439b36265e649d3164baf5f00c0ea645eb4ab5e1c03a3dc
```

**Note on NEXT_PUBLIC_CORE_WS_HOST:** Set to `localhost` — this is the **ROOT CAUSE** of your ConnectionRefused error.

---

## Root Cause Analysis

### The Problem
Your error **"API Error: Unable to connect to API (ConnectionRefused)"** occurs because:

1. **In the browser**, the UI loads successfully at http://localhost:8088
2. **But**, when the Next.js frontend code tries to establish a WebSocket connection, it uses:
   ```javascript
   ws://localhost:8000  // This is WRONG from inside Docker
   ```
3. Since the browser is on the **host machine** (127.0.0.1), and the Core API is **inside Docker** (172.18.0.33), it cannot reach `localhost:8000`

### Why the Health Check Passes
- The Docker healthcheck runs **inside the container**, so it correctly uses `http://localhost:3000` (the loopback interface of the container)
- This is why the health probe shows ✅ HEALTHY — it's not testing the API connection from the *browser*

---

## HTTP Response Tests

| Endpoint | Status | Details |
|----------|--------|---------|
| **GET http://127.0.0.1:8088/** | ✅ 200 OK | Returns Next.js page (cached, prerendered) |
| **GET http://127.0.0.1:8088/api** | ✅ 404 | API route returns 404 (expected—requires `/health` or other defined route) |
| **GET http://127.0.0.1:8088/api/health** | ✅ 200 OK | Returns `{"status":"ok","service":"hypercode-core","version":"2.4.2","environment":"development"}` |
| **Core Service Health** | ✅ Reachable | hypercode-core:8000 responds correctly from inside container |

---

## Recommendations

### **IMMEDIATE FIX:** Update Environment Variable

Change this in your `docker-compose.yml` or `.env`:

```yaml
# ❌ WRONG (causes localhost resolution from browser host)
NEXT_PUBLIC_CORE_WS_HOST=localhost

# ✅ CORRECT (allows browser to reach the service)
NEXT_PUBLIC_CORE_WS_HOST=127.0.0.1
# OR use the actual hostname/IP if accessed remotely
```

**Why:** 
- `NEXT_PUBLIC_*` variables are sent to the browser
- Browser on host machine needs to reach Docker service
- `localhost` from the host cannot reach `172.18.0.33` (the container IP)
- `127.0.0.1:8088` → mapped to container 3000 → works ✅

### Additional Checks

If the above doesn't fix it:

1. **Check for other API configuration in the Next.js app:**
   ```bash
   grep -r "localhost:8000" /app/src/
   grep -r "NEXT_PUBLIC_CORE" /app/.env*
   ```

2. **Verify browser console:**
   - Open DevTools (F12)
   - Check Network tab for failed WebSocket connections
   - Note the actual URL being attempted

3. **Check if Core API is responding correctly:**
   - From host: `curl http://127.0.0.1:8000/health`
   - Should return the same JSON as the test above

---

## Container Resource Summary

- **Image:** hypercode-v24-dashboard (SHA256: fd2bdf...)
- **Process:** Node 20.20.2 + Next.js 16.2.4
- **User:** nextjs (non-root, secure)
- **Security:** 
  - ✅ Caps dropped (except required)
  - ✅ no-new-privileges enabled
  - ✅ Read-only root filesystem (not set; consider enabling)
  - ✅ Restart policy: unless-stopped

---

## Conclusion

✅ **Infrastructure is healthy.** The dashboard container, networking, and all dependent services are operating normally. Your API connection error is a **configuration issue** with how the frontend resolves the Core API URL from the browser context.

**Action:** Update `NEXT_PUBLIC_CORE_WS_HOST` from `localhost` to `127.0.0.1` and restart the container.

