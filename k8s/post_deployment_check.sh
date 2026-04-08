#!/bin/bash

# HyperCode Post-Deployment Verification & Performance Benchmarking
# Comprehensive system diagnostics with detailed recommendations

set -e

NAMESPACE="hypercode"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PERFORMANCE_REPORT="${SCRIPT_DIR}/performance_report.txt"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m'

> "$PERFORMANCE_REPORT"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  HyperCode Post-Deployment Verification & Performance    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"

# 1. Connection Tests
echo -e "\n${MAGENTA}═══ 1. SERVICE CONNECTIVITY TESTS ═══${NC}"

test_connectivity() {
    local service=$1
    local port=$2
    local namespace=$3
    
    echo -n "Testing $service:$port... "
    if kubectl run -it --rm test-curl --image=curlimages/curl:latest --restart=Never -n "$namespace" -- curl -s -m 5 "http://$service:$port/health" &>/dev/null || \
       kubectl run -it --rm test-curl --image=curlimages/curl:latest --restart=Never -n "$namespace" -- curl -s -m 5 "http://$service:$port/" &>/dev/null; then
        echo -e "${GREEN}✓ Connected${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed${NC}"
        return 1
    fi
}

# Test core services
SERVICES_TO_TEST=(
    "hypercode-core:8000"
    "redis:6379"
    "postgres:5432"
    "prometheus:9090"
    "grafana:3000"
)

for service_port in "${SERVICES_TO_TEST[@]}"; do
    IFS=':' read -r service port <<< "$service_port"
    test_connectivity "$service" "$port" "$NAMESPACE" || true
done | tee -a "$PERFORMANCE_REPORT"

# 2. Database Health
echo -e "\n${MAGENTA}═══ 2. DATABASE DIAGNOSTICS ═══${NC}"

echo "PostgreSQL Status:" | tee -a "$PERFORMANCE_REPORT"
kubectl exec -n "$NAMESPACE" postgres-0 -- psql -U postgres -t -c "
SELECT 
    version() as PostgreSQL_Version,
    now() as Current_Time,
    datname as Database_Name,
    pg_database.datistemplate as Is_Template,
    pg_database_size(pg_database.datname) as Size_Bytes
FROM pg_database
WHERE datname = 'hypercode';" 2>/dev/null | tee -a "$PERFORMANCE_REPORT" || echo "  [Unable to connect to PostgreSQL]" | tee -a "$PERFORMANCE_REPORT"

echo "" | tee -a "$PERFORMANCE_REPORT"
echo "Connection Count:" | tee -a "$PERFORMANCE_REPORT"
kubectl exec -n "$NAMESPACE" postgres-0 -- psql -U postgres -t -c "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null | tee -a "$PERFORMANCE_REPORT" || echo "  [N/A]" | tee -a "$PERFORMANCE_REPORT"

echo "" | tee -a "$PERFORMANCE_REPORT"
echo "Replication Status:" | tee -a "$PERFORMANCE_REPORT"
kubectl exec -n "$NAMESPACE" postgres-0 -- psql -U postgres -t -c "SELECT slot_name, slot_type, active FROM pg_replication_slots;" 2>/dev/null | tee -a "$PERFORMANCE_REPORT" || echo "  No replication configured" | tee -a "$PERFORMANCE_REPORT"

# 3. Cache Performance
echo -e "\n${MAGENTA}═══ 3. REDIS CACHE PERFORMANCE ═══${NC}"

echo "Redis Memory Statistics:" | tee -a "$PERFORMANCE_REPORT"
kubectl exec -n "$NAMESPACE" redis-0 -- redis-cli --csv info memory 2>/dev/null | grep -E "used_memory|max_memory|evicted" | tee -a "$PERFORMANCE_REPORT" || echo "  [N/A]" | tee -a "$PERFORMANCE_REPORT"

echo "" | tee -a "$PERFORMANCE_REPORT"
echo "Redis Key Count:" | tee -a "$PERFORMANCE_REPORT"
kubectl exec -n "$NAMESPACE" redis-0 -- redis-cli dbsize 2>/dev/null | tee -a "$PERFORMANCE_REPORT" || echo "  [N/A]" | tee -a "$PERFORMANCE_REPORT"

# 4. Cluster Resource Usage
echo -e "\n${MAGENTA}═══ 4. CLUSTER RESOURCE USAGE ═══${NC}"

echo "Node Resources:" | tee -a "$PERFORMANCE_REPORT"
kubectl top nodes 2>/dev/null | tee -a "$PERFORMANCE_REPORT" || echo "  [Metrics server not installed]" | tee -a "$PERFORMANCE_REPORT"

echo "" | tee -a "$PERFORMANCE_REPORT"
echo "Pod Resource Usage (Top 15):" | tee -a "$PERFORMANCE_REPORT"
kubectl top pods -n "$NAMESPACE" --sort-by=memory 2>/dev/null | head -15 | tee -a "$PERFORMANCE_REPORT" || echo "  [Metrics not available]" | tee -a "$PERFORMANCE_REPORT"

# 5. Storage Analysis
echo -e "\n${MAGENTA}═══ 5. STORAGE ANALYSIS ═══${NC}"

echo "PVC Usage:" | tee -a "$PERFORMANCE_REPORT"
kubectl get pvc -n "$NAMESPACE" -o custom-columns=NAME:.metadata.name,SIZE:.spec.resources.requests.storage,STATUS:.status.phase --no-headers | tee -a "$PERFORMANCE_REPORT"

echo "" | tee -a "$PERFORMANCE_REPORT"
echo "PostgreSQL Data Size:" | tee -a "$PERFORMANCE_REPORT"
kubectl exec -n "$NAMESPACE" postgres-0 -- du -sh /var/lib/postgresql/data 2>/dev/null | tee -a "$PERFORMANCE_REPORT" || echo "  [N/A]" | tee -a "$PERFORMANCE_REPORT"

echo "" | tee -a "$PERFORMANCE_REPORT"
echo "Redis Data Size:" | tee -a "$PERFORMANCE_REPORT"
kubectl exec -n "$NAMESPACE" redis-0 -- du -sh /data 2>/dev/null | tee -a "$PERFORMANCE_REPORT" || echo "  [N/A]" | tee -a "$PERFORMANCE_REPORT"

# 6. Network Performance
echo -e "\n${MAGENTA}═══ 6. NETWORK DIAGNOSTICS ═══${NC}"

echo "Service DNS Resolution:" | tee -a "$PERFORMANCE_REPORT"
CORE_POD=$(kubectl get pod -n "$NAMESPACE" -l app=hypercode-core -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ ! -z "$CORE_POD" ]; then
    kubectl exec -n "$NAMESPACE" "$CORE_POD" -- nslookup postgres 2>/dev/null | grep -A2 "Name:" | head -3 | tee -a "$PERFORMANCE_REPORT" || echo "  [Unable to resolve DNS]" | tee -a "$PERFORMANCE_REPORT"
fi

echo "" | tee -a "$PERFORMANCE_REPORT"
echo "Network Policy Status:" | tee -a "$PERFORMANCE_REPORT"
kubectl get networkpolicy -n "$NAMESPACE" --no-headers 2>/dev/null | tee -a "$PERFORMANCE_REPORT" || echo "  No policies found" | tee -a "$PERFORMANCE_REPORT"

# 7. Application Response Times
echo -e "\n${MAGENTA}═══ 7. APPLICATION LATENCY TESTS ═══${NC}"

if [ ! -z "$CORE_POD" ]; then
    echo "HyperCode Core Response Time (5 requests):" | tee -a "$PERFORMANCE_REPORT"
    for i in {1..5}; do
        start=$(date +%s%N)
        kubectl exec -n "$NAMESPACE" "$CORE_POD" -- curl -s http://localhost:8000/health > /dev/null 2>&1 || true
        end=$(date +%s%N)
        elapsed=$(( (end - start) / 1000000 ))
        echo "  Request $i: ${elapsed}ms" | tee -a "$PERFORMANCE_REPORT"
    done
fi

# 8. Log Volume Analysis
echo -e "\n${MAGENTA}═══ 8. LOG VOLUME ANALYSIS ═══${NC}"

echo "Pod Log Sizes:" | tee -a "$PERFORMANCE_REPORT"
for pod in $(kubectl get pods -n "$NAMESPACE" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null); do
    size=$(kubectl logs -n "$NAMESPACE" "$pod" 2>/dev/null | wc -c)
    echo "  $pod: $(numfmt --to=iec-i --suffix=B $size 2>/dev/null || echo "$size bytes")" | tee -a "$PERFORMANCE_REPORT"
done

# 9. Deployment Status
echo -e "\n${MAGENTA}═══ 9. DEPLOYMENT STATUS SUMMARY ═══${NC}"

kubectl get deployments -n "$NAMESPACE" -o custom-columns=NAME:.metadata.name,READY:.status.readyReplicas,DESIRED:.spec.replicas,UP-TO-DATE:.status.updatedReplicas,AVAILABLE:.status.availableReplicas --no-headers | tee -a "$PERFORMANCE_REPORT"

echo "" | tee -a "$PERFORMANCE_REPORT"
echo "StatefulSet Status:" | tee -a "$PERFORMANCE_REPORT"
kubectl get statefulsets -n "$NAMESPACE" -o custom-columns=NAME:.metadata.name,READY:.status.readyReplicas,DESIRED:.spec.replicas --no-headers | tee -a "$PERFORMANCE_REPORT"

# 10. Event Log
echo -e "\n${MAGENTA}═══ 10. RECENT SYSTEM EVENTS (Last 20) ═══${NC}"

kubectl get events -n "$NAMESPACE" --sort-by='.lastTimestamp' 2>/dev/null | tail -20 | tee -a "$PERFORMANCE_REPORT"

# 11. Recommendations
echo -e "\n${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║            DETAILED RECOMMENDATIONS                       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}\n" | tee -a "$PERFORMANCE_REPORT"

cat >> "$PERFORMANCE_REPORT" << 'EOF'

PRODUCTION DEPLOYMENT RECOMMENDATIONS
═════════════════════════════════════

1. DATABASE OPTIMIZATION
─────────────────────────
  • Enable PostgreSQL autovacuum: Check AUTOVACUUM setting
    kubectl exec -n hypercode postgres-0 -- psql -U postgres -c "SHOW autovacuum;"
  
  • Create indexes on frequently queried columns
    kubectl exec -n hypercode postgres-0 -- psql -U postgres hypercode
    # Then: CREATE INDEX idx_name ON table_name(column_name);
  
  • Enable query logging for slow queries (log_min_duration_statement)
  
  • Regular backups:
    kubectl exec -n hypercode postgres-0 -- pg_dump -U postgres hypercode > backup.sql
  
  • Monitor connection count (Default max: 100)
    Increase if needed: ALTER SYSTEM SET max_connections = 200;

2. REDIS OPTIMIZATION
──────────────────────
  • Monitor eviction policy (currently: allkeys-lru)
    Alternatives: volatile-lru (only expire keys with TTL)
  
  • Increase maxmemory if needed:
    kubectl exec -n hypercode redis-0 -- redis-cli config get maxmemory
    kubectl exec -n hypercode redis-0 -- redis-cli config set maxmemory 1gb
  
  • Enable persistence:
    Current: RDB snapshots every 60 seconds after 1000 changes
    Consider: AOF (Append-Only File) for higher durability
  
  • Monitor keyspace:
    kubectl exec -n hypercode redis-0 -- redis-cli info keyspace

3. RESOURCE ALLOCATION
──────────────────────
  • Monitor CPU throttling:
    kubectl get pods -n hypercode -o json | jq '.items[].spec.containers[].resources'
  
  • Current resource limits:
    - HyperCode Core: 2CPU / 4GB RAM
    - Celery Worker: 1CPU / 1GB RAM
    - Dashboard: 500mCPU / 512MB RAM
  
  • Adjust based on monitoring (kubectl top pods)
  
  • Enable QoS Guaranteed for critical pods:
    Set requests = limits for predictable performance

4. SECURITY HARDENING
──────────────────────
  • Update all secrets (currently using defaults):
    ✗ POSTGRES_PASSWORD: changeme123
    ✗ HYPERCODE_JWT_SECRET: jwt-secret-key-change-me
    ✗ MINIO_ROOT_PASSWORD: minioadmin123
    ✗ API_KEY: dev-master-key
  
  • Commands to update secrets:
    kubectl patch secret hypercode-secrets -n hypercode \
      -p '{"data":{"POSTGRES_PASSWORD":"'$(echo -n 'strong-password' | base64)'"}}'
  
  • Enable Pod Security Standards:
    kubectl label namespace hypercode pod-security.kubernetes.io/enforce=restricted
  
  • Implement RBAC:
    Create ServiceAccount with minimal permissions
    kubectl create serviceaccount hypercode-sa -n hypercode
    kubectl create role hypercode-role -n hypercode --verb=get,list,watch --resource=pods
  
  • Use NetworkPolicies (already configured):
    Review and test: kubectl get networkpolicy -n hypercode

5. MONITORING & ALERTING
─────────────────────────
  • Configure Prometheus scrape intervals:
    Current: 15s (lower for production: 30s for stability)
  
  • Set up alerting rules:
    Add PrometheusRule CRD with alerts for:
    - Pod crash loops
    - High memory usage (>80%)
    - High CPU usage (>70%)
    - Database connection pool exhaustion
    - Redis eviction increases
  
  • Grafana dashboards:
    Import: https://grafana.com/grafana/dashboards/1860/ (Node Exporter)
    Import: https://grafana.com/grafana/dashboards/3662/ (Prometheus)
    Create custom dashboards for application metrics

6. HIGH AVAILABILITY
─────────────────────
  • Multi-replica deployment:
    HyperCode Core: ✓ 2 replicas (should be ≥3 for HA)
    Celery Worker: ✓ 2 replicas
    Dashboard: ✓ 2 replicas
    PostgreSQL: ✗ 1 replica (single point of failure)
  
  • Increase replicas:
    kubectl scale deployment hypercode-core --replicas=3 -n hypercode
    kubectl scale deployment celery-worker --replicas=3 -n hypercode
  
  • Pod Disruption Budgets:
    ✓ Configured for hypercode-core and dashboard
    Add for other critical services
  
  • Node affinity:
    Distribute pods across nodes to prevent single-node failure
    Add podAntiAffinity rules in deployments

7. STORAGE & BACKUP
────────────────────
  • Backup strategy:
    - Database: Daily pg_dump backups to external storage
    - Configuration: Backup Kubernetes manifests to Git
    - Data: Velero for cluster-wide backups
  
  • Implement automated backups:
    Example cronjob:
    kubectl create cronjob -n hypercode postgres-backup \
      --schedule="0 2 * * *" \
      --image=postgres:15-alpine \
      -- /bin/sh -c 'pg_dump -h postgres -U postgres hypercode | gzip > /backup/hypercode_$(date +%Y%m%d).sql.gz'
  
  • Storage class:
    Verify fast, reliable storage (SSD recommended for databases)
    Test: fio tool for storage performance testing

8. SCALING CONFIGURATION
──────────────────────────
  • HorizontalPodAutoscaler: ✓ Configured
    - HyperCode Core: Min 2, Max 10 (CPU 70%, Memory 80%)
    - Dashboard: Min 2, Max 5 (CPU 70%)
  
  • Performance targets:
    - CPU scaling threshold: 70% (consider reducing to 50% for faster scale-up)
    - Memory scaling threshold: 80%
  
  • Cost optimization:
    Use cluster autoscaler for node-level scaling
    Set appropriate pod requests/limits to maximize bin-packing

9. LOGGING & TRACING
─────────────────────
  • Loki configuration: ✓ Deployed
    Retention period: Check current (default: 744h = 31 days)
    Consider: Shorter retention for cost, longer for compliance
  
  • Tempo traces: ✓ Deployed
    Sampling rate: Adjust for volume control (default: sample 100%)
    Consider: 10% sampling in production to reduce storage
  
  • Application logging:
    Set log level to WARN for production (currently: DEBUG likely)
    Forward logs to centralized logging (Loki configured)
  
  • Log rotation:
    Verify log rotation is configured for containers
    Check docker-compose.yml: max-size and max-file settings

10. INGRESS & NETWORKING
──────────────────────────
  • Domain configuration:
    Update ingress with actual domains:
    kubectl edit ingress hypercode-ingress -n hypercode
    Current placeholders: *.example.com
  
  • SSL/TLS certificates:
    Install cert-manager:
    kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
    
    Update ingress annotation:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  
  • DNS setup:
    Create A/CNAME records pointing to ingress IP/hostname
    Test: nslookup hypercode.example.com
  
  • API rate limiting:
    Consider: nginx-ingress rate limit annotations
    Example: nginx.ingress.kubernetes.io/limit-rps: "10"

11. DISASTER RECOVERY
───────────────────────
  • RTO (Recovery Time Objective): Target 4 hours
  • RPO (Recovery Point Objective): Target 1 hour
  
  • Backup testing:
    Monthly restore test to verify backups work
    Document restore procedures
  
  • Failover plan:
    Multi-region deployment (future consideration)
    Documented runbooks for common failures
  
  • Velero installation (cluster-wide backup):
    helm repo add vmware-tanzu https://helm.tanzu.vmware.com
    helm install velero vmware-tanzu/velero -n velero --create-namespace

12. COST OPTIMIZATION
──────────────────────
  • Resource requests:
    Increase specificity to improve scheduling efficiency
    Use requests for better QoS
  
  • Node sizing:
    Right-size nodes to workload (monitor utilization)
    Use spot instances for fault-tolerant workloads (Celery workers)
  
  • Storage costs:
    Archive old data (Loki retention, Prometheus TSDB)
    Use cheaper storage tiers for backups
  
  • Registry costs:
    Use ECR/GCR pull-through cache to reduce egress
    Implement image garbage collection

CRITICAL ACTION ITEMS (Do This First)
══════════════════════════════════════

Priority 1 - Security (DO IMMEDIATELY):
  ☐ Update all default secrets
  ☐ Rotate API keys
  ☐ Enable RBAC
  ☐ Review network policies

Priority 2 - High Availability (DO WITHIN 1 WEEK):
  ☐ Scale PostgreSQL to 3 replicas with streaming replication
  ☐ Increase core replicas to 3
  ☐ Test failover scenarios
  ☐ Implement Pod Disruption Budgets for all critical services

Priority 3 - Backup & Recovery (DO WITHIN 2 WEEKS):
  ☐ Implement automated database backups
  ☐ Test restore procedures
  ☐ Set up Velero for cluster backups
  ☐ Document disaster recovery procedures

Priority 4 - Monitoring (DO WITHIN 1 MONTH):
  ☐ Configure Prometheus alerting rules
  ☐ Create Grafana dashboards for key metrics
  ☐ Set up log aggregation alerts
  ☐ Implement application performance monitoring (APM)

PERFORMANCE TUNING COMMANDS
═════════════════════════════

# View resource utilization
kubectl top pods -n hypercode --sort-by=memory
kubectl top nodes

# Check HPA status and scaling history
kubectl get hpa -n hypercode -o wide
kubectl describe hpa hypercode-core-hpa -n hypercode

# Monitor pod scheduling
kubectl get events -n hypercode --sort-by='.lastTimestamp'

# Check resource quotas
kubectl describe resourcequota hypercode-quota -n hypercode

# View metrics (if prometheus-adapter installed)
kubectl get --raw /apis/custom.metrics.k8s.io/v1beta1 | jq .

# Database performance
kubectl exec -n hypercode postgres-0 -- psql -U postgres -c "\dt+"
kubectl exec -n hypercode postgres-0 -- psql -U postgres -c "SELECT * FROM pg_stat_statements LIMIT 10;"

# Redis performance
kubectl exec -n hypercode redis-0 -- redis-cli --stat

EOF

# Final Summary
echo -e "\n${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║            VERIFICATION COMPLETE                          ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}\n"

echo -e "Report saved to: ${GREEN}$PERFORMANCE_REPORT${NC}"
echo -e "View detailed recommendations: ${YELLOW}cat $PERFORMANCE_REPORT${NC}\n"

cat "$PERFORMANCE_REPORT"
