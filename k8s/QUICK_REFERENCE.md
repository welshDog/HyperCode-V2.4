# HyperCode Kubernetes - Quick Reference Guide for Operators

## 🚀 Quick Start

```bash
# Make scripts executable
chmod +x ./k8s/*.sh

# Run comprehensive health check
./k8s/comprehensive_health_check.sh

# Deploy everything
./k8s/deploy.sh

# Run post-deployment checks
./k8s/post_deployment_check.sh

# View detailed troubleshooting guide
cat ./k8s/TROUBLESHOOTING.md
```

## 📊 Monitoring & Access

### Port Forwarding
```bash
# Dashboard (http://localhost:3000)
kubectl port-forward -n hypercode svc/dashboard 3000:3000

# API (http://localhost:8000)
kubectl port-forward -n hypercode svc/hypercode-core 8000:8000

# Grafana (http://localhost:3001) - admin/password
kubectl port-forward -n hypercode svc/grafana 3001:3000

# Prometheus (http://localhost:9090)
kubectl port-forward -n hypercode svc/prometheus 9090:9090

# MinIO Console (http://localhost:9001)
kubectl port-forward -n hypercode svc/minio 9001:9001
```

### Check Status
```bash
# All resources
kubectl get all -n hypercode

# Pods
kubectl get pods -n hypercode -o wide

# Services
kubectl get svc -n hypercode

# Ingress
kubectl get ingress -n hypercode

# Resources
kubectl top pods -n hypercode --sort-by=memory
kubectl top nodes
```

## 🔧 Common Operations

### Scale Deployments
```bash
# Scale HyperCode Core
kubectl scale deployment hypercode-core --replicas=5 -n hypercode

# Scale Celery Workers
kubectl scale deployment celery-worker --replicas=3 -n hypercode

# Scale Dashboard
kubectl scale deployment dashboard --replicas=3 -n hypercode
```

### View Logs
```bash
# Core service logs
kubectl logs -n hypercode deployment/hypercode-core -f

# Last 100 lines
kubectl logs -n hypercode deployment/hypercode-core --tail=100

# Previous container logs (if restarted)
kubectl logs -n hypercode deployment/hypercode-core --previous

# All containers
kubectl logs -n hypercode -l app=hypercode-core --all-containers
```

### Update Secrets
```bash
# Update API key
kubectl patch secret hypercode-secrets -n hypercode \
  -p '{"data":{"API_KEY":"'$(echo -n 'new-value' | base64)'"}}'

# Update password
kubectl patch secret hypercode-secrets -n hypercode \
  -p '{"data":{"POSTGRES_PASSWORD":"'$(echo -n 'strong-password' | base64)'"}}'

# Verify secret
kubectl get secret hypercode-secrets -n hypercode -o yaml
```

### Update ConfigMap
```bash
# Edit ConfigMap
kubectl edit configmap hypercode-config -n hypercode

# Restart deployment to apply changes
kubectl rollout restart deployment hypercode-core -n hypercode
```

### Database Operations
```bash
# Connect to database
kubectl exec -it -n hypercode postgres-0 -- psql -U postgres -d hypercode

# Run query
kubectl exec -n hypercode postgres-0 -- \
  psql -U postgres hypercode -c "SELECT COUNT(*) FROM information_schema.tables;"

# Create backup
kubectl exec -n hypercode postgres-0 -- \
  pg_dump -U postgres hypercode > backup.sql

# Restore backup
kubectl exec -i -n hypercode postgres-0 -- \
  psql -U postgres hypercode < backup.sql
```

### Redis Operations
```bash
# Check Redis status
kubectl exec -n hypercode redis-0 -- redis-cli ping

# Check memory
kubectl exec -n hypercode redis-0 -- redis-cli info memory

# Check keys
kubectl exec -n hypercode redis-0 -- redis-cli dbsize

# Clear cache
kubectl exec -n hypercode redis-0 -- redis-cli flushdb

# Monitor in real-time
kubectl exec -n hypercode redis-0 -- redis-cli --stat
```

## ⚠️ Troubleshooting Quick Fixes

### Pod in CrashLoopBackOff
```bash
# View logs
kubectl logs -n hypercode <pod-name> --tail=50

# Describe pod
kubectl describe pod <pod-name> -n hypercode

# Delete and restart
kubectl delete pod <pod-name> -n hypercode
```

### Service Not Responding
```bash
# Check endpoints
kubectl get endpoints <service> -n hypercode

# Test connectivity
kubectl exec -n hypercode <any-pod> -- nc -zv <service> <port>

# Check network policies
kubectl describe networkpolicy -n hypercode
```

### PVC Not Binding
```bash
# Check PVC status
kubectl get pvc -n hypercode -o wide

# Describe PVC
kubectl describe pvc <pvc-name> -n hypercode

# Check storage class
kubectl get storageclass
```

### Out of Memory
```bash
# Check usage
kubectl top pods -n hypercode --sort-by=memory

# Increase limit
kubectl set resources deployment <name> -n hypercode \
  --limits=memory=4Gi --requests=memory=2Gi
```

### High CPU Usage
```bash
# Find top consumers
kubectl top pods -n hypercode --sort-by=cpu

# Check if throttled
kubectl describe pod <pod> -n hypercode | grep -i cpu

# Increase limit
kubectl set resources deployment <name> -n hypercode \
  --limits=cpu=2000m --requests=cpu=500m
```

## 📋 Maintenance Tasks

### Daily
- [ ] Check pod status: `kubectl get pods -n hypercode`
- [ ] Review alerts in Grafana
- [ ] Check logs for errors: `kubectl logs -n hypercode -l app=hypercode-core --tail=100 | grep -i error`
- [ ] Verify backup completion

### Weekly
- [ ] Review resource utilization
- [ ] Check for pending updates
- [ ] Test restore procedures
- [ ] Update container images if needed

### Monthly
- [ ] Run disaster recovery drill
- [ ] Review and adjust alerting thresholds
- [ ] Capacity planning review
- [ ] Security audit

## 🔐 Security Checklist

- [ ] All default secrets updated
- [ ] API keys rotated
- [ ] Network policies enforced
- [ ] RBAC configured
- [ ] Ingress with TLS enabled
- [ ] Pod security policies applied
- [ ] Regular backups tested

## 📈 Performance Targets

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| API Availability | 99.9% | 99.8% | < 99.5% |
| Response Time (p99) | 200ms | 500ms | > 1s |
| Error Rate | 0.1% | 0.5% | > 1% |
| Pod Restart Rate | 0 | < 0.1/hour | > 1/hour |
| Disk Usage | < 70% | > 70% | > 90% |

## 🚨 Emergency Procedures

### Restart All Services
```bash
kubectl rollout restart deployment -n hypercode
kubectl wait --for=condition=ready pod --all -n hypercode --timeout=300s
```

### Force Delete Stuck Pod
```bash
kubectl delete pod <pod> -n hypercode --grace-period=0 --force
```

### Emergency Scale Down
```bash
kubectl scale deployment --replicas=0 -n hypercode --all
```

### Full Namespace Reset (DATA LOSS!)
```bash
kubectl delete namespace hypercode
kubectl create namespace hypercode
kubectl apply -f k8s/
```

## 📞 Support Resources

### Logs & Monitoring
- Grafana: http://localhost:3001 (admin/password)
- Prometheus: http://localhost:9090
- Pod logs: `kubectl logs -n hypercode <pod>`
- Events: `kubectl get events -n hypercode --sort-by='.lastTimestamp'`

### Documentation
- Deployment Guide: `./k8s/DEPLOYMENT_GUIDE.md`
- Troubleshooting: `./k8s/TROUBLESHOOTING.md`
- Production Readiness: `./k8s/PRODUCTION_READINESS_CHECKLIST.md`
- Health Check Reports: `./k8s/health_check_*.html`

### kubectl Cheat Sheet
```bash
# Get resources
kubectl get <resource> -n hypercode
kubectl describe <resource> <name> -n hypercode

# View recent changes
kubectl get events -n hypercode --sort-by='.lastTimestamp'

# Watch status
kubectl get pods -n hypercode --watch

# Copy file from pod
kubectl cp hypercode/<pod>:/file ./local-file

# Execute command in pod
kubectl exec -it <pod> -n hypercode -- /bin/bash

# View resource usage
kubectl top pods -n hypercode
kubectl top nodes

# Apply configuration
kubectl apply -f manifest.yaml
kubectl patch resource name -n hypercode -p 'patch'

# Delete resources
kubectl delete pod <name> -n hypercode
kubectl delete -f manifest.yaml -n hypercode

# Rollout management
kubectl rollout status deployment/<name> -n hypercode
kubectl rollout restart deployment/<name> -n hypercode
kubectl rollout undo deployment/<name> -n hypercode
```

## 🆘 When Things Go Wrong

1. **Check health**: `./k8s/comprehensive_health_check.sh`
2. **View logs**: `kubectl logs -n hypercode <pod> --tail=50`
3. **Describe resource**: `kubectl describe pod <pod> -n hypercode`
4. **Check events**: `kubectl get events -n hypercode --sort-by='.lastTimestamp'`
5. **Review documentation**: `./k8s/TROUBLESHOOTING.md`
6. **Restart service**: `kubectl delete pod <pod> -n hypercode`
7. **Scale deployment**: `kubectl scale deployment <name> --replicas=0 -n hypercode`
8. **Force delete**: `kubectl delete pod <pod> -n hypercode --grace-period=0 --force`

## 📱 Essential Commands One-Liners

```bash
# Get all failing pods
kubectl get pods -n hypercode --field-selector=status.phase=Failed

# Get all restarting pods
kubectl get pods -n hypercode -o json | jq '.items[] | select(.status.containerStatuses[].restartCount > 0)'

# Stream all logs
kubectl logs -n hypercode -f --all-containers=true -l app=hypercode-core

# Get pod details in YAML
kubectl get pod <name> -n hypercode -o yaml

# Check resource requests vs usage
kubectl describe nodes | grep -A 5 "Allocated resources"

# List all images in use
kubectl get pods -n hypercode -o jsonpath='{.items[*].spec.containers[*].image}' | tr -s '[[:space:]]' '\n'

# Check certificate expiry
kubectl get certificate -n hypercode -o wide

# Find pods with highest memory
kubectl top pods -n hypercode --sort-by=memory | head -10

# Scale all deployments
kubectl scale deployment --all --replicas=3 -n hypercode

# Restart all pods
kubectl rollout restart deployment --all -n hypercode
```

## 🎯 Production Best Practices

### Before Deploying
- [ ] Run health check: `./k8s/comprehensive_health_check.sh`
- [ ] Verify all secrets updated
- [ ] Test backup/restore
- [ ] Review capacity
- [ ] Notify team

### During Deployment
- [ ] Monitor dashboard
- [ ] Watch pod status: `kubectl get pods -n hypercode --watch`
- [ ] Check logs for errors
- [ ] Verify health endpoints responding

### After Deployment
- [ ] Run post-deployment checks: `./k8s/post_deployment_check.sh`
- [ ] Verify all replicas running
- [ ] Test critical paths
- [ ] Review error logs
- [ ] Update runbooks

### Incident Response
- [ ] Check health: `./k8s/comprehensive_health_check.sh`
- [ ] Review logs: `kubectl logs -n hypercode <pod> --tail=100`
- [ ] Identify root cause
- [ ] Document incident
- [ ] Implement fix
- [ ] Conduct post-mortem
- [ ] Update monitoring/alerts

## 📞 Useful Links

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
- [Prometheus Queries](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Grafana Dashboards](https://grafana.com/grafana/dashboards)

---

**Last Updated**: $(date)
**Maintained By**: DevOps Team
**For Support**: Contact ops-team@example.com
