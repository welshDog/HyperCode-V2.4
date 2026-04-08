# HyperCode Kubernetes Deployment Guide

This guide walks you through deploying the HyperCode platform to a Kubernetes cluster.

## Prerequisites

- Kubernetes cluster (v1.24+)
- kubectl configured to access your cluster
- Container registry access (Docker Hub, GCR, ECR, etc.)
- Ingress controller installed (nginx-ingress recommended)
- cert-manager installed (optional, for TLS)
- Storage class configured for persistent volumes

## Quick Start

```bash
# 1. Create namespace
kubectl apply -f k8s/00-namespace.yaml

# 2. Configure secrets (IMPORTANT: Update with real values first!)
kubectl apply -f k8s/01-secrets.yaml

# 3. Apply configurations
kubectl apply -f k8s/02-configmap.yaml

# 4. Create persistent volumes
kubectl apply -f k8s/03-persistent-volumes.yaml

# 5. Deploy infrastructure (Redis, Postgres)
kubectl apply -f k8s/04-redis.yaml
kubectl apply -f k8s/05-postgres.yaml

# 6. Wait for infrastructure to be ready
kubectl wait --for=condition=ready pod -l app=redis -n hypercode --timeout=180s
kubectl wait --for=condition=ready pod -l app=postgres -n hypercode --timeout=180s

# 7. Deploy core services
kubectl apply -f k8s/06-hypercode-core.yaml
kubectl apply -f k8s/07-crew-orchestrator.yaml

# 8. Deploy agents
kubectl apply -f k8s/08-agents.yaml

# 9. Deploy dashboard
kubectl apply -f k8s/09-dashboard.yaml

# 10. Deploy Ollama (optional, requires GPU nodes)
kubectl apply -f k8s/10-ollama.yaml

# 11. Deploy monitoring stack
kubectl apply -f k8s/11-monitoring.yaml

# 12. Apply network policies (optional but recommended)
kubectl apply -f k8s/13-network-policy.yaml

# 13. Configure ingress (update hosts in 12-ingress.yaml first!)
kubectl apply -f k8s/12-ingress.yaml

# 14. Enable autoscaling (optional)
kubectl apply -f k8s/14-hpa.yaml
```

## Pre-Deployment Steps

### 1. Build and Push Container Images

Before deploying, build and push all container images to your registry:

```bash
# Set your registry
export REGISTRY="your-registry.com/hypercode"

# Build and push HyperCode Core
docker build -t $REGISTRY/hypercode-core:latest ./HyperCode-V2.0/THE\ HYPERCODE/hypercode-core
docker push $REGISTRY/hypercode-core:latest

# Build and push Crew Orchestrator
docker build -t $REGISTRY/crew-orchestrator:latest ./agents/crew-orchestrator
docker push $REGISTRY/crew-orchestrator:latest

# Build and push all agents
for agent in 01-frontend-specialist 02-backend-specialist 03-database-architect 04-qa-engineer 05-devops-engineer 06-security-engineer 07-system-architect 08-project-strategist; do
  docker build -t $REGISTRY/${agent}:latest ./agents/${agent}
  docker push $REGISTRY/${agent}:latest
done
```

Update image names in the manifests to match your registry.

### 2. Configure Secrets

**CRITICAL:** Update `k8s/01-secrets.yaml` with real values:

```bash
# Generate secure secrets
PERPLEXITY_KEY="your-PERPLEXITY-api-key"
JWT_SECRET=$(openssl rand -base64 32)
POSTGRES_PASS=$(openssl rand -base64 24)
REDIS_PASS=$(openssl rand -base64 24)
GRAFANA_PASS=$(openssl rand -base64 16)

# Update the secrets file or create directly
kubectl create secret generic hypercode-secrets \
  --from-literal=PERPLEXITY-api-key="$PERPLEXITY_KEY" \
  --from-literal=hypercode-jwt-secret="$JWT_SECRET" \
  --from-literal=postgres-password="$POSTGRES_PASS" \
  --from-literal=redis-password="$REDIS_PASS" \
  --from-literal=grafana-admin-password="$GRAFANA_PASS" \
  -n hypercode
```

### 3. Configure Storage

Update storage class in `k8s/03-persistent-volumes.yaml` based on your cluster:

- **GKE**: `standard` or `standard-rwo`
- **EKS**: `gp3` or `gp2`
- **AKS**: `default` or `managed-premium`
- **On-premises**: Your configured storage class

### 4. Configure Ingress

Update `k8s/12-ingress.yaml` with your actual domain names:

```yaml
- host: hypercode.yourdomain.com  # Change this
- host: dashboard.hypercode.yourdomain.com  # Change this
- host: grafana.hypercode.yourdomain.com  # Change this
```

## Verification

### Check Pod Status

```bash
# View all pods
kubectl get pods -n hypercode

# Watch deployment progress
kubectl get pods -n hypercode -w

# Check specific deployment
kubectl get deployment hypercode-core -n hypercode
```

### Check Services

```bash
kubectl get svc -n hypercode
```

### View Logs

```bash
# HyperCode Core logs
kubectl logs -f deployment/hypercode-core -n hypercode

# Crew Orchestrator logs
kubectl logs -f deployment/crew-orchestrator -n hypercode

# Agent logs
kubectl logs -f deployment/frontend-specialist -n hypercode
```

### Test Connectivity

```bash
# Port forward to test locally
kubectl port-forward svc/hypercode-core 8000:8000 -n hypercode
kubectl port-forward svc/dashboard 8088:80 -n hypercode
kubectl port-forward svc/grafana 3001:3000 -n hypercode

# Test endpoints
curl http://localhost:8000/health
curl http://localhost:8088/
```

## Monitoring

### Access Grafana

```bash
# Port forward Grafana
kubectl port-forward svc/grafana 3001:3000 -n hypercode

# Get admin password
kubectl get secret hypercode-secrets -n hypercode -o jsonpath='{.data.grafana-admin-password}' | base64 -d

# Open http://localhost:3001
```

### Access Prometheus

```bash
kubectl port-forward svc/prometheus 9090:9090 -n hypercode
# Open http://localhost:9090
```

### Access Jaeger

```bash
kubectl port-forward svc/jaeger 16686:16686 -n hypercode
# Open http://localhost:16686
```

## Scaling

### Manual Scaling

```bash
# Scale HyperCode Core
kubectl scale deployment hypercode-core --replicas=5 -n hypercode

# Scale specific agent
kubectl scale deployment frontend-specialist --replicas=2 -n hypercode
```

### Autoscaling

HPA manifests are provided in `k8s/14-hpa.yaml`. They automatically scale based on CPU/memory usage.

```bash
# View HPA status
kubectl get hpa -n hypercode

# Describe HPA
kubectl describe hpa hypercode-core-hpa -n hypercode
```

## Backup and Restore

### Backup Postgres

```bash
# Create backup
kubectl exec -it postgres-0 -n hypercode -- pg_dump -U postgres hypercode > backup.sql

# Restore backup
kubectl exec -i postgres-0 -n hypercode -- psql -U postgres hypercode < backup.sql
```

### Backup Redis

```bash
# Trigger save
kubectl exec -it redis-0 -n hypercode -- redis-cli SAVE

# Copy dump file
kubectl cp hypercode/redis-0:/data/dump.rdb ./redis-backup.rdb
```

## Troubleshooting

### Pods Not Starting

```bash
# Check pod events
kubectl describe pod <pod-name> -n hypercode

# Check logs
kubectl logs <pod-name> -n hypercode

# Check previous container logs (if crashed)
kubectl logs <pod-name> -n hypercode --previous
```

### Network Issues

```bash
# Check network policies
kubectl get networkpolicies -n hypercode

# Test connectivity between pods
kubectl run -it --rm debug --image=nicolaka/netshoot -n hypercode -- /bin/bash
# Inside the pod:
curl http://hypercode-core:8000/health
```

### Database Connection Issues

```bash
# Check Postgres status
kubectl exec -it postgres-0 -n hypercode -- psql -U postgres -c "SELECT version();"

# Check Redis
kubectl exec -it redis-0 -n hypercode -- redis-cli ping
```

### Resource Constraints

```bash
# Check resource usage
kubectl top pods -n hypercode
kubectl top nodes

# Check pod resource requests/limits
kubectl describe pod <pod-name> -n hypercode | grep -A5 "Limits:\|Requests:"
```

## Security Considerations

1. **Secrets Management**: Use external secret management (Vault, AWS Secrets Manager, etc.)
2. **Network Policies**: Enable network policies to restrict pod-to-pod communication
3. **RBAC**: Configure appropriate RBAC roles and service accounts
4. **Pod Security**: Enable pod security standards/admission
5. **TLS**: Enable TLS for all external endpoints using cert-manager
6. **Image Scanning**: Scan all images for vulnerabilities before deployment
7. **Resource Limits**: Always set resource requests and limits

## Production Checklist

- [ ] Secrets properly configured (not using placeholder values)
- [ ] Images built and pushed to registry
- [ ] Storage class configured correctly
- [ ] Ingress controller installed
- [ ] TLS certificates configured
- [ ] Network policies enabled
- [ ] Resource requests/limits tuned
- [ ] Monitoring stack deployed
- [ ] Backup strategy implemented
- [ ] Disaster recovery plan documented
- [ ] Security scanning enabled
- [ ] Logging configured (ELK, Loki, etc.)
- [ ] Alerting configured
- [ ] Load testing completed

## Maintenance

### Update Deployments

```bash
# Update image
kubectl set image deployment/hypercode-core hypercode-core=$REGISTRY/hypercode-core:v2.0 -n hypercode

# Rollout status
kubectl rollout status deployment/hypercode-core -n hypercode

# Rollback if needed
kubectl rollout undo deployment/hypercode-core -n hypercode
```

### Database Migrations

```bash
# Run migrations
kubectl exec -it deployment/hypercode-core -n hypercode -- python -m prisma migrate deploy
```

## Cleanup

```bash
# Delete all resources
kubectl delete namespace hypercode

# Or delete individual components
kubectl delete -f k8s/
```

## Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
- [Production Best Practices](https://kubernetes.io/docs/setup/best-practices/)

## Support

For issues or questions:
- Check logs: `kubectl logs <pod-name> -n hypercode`
- Check events: `kubectl get events -n hypercode --sort-by='.lastTimestamp'`
- Review pod status: `kubectl describe pod <pod-name> -n hypercode`
