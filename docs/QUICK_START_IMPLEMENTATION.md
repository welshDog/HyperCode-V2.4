# IMPLEMENTATION CHECKLIST & QUICK-START GUIDE

## PRE-IMPLEMENTATION CHECKLIST

### Day 1: Environment Preparation
- [ ] `.env` file created with all production secrets
- [ ] Tempo configuration validated and volumes created
- [ ] PostgreSQL healthcheck passing
- [ ] All 28+ services running healthy
- [ ] Backup of postgres-data and redis-data volumes
- [ ] Disk cleanup completed (24GB+ freed)

### Day 2: Baseline Metrics Collection
- [ ] Current error rate measured: ____%
- [ ] P99 latency measured: ____ms
- [ ] Average response time: ____ms
- [ ] Memory utilization baseline: ____%
- [ ] CPU utilization baseline: ____%
- [ ] Request volume: ____req/s

---

## QUICK-START: FIX FAILED CONTAINERS (Today)

### Fix #1: PostgreSQL Init Failure (2 min)
```bash
# The issue: Missing .env file with POSTGRES_PASSWORD

# Solution A: Verify .env exists and has password
ls -la .env
cat .env | grep POSTGRES_PASSWORD

# Solution B: If still having issues, use explicit password
docker run -d \
  -e POSTGRES_PASSWORD=hypercode-prod-password \
  -e POSTGRES_DB=hypercode \
  -v postgres-data:/var/lib/postgresql/data \
  --name postgres-fixed \
  postgres:15-alpine

# Verify
docker logs postgres-fixed | head -20
docker exec postgres-fixed pg_isready -U postgres
```

### Fix #2: Tempo Configuration (5 min)
```bash
# The issue: YAML parsing error - storage backend not properly configured

# Step 1: Verify Tempo config syntax
docker run --rm -v $(pwd)/monitoring/tempo:/config alpine:latest \
  sh -c "cat /config/tempo.yaml && echo '✓ File exists'"

# Step 2: Start fresh Tempo with correct config
docker rm -f compassionate_villani tempo 2>/dev/null || true

# Step 3: Create volumes for Tempo
docker volume create tempo-data
docker volume create tempo-wal

# Step 4: Start Tempo with new config
docker-compose up -d tempo

# Step 5: Wait for health check
docker logs tempo --follow  # Watch logs until "ready"

# Verify
curl -s http://localhost:3200/ready
```

### Fix #3: MCP Plugin (1 min)
```bash
# The issue: Outdated MCP plugin version (0.0.17)

# Option A: Remove problematic plugin
docker plugin rm -f mcp/docker:0.0.17 2>/dev/null || true

# Option B: Docker will auto-install latest on next use
docker plugin ls | grep mcp

# Verify
docker info | grep -A5 "mcp"
```

### Quick Validation Script
```bash
#!/bin/bash
echo "=== QUICK HEALTH CHECK ==="

# Check services
echo "Running containers: $(docker ps -q | wc -l)/31"

# Check Tempo
echo -n "Tempo: "
curl -s -f http://localhost:3200/ready > /dev/null && echo "✓ Healthy" || echo "✗ Unhealthy"

# Check PostgreSQL
echo -n "PostgreSQL: "
docker exec postgres pg_isready -U postgres > /dev/null 2>&1 && echo "✓ Healthy" || echo "✗ Unhealthy"

# Check Redis
echo -n "Redis: "
docker exec redis redis-cli ping > /dev/null 2>&1 && echo "✓ Healthy" || echo "✗ Unhealthy"

# Check Loki
echo -n "Loki: "
curl -s -f http://localhost:3100/ready > /dev/null && echo "✓ Healthy" || echo "✗ Unhealthy"

# Disk space
echo ""
echo "Disk usage:"
docker system df
```

---

## DISK CLEANUP (24GB+ available)

### Option 1: Manual Step-by-Step
```bash
# 1. Remove unused images (68% reclaimable = 23.7GB)
echo "Removing unused images..."
docker image prune -a --force --filter "label!=keep=true"

# 2. Remove unused volumes (85% reclaimable = 663MB)
echo "Removing unused volumes..."
docker volume prune --force --filter "label!=keep=true"

# 3. Remove build cache (saves 272MB)
echo "Removing build cache..."
docker builder prune -a --force

# 4. Verify
docker system df
```

### Option 2: Automated Script
```bash
bash CLEANUP_SCRIPT.sh
```

---

## UPGRADE PHASE 1: ZERO-DOWNTIME ROLLING UPDATES (Week 1)

### Prerequisites
- [ ] All services running healthy
- [ ] 24GB+ disk space available
- [ ] Backup volumes created
- [ ] Team trained on rollback procedures

### Step-by-Step Implementation

#### 1. Deploy Nginx Reverse Proxy (30 min)
```bash
# Create nginx config directory
mkdir -p nginx/ssl

# Copy production config
cp nginx/nginx.prod.conf nginx/nginx.conf

# Start Nginx
docker-compose up -d nginx

# Verify Nginx is running
curl -s http://localhost/health | grep -q "healthy" && echo "✓ Nginx healthy"
```

#### 2. Update Docker-Compose with Blue-Green (30 min)
```bash
# Backup current compose
cp docker-compose.yml docker-compose.yml.backup

# Update compose file (use the updated version)
# - Add hypercode-core-v1 (blue)
# - Add hypercode-core-v2 (green) with profile
# - Add tempo volumes

# Validate
docker-compose config > /dev/null && echo "✓ Compose valid"
```

#### 3. Deploy Test Version (15 min)
```bash
# Set version variables
export VERSION_BLUE=v1.0.0
export VERSION_GREEN=v1.0.1

# Start green (inactive)
docker-compose --profile green up -d hypercode-core-v2

# Wait for health check
sleep 30
docker ps | grep hypercode-core-v2

# Check it's healthy
curl -s http://localhost:8000/health
```

#### 4. Test Traffic Shift (30 min)
```bash
# Shift 10% traffic to green
curl -X POST http://localhost/admin/traffic-split \
  -H "Content-Type: application/json" \
  -d '{"green_traffic": 10}'

# Monitor error rate for 5 minutes
for i in {1..5}; do
  echo "Minute $i: $(curl -s http://prometheus:9090/api/v1/query?query=rate(http_requests_errors[5m]))"
  sleep 60
done

# If OK, shift 50%
curl -X POST http://localhost/admin/traffic-split \
  -H "Content-Type: application/json" \
  -d '{"green_traffic": 50}'

# Final shift to 100%
curl -X POST http://localhost/admin/traffic-split \
  -H "Content-Type: application/json" \
  -d '{"green_traffic": 100}'
```

---

## UPGRADE PHASE 2: CANARY DEPLOYMENTS (Week 3)

### Prerequisites
- [ ] Phase 1 complete and validated
- [ ] Prometheus scraping metrics correctly
- [ ] Baseline metrics collected
- [ ] Python 3.11 available

### Step-by-Step Implementation

#### 1. Deploy Canary Service (1 hour)
```bash
# Build canary service
cd services/canary-deployer
docker build -t hypercode/canary-deployer:latest .

# Start canary service
docker-compose -f docker-compose.canary.yml up -d canary-deployer

# Verify
curl -s http://localhost:8000/metrics | grep canary
```

#### 2. Configure Prometheus Rules (15 min)
```bash
# Add canary alert rules
cp monitoring/prometheus/canary-alerts.yml monitoring/prometheus/rules/

# Reload Prometheus
curl -X POST http://localhost:9090/-/reload

# Verify alerts loaded
curl -s http://localhost:9090/api/v1/rules | grep canary
```

#### 3. Test Canary Deployment (30 min)
```bash
# Trigger test canary
curl -X POST http://localhost:8000/api/canary/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "baseline_version": "v1.0.0",
    "canary_version": "v1.0.1"
  }'

# Watch deployment progress
docker logs canary-deployer -f | grep -E "traffic|error_rate|promoted|rolled"

# Expected output:
# [1/7] Validating new image
# [2/7] Checking deployment health
# [3/7] Target: green
# [4/7] Starting green in shadow mode
# [5/7] Waiting for health checks
# [6/7] Shifting traffic 10% → 50% → 100%
# [7/7] Finalizing deployment
# ✓ Deployment complete!
```

---

## UPGRADE PHASE 3: ENHANCED OBSERVABILITY (Week 4)

### Prerequisites
- [ ] Tempo healthy and collecting traces
- [ ] Prometheus metrics baseline established
- [ ] Grafana dashboards accessible

### Step-by-Step Implementation

#### 1. Setup Jaeger Integration (30 min)
```bash
# Update Tempo config to enable Jaeger receivers
cat > monitoring/tempo/tempo.yaml << 'EOF'
[TEMPO_CONFIG_WITH_JAEGER_RECEIVERS]
EOF

# Restart Tempo
docker-compose restart tempo

# Verify Jaeger ports listening
netstat -an | grep LISTEN | grep -E "6831|14268|14250"
```

#### 2. Instrument Applications (1 hour)
```bash
# Add OpenTelemetry to backend
pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-jaeger

# Update backend/app/main.py to include otel_setup.py

# Rebuild and restart
docker-compose up -d --build hypercode-core

# Generate some traffic
curl http://localhost:8000/api/health

# Check traces in Jaeger (via Grafana)
# Grafana → Explore → Select "Jaeger" datasource
# Search for service "hypercode-core"
```

#### 3. Create Custom Dashboards (30 min)
```bash
# Import Grafana dashboards
curl -X POST http://localhost:3001/api/dashboards/db \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GRAFANA_API_TOKEN" \
  -d @monitoring/grafana/dashboards/deployment-dashboard.json

# Access dashboard
# Grafana → Dashboards → Zero-Downtime Deployment Dashboard
```

---

## TESTING & VALIDATION

### Load Testing
```bash
# Install k6 (load testing tool)
brew install k6  # or download from k6.io

# Run load test (100 concurrent users, 5 minutes)
k6 run --vus 100 --duration 5m tests/load-test.js

# Monitor in Grafana during test
# Grafana → Dashboard → Performance Monitoring
```

### Chaos Engineering
```bash
# Test resilience with Chaos Monkey
docker run -d --name chaos \
  -e CHAOS_ENABLED=true \
  -e CHAOS_INTERVAL=30 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  chaos-monkey:latest

# This will randomly kill containers to test recovery
# Monitor recovery times in Prometheus
```

### Deployment Dry-Run
```bash
# Stage an upgrade without deploying to prod
docker-compose -f docker-compose.staging.yml up -d

# Run full test suite
pytest tests/integration/ -v

# Run smoke tests
bash tests/smoke-tests.sh

# Test rollback
bash scripts/rolling-deploy.sh v1.0.2 --dry-run
```

---

## MONITORING & ALERTING

### Key Metrics to Watch

#### During Deployment
```bash
# Real-time error rate
docker logs hypercode-core-v2 | grep ERROR | wc -l

# Request latency
curl -s http://prometheus:9090/api/v1/query?query=histogram_quantile\(0.99,http_request_duration_ms\)

# Database connections
curl -s http://prometheus:9090/api/v1/query?query=pg_stat_activity_count

# Memory usage
docker stats --no-stream hypercode-core-v2 | awk '{print $NF}' | head -2
```

#### Post-Deployment
```bash
# Error rate < 0.1%
curl -s http://prometheus:9090/api/v1/query?query=rate\(http_requests_errors\[5m\]\)

# P99 latency stable
curl -s http://prometheus:9090/api/v1/query?query=histogram_quantile\(0.99,http_request_duration_ms\)

# Rollback rate 0
curl -s http://prometheus:9090/api/v1/query?query=canary_deployment_status
```

---

## TROUBLESHOOTING GUIDE

### Tempo Not Starting
```bash
# Check config syntax
docker run --rm -v $(pwd)/monitoring/tempo:/config yaml -c /config/tempo.yaml

# Check volume mounts
docker volume inspect tempo-data

# Check logs
docker logs tempo | tail -50

# Restart with debug logging
docker-compose up tempo  # In foreground
```

### Canary Promotion Failing
```bash
# Check Prometheus connectivity
docker exec canary-deployer curl -s http://prometheus:9090/api/v1/targets

# Check metric values
curl -s 'http://prometheus:9090/api/v1/query?query=rate(http_requests_errors[5m])'

# Check Nginx config
docker exec nginx-prod cat /etc/nginx/nginx.conf

# Manually approve deployment
curl -X POST http://localhost:8000/api/canary/promote \
  -H "Content-Type: application/json" \
  -d '{"version": "v1.0.1", "force": true}'
```

### High Latency During Canary
```bash
# Check if database is bottleneck
docker stats postgres --no-stream

# Check if Nginx is overloaded
curl -s http://localhost/metrics | grep nginx_requests

# Reduce traffic to canary
curl -X POST http://localhost/admin/traffic-split \
  -d '{"green_traffic": 10}'

# Check application logs
docker logs hypercode-core-v2 | grep -i error | tail -20
```

---

## ROLLBACK PROCEDURES

### Automatic Rollback (If Error Rate Spikes)
```bash
# This happens automatically when:
# - Error rate > 0.5%
# - Latency P99 > baseline + 30%
# - Memory usage > limit

# Monitor progress
docker logs canary-deployer | grep -E "error|rollback"

# Check new error rate
curl -s http://prometheus:9090/api/v1/query?query=rate\(http_requests_errors\[5m\]\)
```

### Manual Rollback
```bash
# Step 1: Stop traffic to green
curl -X POST http://localhost/admin/traffic-split \
  -d '{"green_traffic": 0}'

# Step 2: Verify blue is healthy
docker exec hypercode-core-v1 curl http://localhost:8000/health

# Step 3: Restart blue if needed
docker-compose restart hypercode-core-v1

# Step 4: Shift all traffic back to blue
curl -X POST http://localhost/admin/traffic-split \
  -d '{"green_traffic": 0}'

# Step 5: Investigate issue
docker logs hypercode-core-v2 | tail -100 > /tmp/canary-failure.log

# Step 6: Fix and retry
# git revert <bad-commit>
# docker build -t hypercode-v20:v1.0.2-fixed .
```

---

## SUCCESS CHECKLIST (Post-Implementation)

### Week 1-2: Blue-Green Setup
- [ ] Nginx reverse proxy healthy and routing correctly
- [ ] Manual blue/green switches tested (5+ times)
- [ ] Health checks passing on both versions
- [ ] Rollback tested and working
- [ ] No manual intervention needed during switches

### Week 3-4: Canary Deployments
- [ ] Canary service deployed and running
- [ ] ML model detecting 90%+ of anomalies
- [ ] Automatic promotion working for good builds
- [ ] Automatic rollback working for bad builds
- [ ] 5-minute canary period validated

### Week 4: Enhanced Observability
- [ ] Tempo tracing 100% of requests
- [ ] Jaeger showing full trace depth
- [ ] Logs/metrics/traces correlated
- [ ] Custom dashboards showing deployment status
- [ ] Alert thresholds properly tuned
- [ ] MTTR reduced to < 5 minutes

---

## NEXT MEETING AGENDA

- [ ] Review current status vs. timeline
- [ ] Discuss any blockers or issues
- [ ] Plan next sprint objectives
- [ ] Schedule training sessions
- [ ] Plan production cutover date

---

*Last Updated: 2026-03-05 | Next Review: 2026-03-12*
