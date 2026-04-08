# HyperCode Kubernetes Troubleshooting Guide

## Quick Start: Run Health Checks

```bash
# Make scripts executable
chmod +x ./k8s/health_check.sh
chmod +x ./k8s/post_deployment_check.sh

# Run full health check
./k8s/health_check.sh

# Run post-deployment verification (takes 5-10 minutes)
./k8s/post_deployment_check.sh

# View detailed reports
cat ./k8s/health_check_report.txt
cat ./k8s/issues_and_recommendations.txt
cat ./k8s/performance_report.txt
```

## Common Issues & Solutions

### 1. Pods Stuck in "Pending" State

**Diagnosis:**
```bash
kubectl describe pod <pod-name> -n hypercode
```

**Common Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| **Insufficient CPU/Memory** | Scale up node or reduce resource requests:<br/>`kubectl set resources deployment hypercode-core -n hypercode --limits=cpu=1000m,memory=2Gi --requests=cpu=250m,memory=512Mi` |
| **PVC not bound** | `kubectl get pvc -n hypercode` - Check if status is "Pending"<br/>Create PVCs: `kubectl apply -f k8s/03-pvcs.yaml` |
| **Image pull failure** | `kubectl describe pod <pod> -n hypercode` - Check Events section<br/>Verify image exists and credentials are correct |
| **Node not ready** | `kubectl get nodes` - Check node status<br/>If NotReady: `kubectl describe node <node-name>` |
| **Node selector mismatch** | Remove node selectors or add labels to nodes:<br/>`kubectl label node <node-name> workload=hypercode` |

### 2. Pods in "CrashLoopBackOff"

**Diagnosis:**
```bash
kubectl logs -n hypercode <pod-name> --tail=50
kubectl logs -n hypercode <pod-name> --previous  # Last run's logs
kubectl describe pod <pod-name> -n hypercode
```

**Common Causes:**

**PostgreSQL CrashLoop:**
```bash
# Check logs
kubectl logs -n hypercode postgres-0

# Verify PVC is mounted
kubectl get pvc -n hypercode postgres-pvc

# Check initDB
kubectl exec -n hypercode postgres-0 -- ls -la /var/lib/postgresql/data/

# Reset if corrupted
kubectl exec -n hypercode postgres-0 -- rm -rf /var/lib/postgresql/data/*
kubectl delete pod postgres-0 -n hypercode
```

**Application CrashLoop:**
```bash
# Check environment variables
kubectl describe pod <core-pod> -n hypercode | grep -A 50 "Environment:"

# Check database connectivity
kubectl exec -n hypercode <core-pod> -- \
  psql -h postgres -U postgres -d hypercode -c "SELECT 1"

# Check for config issues
kubectl get configmap hypercode-config -n hypercode -o yaml
```

### 3. Service Cannot Connect to Database

**Diagnosis:**
```bash
# Test connectivity from application pod
kubectl exec -n hypercode <app-pod> -- nc -zv postgres 5432

# Test DNS resolution
kubectl exec -n hypercode <app-pod> -- nslookup postgres.hypercode.svc.cluster.local

# Verify database is running
kubectl get pod postgres-0 -n hypercode -o wide
```

**Solutions:**

```bash
# Recreate postgres with proper initialization
kubectl delete statefulset postgres -n hypercode
kubectl delete pvc postgres-pvc -n hypercode
kubectl apply -f k8s/04-postgres.yaml
kubectl wait --for=condition=ready pod postgres-0 -n hypercode --timeout=300s

# Or if data is important, just restart the pod
kubectl delete pod postgres-0 -n hypercode
# StatefulSet will recreate it

# Verify connection
kubectl exec -n hypercode postgres-0 -- psql -U postgres -c "SELECT 1"

# Check environment in app pod
kubectl exec -n hypercode <app-pod> -- env | grep DATABASE
```

### 4. Out of Memory (OOM) Killed

**Diagnosis:**
```bash
# Check memory usage
kubectl top pods -n hypercode --sort-by=memory

# Check pod events
kubectl describe pod <pod-name> -n hypercode | grep -i "memory\|oom"

# Check node available memory
kubectl describe node <node-name> | grep -i "memory"
```

**Solutions:**

```bash
# Increase memory limit for deployment
kubectl set resources deployment hypercode-core -n hypercode \
  --limits=memory=4Gi --requests=memory=2Gi

# Or edit deployment directly
kubectl edit deployment hypercode-core -n hypercode
# Change: limits.memory and requests.memory

# Scale down other services if node is memory-constrained
kubectl scale deployment dashboard --replicas=1 -n hypercode

# Add more nodes to cluster (cloud-specific)
# AWS: aws eks update-nodegroup-config ...
# GCP: gcloud container clusters resize ...
```

### 5. Persistent Volume Not Mounting

**Diagnosis:**
```bash
kubectl get pvc -n hypercode -o wide
kubectl describe pvc postgres-pvc -n hypercode
kubectl get pv

# Check pod mount details
kubectl describe pod postgres-0 -n hypercode | grep -A 20 "Mounts:"
```

**Solutions:**

```bash
# Check storage class
kubectl get storageclass
kubectl describe storageclass standard

# Verify PV is created
kubectl get pv | grep hypercode

# If PVC is pending (no PV bound):
# 1. Check storage class exists
kubectl get storageclass standard

# 2. If not, create one
kubectl apply -f - <<EOF
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: standard
provisioner: kubernetes.io/aws-ebs  # Change based on provider
parameters:
  type: gp2
  iops: "100"
  fstype: ext4
EOF

# 3. Delete and recreate PVC
kubectl delete pvc postgres-pvc -n hypercode
kubectl apply -f k8s/03-pvcs.yaml
```

### 6. Ingress Not Working / No External IP

**Diagnosis:**
```bash
kubectl get ingress -n hypercode -o wide
kubectl describe ingress hypercode-ingress -n hypercode
kubectl get ingressclass
```

**Solutions:**

```bash
# Check if ingress controller is installed
kubectl get pods -n ingress-nginx

# If not installed, install NGINX ingress controller
kubectl apply -f \
  https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/cloud/deploy.yaml

# Wait for LoadBalancer IP
kubectl get ingress -n hypercode --watch

# Update DNS records with IP
# Once IP is assigned, point DNS to it
nslookup hypercode.example.com

# Test ingress
curl http://hypercode.example.com
```

### 7. High CPU Usage

**Diagnosis:**
```bash
# Find top CPU consumers
kubectl top pods -n hypercode --sort-by=cpu

# Check specific pod
kubectl describe pod <pod-name> -n hypercode

# Monitor real-time
kubectl top pods -n hypercode --sort-by=cpu --watch
```

**Solutions:**

```bash
# Check what's consuming CPU (inside pod)
kubectl exec -n hypercode <pod-name> -- top -n 1

# For application, enable profiling
kubectl exec -n hypercode <app-pod> -- \
  curl -s http://localhost:8000/debug/pprof/ | head -20

# Increase resource limits if pod is being throttled
kubectl set resources deployment hypercode-core -n hypercode \
  --limits=cpu=2000m --requests=cpu=500m

# Enable HPA if not scaling
kubectl autoscale deployment hypercode-core -n hypercode \
  --min=2 --max=10 --cpu-percent=70
```

### 8. Database Replication Issues

**Diagnosis:**
```bash
# Check replication status
kubectl exec -n hypercode postgres-0 -- \
  psql -U postgres -c "SELECT * FROM pg_stat_replication;"

# Check WAL files
kubectl exec -n hypercode postgres-0 -- \
  ls -lh /var/lib/postgresql/data/pg_wal/ | head -20

# Check replication slots
kubectl exec -n hypercode postgres-0 -- \
  psql -U postgres -c "SELECT * FROM pg_replication_slots;"
```

**Solutions:**

```bash
# If replication is lagging, increase WAL buffer
kubectl exec -n hypercode postgres-0 -- psql -U postgres << EOF
ALTER SYSTEM SET wal_buffers = '16MB';
SELECT pg_reload_conf();
EOF

# If slot is failing, reset it
kubectl exec -n hypercode postgres-0 -- \
  psql -U postgres -c "SELECT pg_drop_replication_slot('slot_name');"

# Restart PostgreSQL
kubectl delete pod postgres-0 -n hypercode
```

### 9. Redis Connection Timeout

**Diagnosis:**
```bash
# Test redis connectivity
kubectl exec -n hypercode <app-pod> -- redis-cli -h redis ping

# Check redis metrics
kubectl exec -n hypercode redis-0 -- redis-cli info stats

# Check connection count
kubectl exec -n hypercode redis-0 -- redis-cli client list | wc -l
```

**Solutions:**

```bash
# Increase maxconnections if needed (default: 10000)
kubectl exec -n hypercode redis-0 -- \
  redis-cli config set maxclients 20000

# Clear old connections
kubectl exec -n hypercode redis-0 -- \
  redis-cli client kill TYPE normal

# Monitor connections
kubectl exec -n hypercode redis-0 -- \
  redis-cli --stat
```

### 10. Network Policy Blocking Traffic

**Diagnosis:**
```bash
# Check network policies
kubectl get networkpolicy -n hypercode

# Describe policy
kubectl describe networkpolicy hypercode-network-policy -n hypercode

# Test connectivity between pods
kubectl exec -n hypercode <pod1> -- nc -zv <pod2> 5432
```

**Solutions:**

```bash
# Temporarily disable network policy for testing
kubectl delete networkpolicy hypercode-network-policy -n hypercode

# Test if connectivity works
kubectl exec -n hypercode <pod1> -- nc -zv <pod2> 5432

# If it works, review and fix the policy
kubectl apply -f k8s/11-ingress-network-policy.yaml

# Or modify specific policy rules
kubectl edit networkpolicy hypercode-network-policy -n hypercode
```

### 11. Certificate/SSL Issues

**Diagnosis:**
```bash
# Check certificate status
kubectl get certificate -n hypercode

# Describe cert
kubectl describe certificate hypercode-tls -n hypercode

# Check ingress TLS
kubectl get ingress hypercode-ingress -n hypercode -o yaml | grep -A 10 "tls:"
```

**Solutions:**

```bash
# Install cert-manager (if not installed)
kubectl apply -f \
  https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Wait for cert-manager to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/instance=cert-manager -n cert-manager --timeout=300s

# Create ClusterIssuer for Let's Encrypt
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF

# Verify certificate is created
kubectl get certificate -n hypercode --watch
```

### 12. Application Not Finding Dependencies

**Diagnosis:**
```bash
# Check if all services are running
kubectl get svc -n hypercode

# Test service DNS from pod
kubectl exec -n hypercode <pod> -- nslookup <service>

# Check service endpoints
kubectl get endpoints -n hypercode
```

**Solutions:**

```bash
# Verify services exist and have endpoints
kubectl get svc -n hypercode -o wide
kubectl get endpoints -n hypercode

# Create missing services
kubectl apply -f k8s/04-postgres.yaml  # Creates postgres service
kubectl apply -f k8s/05-redis.yaml     # Creates redis service
# ... etc for all services

# Check DNS is working
kubectl run -it --rm debug --image=busybox:1.28 --restart=Never -n hypercode \
  -- nslookup postgres.hypercode.svc.cluster.local
```

## Debugging Commands Cheatsheet

```bash
# View comprehensive pod information
kubectl get pod <pod> -n hypercode -o yaml

# Stream logs from all pods with label
kubectl logs -n hypercode -l app=hypercode-core --all-containers --follow

# Get into a pod for debugging
kubectl exec -it <pod> -n hypercode -- /bin/bash

# Copy file from pod
kubectl cp hypercode/<pod>:/path/to/file ./local-file

# Get metric data
kubectl top pod <pod> -n hypercode
kubectl describe node <node-name>

# Check events
kubectl get events -n hypercode --sort-by='.lastTimestamp'

# See resource usage
kubectl api-resources --verbs=list --namespaced=true

# Troubleshoot service discovery
kubectl exec -n hypercode <pod> -- cat /etc/resolv.conf
kubectl exec -n hypercode <pod> -- getent hosts <service>

# Check pod scheduling
kubectl describe pod <pod> -n hypercode | grep -A 20 "Conditions:"
```

## Emergency Recovery

### Restart All Pods

```bash
# Restart all deployments
kubectl rollout restart deployment -n hypercode

# Wait for all pods to be ready
kubectl wait --for=condition=ready pod --all -n hypercode --timeout=300s
```

### Emergency Database Reset (DATA LOSS!)

```bash
# WARNING: This deletes all database data
kubectl delete pvc postgres-pvc -n hypercode
kubectl delete pod postgres-0 -n hypercode
# Wait, then apply postgres manifest
kubectl apply -f k8s/04-postgres.yaml
```

### Clear All Redis Data

```bash
kubectl exec -n hypercode redis-0 -- redis-cli flushall
```

### Force Delete Stuck Pod

```bash
kubectl delete pod <pod> -n hypercode --grace-period=0 --force
```

## Performance Optimization

```bash
# Optimize database queries
kubectl exec -n hypercode postgres-0 -- \
  psql -U postgres -c "ANALYZE;"

# Optimize indexes
kubectl exec -n hypercode postgres-0 -- \
  psql -U postgres -c "REINDEX DATABASE hypercode;"

# Clear Redis cache
kubectl exec -n hypercode redis-0 -- redis-cli flushdb

# Restart application gracefully
kubectl rollout restart deployment hypercode-core -n hypercode

# Check rollout status
kubectl rollout status deployment hypercode-core -n hypercode

# View rollout history
kubectl rollout history deployment hypercode-core -n hypercode
```

## Monitoring & Observability

```bash
# Access Prometheus
kubectl port-forward -n hypercode svc/prometheus 9090:9090
# Visit: http://localhost:9090

# Access Grafana
kubectl port-forward -n hypercode svc/grafana 3001:3000
# Visit: http://localhost:3001 (admin/password)

# View application logs
kubectl logs -n hypercode -l app=hypercode-core --tail=100 --follow

# Check all pod statuses
kubectl get pods -n hypercode -o wide

# Get pod restart count
kubectl get pods -n hypercode -o custom-columns=NAME:.metadata.name,RESTARTS:.status.containerStatuses[0].restartCount

# Find resource-hungry pods
kubectl top pods -n hypercode --sort-by=memory
```

## Useful Links

- [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
- [Kubernetes Troubleshooting](https://kubernetes.io/docs/tasks/debug-application-cluster/)
- [PostgreSQL on Kubernetes](https://kubernetes.io/docs/tasks/run-application/run-replicated-stateful-application/)
