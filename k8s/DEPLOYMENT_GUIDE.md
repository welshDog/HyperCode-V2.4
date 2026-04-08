# Kubernetes Deployment Guide for HyperCode Application

## Overview
This guide explains how to deploy the HyperCode application to a Kubernetes cluster using the provided manifests.

## Prerequisites

1. **Kubernetes Cluster**: 1.20+ (EKS, GKE, AKS, or local Minikube/Docker Desktop)
2. **kubectl**: Latest version configured to access your cluster
3. **Helm** (optional): For advanced deployments
4. **Storage Class**: Ensure your cluster has a default storage class (`standard` by default)
5. **Ingress Controller**: NGINX or similar for ingress
6. **Cert-Manager** (optional): For automatic HTTPS with Let's Encrypt

## File Structure

```
k8s/
├── 00-namespace.yaml              # Kubernetes namespace
├── 01-configmaps.yaml             # Configuration management
├── 02-secrets.yaml                # Sensitive credentials
├── 03-pvcs.yaml                   # Persistent volume claims
├── 04-postgres.yaml               # PostgreSQL StatefulSet
├── 05-redis.yaml                  # Redis StatefulSet
├── 06-hypercode-core.yaml         # Core service + Celery worker
├── 07-observability.yaml          # Prometheus, Grafana, Node Exporter
├── 08-logging-tracing.yaml        # Tempo, Loki
├── 09-data-services.yaml          # MinIO, ChromaDB, Ollama
├── 10-dashboard.yaml              # Frontend dashboard
├── 11-ingress-network-policy.yaml # Ingress, network policies, HPA
└── 12-broski-bot.yaml             # Discord bot deployment
```

## Deployment Steps

### 1. Prepare Your Environment

Before deploying, update secrets with your actual credentials:

```bash
# Edit secrets file with your API keys
kubectl apply -f k8s/02-secrets.yaml --dry-run=client -o yaml | \
  sed 's/changeme123/YOUR_ACTUAL_PASSWORD/g' | \
  kubectl apply -f -
```

Or manually edit the file:
```bash
# Open the secrets file and add your credentials
nano k8s/02-secrets.yaml
```

**Critical secrets to update:**
- `POSTGRES_PASSWORD`: Strong database password
- `HYPERCODE_JWT_SECRET`: Secure JWT key
- `API_KEY`: Application API key
- `MINIO_ROOT_PASSWORD`: MinIO credentials
- `PERPLEXITY_API_KEY`, `OPENAI_API_KEY`: LLM API keys
- `DISCORD_TOKEN`, `DISCORD_GUILD_ID`: Bot credentials

### 2. Create Namespace and ConfigMaps

```bash
# Create namespace
kubectl apply -f k8s/00-namespace.yaml

# Apply configurations
kubectl apply -f k8s/01-configmaps.yaml
```

### 3. Create Secrets

```bash
# Apply secrets (AFTER updating credentials)
kubectl apply -f k8s/02-secrets.yaml
```

### 4. Create Storage

```bash
# Create persistent volume claims
kubectl apply -f k8s/03-pvcs.yaml

# Verify PVCs are created
kubectl get pvc -n hypercode
```

### 5. Deploy Databases and Cache

```bash
# Deploy PostgreSQL (StatefulSet)
kubectl apply -f k8s/04-postgres.yaml

# Deploy Redis (StatefulSet)
kubectl apply -f k8s/05-redis.yaml

# Wait for databases to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n hypercode --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n hypercode --timeout=300s
```

### 6. Deploy Core Services

```bash
# Deploy HyperCode Core and Celery Worker
kubectl apply -f k8s/06-hypercode-core.yaml

# Wait for services to be ready
kubectl wait --for=condition=ready pod -l app=hypercode-core -n hypercode --timeout=300s
```

### 7. Deploy Observability Stack

```bash
# Deploy Prometheus, Grafana, Node Exporter
kubectl apply -f k8s/07-observability.yaml

# Deploy Tempo (tracing) and Loki (logging)
kubectl apply -f k8s/08-logging-tracing.yaml
```

### 8. Deploy Data Services

```bash
# Deploy MinIO, ChromaDB, Ollama
kubectl apply -f k8s/09-data-services.yaml

# Wait for services to stabilize
kubectl wait --for=condition=ready pod -l app=chroma -n hypercode --timeout=300s
```

### 9. Deploy Dashboard

```bash
# Deploy frontend dashboard
kubectl apply -f k8s/10-dashboard.yaml

# Wait for dashboard to be ready
kubectl wait --for=condition=ready pod -l app=dashboard -n hypercode --timeout=300s
```

### 10. Configure Ingress and Network Policies

```bash
# First, update domain names in the ingress file
nano k8s/11-ingress-network-policy.yaml  # Change *.example.com to your domains

# Apply ingress and network policies
kubectl apply -f k8s/11-ingress-network-policy.yaml
```

### 11. Deploy Optional Services (Agents)

```bash
# Deploy Broski Bot (Discord integration)
kubectl apply -f k8s/12-broski-bot.yaml
```

## Complete Deployment Script

```bash
#!/bin/bash
set -e

echo "Deploying HyperCode to Kubernetes..."

# Create namespace and initial configs
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/01-configmaps.yaml
kubectl apply -f k8s/02-secrets.yaml
kubectl apply -f k8s/03-pvcs.yaml

# Deploy core infrastructure
kubectl apply -f k8s/04-postgres.yaml
kubectl apply -f k8s/05-redis.yaml
kubectl wait --for=condition=ready pod -l app=postgres -n hypercode --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n hypercode --timeout=300s

# Deploy application
kubectl apply -f k8s/06-hypercode-core.yaml
kubectl wait --for=condition=ready pod -l app=hypercode-core -n hypercode --timeout=300s

# Deploy observability
kubectl apply -f k8s/07-observability.yaml
kubectl apply -f k8s/08-logging-tracing.yaml

# Deploy data services
kubectl apply -f k8s/09-data-services.yaml
kubectl apply -f k8s/10-dashboard.yaml

# Configure networking
kubectl apply -f k8s/11-ingress-network-policy.yaml

echo "Deployment complete!"
```

## Accessing the Application

### Port Forwarding (for local development)

```bash
# Dashboard
kubectl port-forward -n hypercode svc/dashboard 3000:3000

# API
kubectl port-forward -n hypercode svc/hypercode-core 8000:8000

# Grafana
kubectl port-forward -n hypercode svc/grafana 3001:3000

# Prometheus
kubectl port-forward -n hypercode svc/prometheus 9090:9090

# MinIO Console
kubectl port-forward -n hypercode svc/minio 9001:9001
```

### Ingress Access (production)

After configuring DNS and ingress:
- Dashboard: `https://hypercode.example.com`
- API: `https://api.hypercode.example.com`
- Grafana: `https://grafana.hypercode.example.com`
- Prometheus: `https://prometheus.hypercode.example.com`
- MinIO: `https://minio.hypercode.example.com`

## Monitoring and Debugging

### Check Deployment Status

```bash
# View all resources in namespace
kubectl get all -n hypercode

# Check pod status
kubectl get pods -n hypercode -o wide

# Check services
kubectl get svc -n hypercode

# Check ingress
kubectl get ingress -n hypercode
```

### View Logs

```bash
# Core service logs
kubectl logs -n hypercode deployment/hypercode-core -f

# Celery worker logs
kubectl logs -n hypercode deployment/celery-worker -f

# Dashboard logs
kubectl logs -n hypercode deployment/dashboard -f

# Previous pod logs (if restarted)
kubectl logs -n hypercode deployment/hypercode-core --previous
```

### Describe Resources

```bash
# Get detailed pod information
kubectl describe pod -n hypercode <pod-name>

# Get service details
kubectl describe svc -n hypercode hypercode-core

# Get ingress details
kubectl describe ingress -n hypercode hypercode-ingress
```

### Execute Commands in Pods

```bash
# Connect to database
kubectl exec -it -n hypercode postgres-0 -- psql -U postgres -d hypercode

# Check Redis
kubectl exec -it -n hypercode redis-0 -- redis-cli ping

# Shell into pod
kubectl exec -it -n hypercode <pod-name> -- /bin/bash
```

## Scaling

### Manual Scaling

```bash
# Scale HyperCode Core
kubectl scale deployment hypercode-core --replicas=5 -n hypercode

# Scale Celery Workers
kubectl scale deployment celery-worker --replicas=3 -n hypercode
```

### Automatic Scaling (HPA)

The manifests include HorizontalPodAutoscaler for HyperCode Core and Dashboard:

```bash
# View HPA status
kubectl get hpa -n hypercode

# Describe HPA
kubectl describe hpa hypercode-core-hpa -n hypercode

# Monitor scaling events
kubectl get events -n hypercode --sort-by='.lastTimestamp'
```

## Updating Deployments

### Update Image

```bash
# Set new image
kubectl set image deployment/hypercode-core \
  hypercode-core=myregistry/hypercode:v2.0 \
  -n hypercode

# Check rollout status
kubectl rollout status deployment/hypercode-core -n hypercode

# Rollback if needed
kubectl rollout undo deployment/hypercode-core -n hypercode
```

### Update ConfigMap

```bash
# Edit ConfigMap
kubectl edit configmap hypercode-config -n hypercode

# Restart deployment to apply changes
kubectl rollout restart deployment/hypercode-core -n hypercode
```

## Storage Management

### Check Storage Usage

```bash
# Show PVC sizes and status
kubectl get pvc -n hypercode

# Check actual disk usage
kubectl exec -n hypercode postgres-0 -- du -sh /var/lib/postgresql/data
```

### Backup Database

```bash
# Create backup
kubectl exec -n hypercode postgres-0 -- \
  pg_dump -U postgres hypercode > hypercode_backup.sql

# Restore backup
kubectl exec -i -n hypercode postgres-0 -- \
  psql -U postgres hypercode < hypercode_backup.sql
```

## Production Considerations

### High Availability

1. **Database Replication**: Use PostgreSQL replication for HA
2. **Redis Sentinel**: Set up Redis Sentinel for failover
3. **Multiple Replicas**: Scale services to multiple replicas
4. **Pod Disruption Budgets**: Already configured in manifests
5. **Affinity Rules**: Add pod anti-affinity for distributed scheduling

### Security

1. **RBAC**: Implement Role-Based Access Control
2. **Network Policies**: Already included in manifests
3. **Pod Security Policy**: Enforce security standards
4. **Secrets Management**: Use external secret management (Vault, Sealed Secrets)
5. **Image Scanning**: Scan images for vulnerabilities

### Resource Management

1. **Resource Quotas**: Already set in manifests
2. **Limit Ranges**: Define per-container limits
3. **Node Affinity**: Pin workloads to specific nodes
4. **QoS Classes**: Ensure appropriate quality of service

### Backup and Disaster Recovery

1. **Velero**: Use for cluster-wide backups
2. **Database Backups**: Regular automated backups
3. **Volume Snapshots**: Kubernetes native snapshots
4. **Cross-region Replication**: For disaster recovery

## Cleanup

### Delete Deployment

```bash
# Delete all resources
kubectl delete namespace hypercode

# Or selectively delete resources
kubectl delete -f k8s/12-broski-bot.yaml
kubectl delete -f k8s/11-ingress-network-policy.yaml
# ... etc
```

## Troubleshooting

### Pods not starting

```bash
# Check pod events
kubectl describe pod <pod-name> -n hypercode

# Check for resource constraints
kubectl top nodes
kubectl top pods -n hypercode
```

### Image pull errors

```bash
# Check image availability
docker pull <image-name>

# Create image pull secret if using private registry
kubectl create secret docker-registry regcred \
  --docker-server=<registry> \
  --docker-username=<username> \
  --docker-password=<password> \
  -n hypercode
```

### Database connection errors

```bash
# Test connectivity
kubectl exec -n hypercode <pod-name> -- \
  psql -h postgres -U postgres -d hypercode -c "SELECT 1"

# Check network policies
kubectl get networkpolicy -n hypercode
```

## Support Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
- [Docker Hub Images](https://hub.docker.com/)
