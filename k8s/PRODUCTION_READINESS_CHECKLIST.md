# HyperCode Kubernetes Production Readiness Checklist

## Pre-Deployment Checklist

### Infrastructure Setup
- [ ] Kubernetes cluster provisioned (1.20+)
- [ ] Multiple nodes available (minimum 3 for HA)
- [ ] Storage class configured and set as default
- [ ] Metrics server installed (`kubectl get deployment metrics-server -n kube-system`)
- [ ] Ingress controller installed
- [ ] cert-manager installed (for TLS)

### Verify with:
```bash
kubectl get nodes -o wide
kubectl get storageclass
kubectl get ingressclass
kubectl get pods -n kube-system | grep metrics-server
kubectl get pods -n ingress-nginx
kubectl get pods -n cert-manager
```

### Secrets & Configuration
- [ ] All default secrets updated (POSTGRES_PASSWORD, JWT_SECRET, API_KEY, etc.)
- [ ] API keys configured (PERPLEXITY_API_KEY, OPENAI_API_KEY)
- [ ] Discord credentials added (DISCORD_TOKEN, DISCORD_GUILD_ID)
- [ ] MinIO credentials set to strong values
- [ ] SSL/TLS certificates ready or Let's Encrypt configured

### Validate with:
```bash
# Create dummy secret to verify
kubectl create secret generic test-secret -n hypercode --from-literal=test=value --dry-run=client -o yaml

# Check secret encoding (should not be plaintext in etcd)
kubectl get secret hypercode-secrets -n hypercode -o jsonpath='{.data.API_KEY}' | base64 -d | head -c 20
```

### Network & DNS
- [ ] Domain names ready (hypercode.example.com, api.hypercode.example.com, etc.)
- [ ] DNS records pointing to ingress IP/hostname
- [ ] SSL certificates acquired or auto-renewal configured
- [ ] Network policies reviewed and tested
- [ ] Firewall rules allowing ingress traffic

### Validate with:
```bash
nslookup hypercode.example.com
curl -I https://hypercode.example.com
```

## Deployment Checklist

### Pre-Deployment Backup
- [ ] Existing data backed up (if migrating)
- [ ] Kubernetes manifests committed to Git
- [ ] Environment configuration documented

### Step-by-Step Deployment
- [ ] Namespace created
- [ ] ConfigMaps deployed
- [ ] Secrets deployed
- [ ] PersistentVolumeClaims created
- [ ] PostgreSQL StatefulSet deployed and verified ready
- [ ] Redis StatefulSet deployed and verified ready
- [ ] HyperCode Core Deployment deployed
- [ ] Celery Worker Deployment deployed
- [ ] Dashboard Deployment deployed
- [ ] Observability stack deployed (Prometheus, Grafana, etc.)
- [ ] Logging & Tracing deployed (Loki, Tempo)
- [ ] Data services deployed (MinIO, ChromaDB, Ollama)
- [ ] Ingress configured with proper domains
- [ ] Network policies applied
- [ ] Auto-scaling (HPA) configured

### Verify deployment:
```bash
# Run health check script
./k8s/health_check.sh

# Check all pods running
kubectl get pods -n hypercode

# Check all services
kubectl get svc -n hypercode

# Check ingress
kubectl get ingress -n hypercode
```

## Post-Deployment Verification

### 1. Connectivity Tests
- [ ] API responds to health checks: `curl http://api:8000/health`
- [ ] Dashboard accessible via ingress
- [ ] Database connectivity verified
- [ ] Redis connectivity verified
- [ ] Services can communicate internally

```bash
./k8s/post_deployment_check.sh
```

### 2. Data Persistence
- [ ] Database data persists after pod restart
- [ ] Redis data persists after pod restart
- [ ] File uploads stored in MinIO
- [ ] Logs aggregated in Loki

```bash
# Test database persistence
kubectl delete pod postgres-0 -n hypercode
# Wait for recreation
kubectl exec -n hypercode postgres-0 -- psql -U postgres hypercode -c "SELECT COUNT(*) FROM information_schema.tables;"

# Test Redis persistence
kubectl delete pod redis-0 -n hypercode
# Check if data is restored
kubectl exec -n hypercode redis-0 -- redis-cli dbsize
```

### 3. High Availability
- [ ] Multiple replicas of all stateless services
- [ ] Pod Disruption Budgets configured
- [ ] HPA scaling tested (simulate high load)
- [ ] Pod anti-affinity working (pods distributed across nodes)

```bash
# Test HPA
kubectl get hpa -n hypercode

# Generate load to test scaling
kubectl run -it --rm load-gen --image=busybox:1.28 --restart=Never -n hypercode \
  -- /bin/sh -c 'while true; do wget -q -O- http://hypercode-core:8000/; done'

# Watch pods scale
kubectl get pods -n hypercode --watch
```

### 4. Monitoring & Logging
- [ ] Prometheus scraping all targets
- [ ] Grafana dashboards configured
- [ ] Alerts firing correctly
- [ ] Logs appearing in Loki
- [ ] Traces visible in Tempo

```bash
# Port forward to monitoring
kubectl port-forward -n hypercode svc/prometheus 9090:9090
# Visit http://localhost:9090 to check targets

kubectl port-forward -n hypercode svc/grafana 3001:3000
# Visit http://localhost:3001 (admin/password)
```

### 5. Backup & Recovery
- [ ] Automated database backups running
- [ ] Backup restore procedure tested
- [ ] Volume snapshots configured (if cloud provider supports)
- [ ] Velero backup system operational (if installed)

```bash
# Test database backup
kubectl exec -n hypercode postgres-0 -- \
  pg_dump -U postgres hypercode | gzip > /tmp/backup.sql.gz

# Verify backup
gunzip -c /tmp/backup.sql.gz | head -20
```

### 6. Security
- [ ] RBAC policies configured
- [ ] Network policies restricting traffic
- [ ] Pod Security Standards enforced
- [ ] Container images scanned for vulnerabilities
- [ ] Secrets encrypted at rest (if etcd encryption enabled)
- [ ] Regular security audits scheduled

```bash
# Check RBAC
kubectl get roles,rolebindings -n hypercode

# Check network policies
kubectl get networkpolicy -n hypercode

# View pod security labels
kubectl get namespace hypercode -o yaml | grep pod-security
```

### 7. Resource Limits
- [ ] All pods have resource requests/limits
- [ ] Resource quotas enforced at namespace level
- [ ] No pods requesting unlimited resources
- [ ] CPU and memory appropriately sized

```bash
# Check resource quotas
kubectl describe resourcequota hypercode-quota -n hypercode

# Verify all pods have limits
kubectl get pods -n hypercode -o json | \
  jq '.items[] | select(.spec.containers[].resources.limits == null)'
```

### 8. Scaling & Performance
- [ ] Load testing completed
- [ ] Performance benchmarks documented
- [ ] Auto-scaling limits appropriate
- [ ] Database performance optimized
- [ ] Connection pools sized correctly

```bash
# Run performance check
./k8s/post_deployment_check.sh

# Monitor real-time metrics
watch -n 1 'kubectl top pods -n hypercode --sort-by=memory'
```

## Production Hardening Checklist

### Security Hardening
- [ ] All secrets rotated from defaults
- [ ] API keys restricted to necessary scopes
- [ ] Database password at least 20 characters
- [ ] JWT secret at least 32 characters
- [ ] Pod Security Policy enforced
- [ ] Network policies blocking unexpected traffic
- [ ] Ingress configured with rate limiting
- [ ] CORS headers properly configured

### Commands:
```bash
# Check for insecure defaults
kubectl get secret hypercode-secrets -n hypercode -o yaml | grep -i "changeme\|dev-key\|admin"

# Update insecure values
kubectl patch secret hypercode-secrets -n hypercode -p '{"data":{"POSTGRES_PASSWORD":"'$(echo -n 'YOUR_STRONG_PASSWORD' | base64)'"}}'
```

### Availability Hardening
- [ ] Minimum 3 replicas for stateless services
- [ ] PostgreSQL in HA configuration (Patroni/Streaming Replication)
- [ ] Redis Sentinel or cluster mode
- [ ] Multi-node cluster with redundant master
- [ ] Backup and restore tested within SLA
- [ ] Incident response procedures documented

### Monitoring & Alerting
- [ ] Prometheus retention configured (default: 15 days)
- [ ] Alert thresholds tuned based on baselines
- [ ] On-call rotation and escalation paths defined
- [ ] Incident tracking system integrated
- [ ] Alert notifications configured (email, Slack, PagerDuty)

### Commands:
```bash
# Check alert rules
kubectl get PrometheusRule -n hypercode
kubectl describe PrometheusRule hypercode-alerts -n hypercode

# View Prometheus targets
kubectl port-forward -n hypercode svc/prometheus 9090:9090
# Check http://localhost:9090/targets
```

## Operational Checklist

### Daily Operations
- [ ] Monitor dashboard for alerts
- [ ] Check pod restart counts
- [ ] Verify backup completion
- [ ] Review error logs
- [ ] Check disk space usage

```bash
# Daily health check
./k8s/health_check.sh

# Check for issues
kubectl describe nodes
kubectl get events -n hypercode --sort-by='.lastTimestamp' | tail -20
```

### Weekly Operations
- [ ] Review resource utilization trends
- [ ] Test restore procedures
- [ ] Update container images
- [ ] Review and rotate logs
- [ ] Security audit

```bash
# Weekly performance review
./k8s/post_deployment_check.sh

# Check for pending updates
kubectl describe nodes | grep -A 5 "Allocatable"
```

### Monthly Operations
- [ ] Disaster recovery drill
- [ ] Capacity planning review
- [ ] Performance tuning
- [ ] Security updates
- [ ] Documentation review and update

```bash
# Monthly comprehensive check
./k8s/health_check.sh
./k8s/post_deployment_check.sh

# Review alerting and adjust thresholds if needed
kubectl get PrometheusRule -n hypercode -o yaml
```

## SLA & Performance Targets

### Service Level Objectives (SLOs)
| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| API Availability | 99.9% | < 99.8% |
| API Response Time (p99) | 200ms | > 500ms |
| API Error Rate | < 0.1% | > 0.5% |
| Database Response Time | < 50ms | > 100ms |
| Cache Hit Rate | > 95% | < 90% |

### Error Budget
- Monthly error budget: 43 minutes
- Reserve for: deployments, updates, maintenance

### Capacity Planning
- CPU utilization target: 70% (reserve 30% for spikes)
- Memory utilization target: 80% (reserve 20% for overflow)
- Disk utilization target: 70% (maintain 30% free space)
- Network utilization target: 60% (reserve 40% for peaks)

## Runbooks for Common Incidents

### Database Down
1. Check PostgreSQL pod status: `kubectl get pod postgres-0 -n hypercode`
2. View logs: `kubectl logs postgres-0 -n hypercode --tail=50`
3. If corrupted, resync from replica (if available)
4. If single replica, restore from backup
5. Estimated RTO: 15-30 minutes

### Redis Down
1. Check Redis pod status: `kubectl get pod redis-0 -n hypercode`
2. Check volume: `kubectl describe pvc redis-pvc -n hypercode`
3. Restart if not corrupted: `kubectl delete pod redis-0 -n hypercode`
4. Application should have fallback to direct database
5. Estimated RTO: 5 minutes

### High CPU Usage
1. Identify noisy neighbor: `kubectl top pods -n hypercode --sort-by=cpu`
2. Check pod logs for exceptions
3. Scale deployment if legitimate load: `kubectl scale deployment <name> --replicas=5`
4. If spike, wait for HPA to scale automatically
5. Estimated resolution: 1-5 minutes

### Disk Full
1. Check usage: `kubectl exec -n hypercode postgres-0 -- df -h`
2. Identify large files/tables
3. Archive old data (logs, traces, metrics)
4. Expand PVC if needed (varies by provider)
5. Clean up old backups
6. Estimated RTO: 30-60 minutes

### Certificate Expiration
1. Check cert status: `kubectl get certificate -n hypercode`
2. Manually request new cert if auto-renewal failed
3. Update ingress annotation if needed
4. Verify renewal in logs: `kubectl logs -n cert-manager deployment/cert-manager`
5. Estimated RTO: 5-10 minutes

## Compliance Checklist

### Data Protection
- [ ] Encryption at rest enabled for sensitive data
- [ ] Encryption in transit (TLS/HTTPS) enforced
- [ ] Data retention policies configured
- [ ] GDPR compliance (if applicable)
- [ ] PII handling procedures documented

### Audit & Logging
- [ ] API access logged
- [ ] Configuration changes logged
- [ ] Authentication attempts logged
- [ ] Log retention policy enforced
- [ ] Audit logs protected from tampering

### Backup & Recovery
- [ ] RPO (Recovery Point Objective): 1 hour
- [ ] RTO (Recovery Time Objective): 4 hours
- [ ] Backup tested monthly
- [ ] Off-site backup storage
- [ ] Backup encryption enabled

### Disaster Recovery
- [ ] DR runbook documented
- [ ] Secondary site/cluster available (future)
- [ ] Regular DR drills (quarterly)
- [ ] Communication plan for incidents
- [ ] Incident post-mortems conducted

## Checklist Validation Commands

```bash
#!/bin/bash
# Run all validation checks

echo "=== Infrastructure Checks ==="
kubectl get nodes -o wide
kubectl get storageclass
kubectl top nodes 2>/dev/null || echo "Metrics not available"

echo -e "\n=== Deployment Health ==="
kubectl get deployments -n hypercode -o wide
kubectl get statefulsets -n hypercode -o wide

echo -e "\n=== Pod Status ==="
kubectl get pods -n hypercode -o wide

echo -e "\n=== Resource Usage ==="
kubectl top pods -n hypercode --sort-by=memory 2>/dev/null || echo "Metrics not available"

echo -e "\n=== Persistent Volumes ==="
kubectl get pvc -n hypercode -o wide

echo -e "\n=== Services ==="
kubectl get svc -n hypercode -o wide

echo -e "\n=== Ingress ==="
kubectl get ingress -n hypercode -o wide

echo -e "\n=== Health Check Status ==="
kubectl get pods -n hypercode -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.conditions[?(@.type=="Ready")].status}{"\n"}{end}'

echo -e "\n=== Recent Events ==="
kubectl get events -n hypercode --sort-by='.lastTimestamp' | tail -20

echo -e "\n=== Alert Rules ==="
kubectl get PrometheusRule -n hypercode

echo -e "\nProduction readiness checks complete!"
```

Save this as `validate_production.sh` and run: `bash validate_production.sh`

## Post-Incident Checklist

After any production incident:
- [ ] Incident documented with timeline
- [ ] Root cause identified
- [ ] Corrective actions implemented
- [ ] Preventive measures identified
- [ ] Monitoring/alerting gaps addressed
- [ ] Runbook updated
- [ ] Team trained on lessons learned
- [ ] Post-mortem meeting conducted

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| DevOps Lead | | | |
| Security Lead | | | |
| Application Lead | | | |
| Operations Lead | | | |
| Infrastructure Lead | | | |

Once all checklists are complete and sign-offs obtained, the system is production-ready.
