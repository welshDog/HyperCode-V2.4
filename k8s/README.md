# HyperCode Kubernetes Deployment - Complete Guide

## 📋 Overview

This directory contains complete Kubernetes manifests and automation scripts for deploying the HyperCode application stack to any Kubernetes cluster (1.20+). The deployment includes:

- **Core Application**: HyperCode Core, Celery Workers, Dashboard
- **Databases**: PostgreSQL, Redis
- **Observability**: Prometheus, Grafana, Loki, Tempo
- **Data Services**: MinIO, ChromaDB, Ollama
- **Optional Services**: Broski Bot (Discord integration)
- **Infrastructure**: Ingress, Network Policies, HPA, PDB

## 📁 Directory Structure

```
k8s/
├── 00-namespace.yaml                    # Kubernetes namespace
├── 01-configmaps.yaml                   # Configuration management
├── 02-secrets.yaml                      # Sensitive credentials (⚠️ UPDATE BEFORE DEPLOYING)
├── 03-pvcs.yaml                         # Persistent volume claims
├── 04-postgres.yaml                     # PostgreSQL StatefulSet
├── 05-redis.yaml                        # Redis cache StatefulSet
├── 06-hypercode-core.yaml               # Core app & Celery workers
├── 07-observability.yaml                # Prometheus, Grafana, Node Exporter
├── 08-logging-tracing.yaml              # Loki (logs), Tempo (traces)
├── 09-data-services.yaml                # MinIO, ChromaDB, Ollama
├── 10-dashboard.yaml                    # Frontend dashboard
├── 11-ingress-network-policy.yaml       # Ingress, networking, HPA, PDB
├── 12-broski-bot.yaml                   # Discord bot (optional)
├── 13-monitoring-alerts.yaml            # Prometheus rules & alerts
├── 14-grafana-dashboards-alertmanager.yaml  # Grafana datasources & dashboards
│
├── Automated Scripts:
├── deploy.sh                            # 🚀 Main deployment automation
├── health_check.sh                      # Health check script
├── post_deployment_check.sh             # Post-deployment verification
├── comprehensive_health_check.sh        # Complete health assessment
│
└── Documentation:
    ├── DEPLOYMENT_GUIDE.md              # Step-by-step deployment
    ├── TROUBLESHOOTING.md               # Common issues & solutions
    ├── PRODUCTION_READINESS_CHECKLIST.md # Pre-production verification
    ├── QUICK_REFERENCE.md               # Operator quick reference
    └── README.md                        # This file
```

## 🚀 Quick Start (5 Minutes)

### 1. Prerequisites Check
```bash
# Verify kubectl is installed and connected
kubectl cluster-info

# Verify cluster version (1.20+)
kubectl version --short

# Check available storage
kubectl get storageclass
```

### 2. Update Secrets (CRITICAL!)
```bash
# Edit secrets with your values
nano ./k8s/02-secrets.yaml

# Update at minimum:
# - POSTGRES_PASSWORD: Strong database password
# - HYPERCODE_JWT_SECRET: Secure JWT key
# - API_KEY: Application API key
# - PERPLEXITY_API_KEY: LLM API key
# - MINIO_ROOT_PASSWORD: MinIO credentials
```

### 3. Deploy Everything
```bash
# Make deploy script executable
chmod +x ./k8s/deploy.sh

# Run automated deployment
./k8s/deploy.sh

# Monitor deployment progress
kubectl get pods -n hypercode --watch
```

### 4. Verify Deployment
```bash
# Run comprehensive health check
chmod +x ./k8s/comprehensive_health_check.sh
./k8s/comprehensive_health_check.sh

# Access services
kubectl port-forward -n hypercode svc/dashboard 3000:3000
# Visit http://localhost:3000
```

## 📊 Health Check Commands

```bash
# Full health check with recommendations
./k8s/comprehensive_health_check.sh

# Traditional health check
./k8s/health_check.sh

# Post-deployment verification
./k8s/post_deployment_check.sh

# View generated reports
cat ./health_check_*.txt
cat ./performance_report.txt
```

## 📈 Recommended Deployment Flow

### Phase 1: Pre-Deployment (30 minutes)
```bash
./k8s/health_check.sh                          # Initial assessment
# Review recommendations and update secrets
nano ./k8s/02-secrets.yaml                     # Update all credentials
```

### Phase 2: Deployment (15 minutes)
```bash
./k8s/deploy.sh                                # Automated deployment
# Or manual:
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/01-configmaps.yaml
kubectl apply -f k8s/02-secrets.yaml
# ... continue with remaining manifests
```

### Phase 3: Verification (20 minutes)
```bash
./k8s/post_deployment_check.sh                 # Performance analysis
./k8s/comprehensive_health_check.sh            # Complete assessment

# View detailed recommendations
cat ./HEALTH_CHECK_REPORT_*.html               # Open in browser
cat ./issues_and_recommendations.txt
```

## 🎯 Key Features

### ✅ Production-Ready
- Multi-replica deployments for HA
- Pod Disruption Budgets for maintenance windows
- Horizontal Pod Autoscaling configured
- Network policies for security
- Resource quotas enforced

### ✅ Fully Observable
- Prometheus metrics collection
- Grafana dashboards
- Alerting rules
- Centralized logging with Loki
- Distributed tracing with Tempo

### ✅ Data Protection
- PersistentVolumes for all stateful services
- Database replication support
- Backup-friendly design
- Multi-tier data storage

### ✅ Secure by Default
- Network policies isolating pods
- Resource limits preventing resource exhaustion
- RBAC-ready
- Secrets encrypted (with etcd encryption enabled)

## 🔧 Configuration

### Secrets Management
All sensitive credentials are in `02-secrets.yaml`:
```yaml
POSTGRES_PASSWORD: "changeme123"              # ⚠️ CHANGE THIS
HYPERCODE_JWT_SECRET: "jwt-secret-key"        # ⚠️ CHANGE THIS
API_KEY: "dev-master-key"                     # ⚠️ CHANGE THIS
MINIO_ROOT_PASSWORD: "minioadmin123"          # ⚠️ CHANGE THIS
```

**Before production deployment:**
```bash
# Update each secret
kubectl patch secret hypercode-secrets -n hypercode \
  -p '{"data":{"POSTGRES_PASSWORD":"'$(echo -n 'STRONG_PASSWORD' | base64)'"}}'
```

### ConfigMap Customization
Edit `01-configmaps.yaml` for:
- Prometheus scrape intervals
- Loki retention period
- Tempo sampling rate
- Application environment variables

### Resource Allocation
Adjust in respective manifests:
- HyperCode Core: 500m CPU / 1Gi RAM (default)
- Celery Worker: 250m CPU / 512Mi RAM (default)
- Database: 250m CPU / 512Mi RAM (default)
- Cache: 100m CPU / 256Mi RAM (default)

## 📊 Monitoring & Observability

### Access Monitoring Dashboards
```bash
# Grafana (admin/password)
kubectl port-forward -n hypercode svc/grafana 3001:3000
# http://localhost:3001

# Prometheus
kubectl port-forward -n hypercode svc/prometheus 9090:9090
# http://localhost:9090

# MinIO Console
kubectl port-forward -n hypercode svc/minio 9001:9001
# http://localhost:9001 (minioadmin/minioadmin)
```

### Key Metrics to Monitor
- Pod CPU/Memory usage
- Database connection pool
- Redis memory utilization
- API response times
- Error rates
- Queue lengths (Celery)

## 🔍 Health Check Output

The `comprehensive_health_check.sh` generates:

1. **Terminal Output**: Color-coded status with immediate issues
2. **HTML Report**: `HEALTH_CHECK_REPORT_*.html` - Full visualization
3. **JSON Report**: `health_check_*.json` - Machine-readable format
4. **Text Report**: `issues_and_recommendations.txt` - Actionable items

### Health Score Interpretation
- **90-100**: Excellent - Production ready
- **70-89**: Good - Minor issues only
- **50-69**: Warning - Several issues need attention
- **< 50**: Critical - Must fix before production

## ⚠️ Critical Pre-Production Checklist

- [ ] All default secrets updated to strong values
- [ ] Storage class set as default
- [ ] Ingress controller installed
- [ ] Domain names configured (update ingress)
- [ ] SSL certificates ready or Let's Encrypt configured
- [ ] Backup strategy implemented and tested
- [ ] Monitoring alerts configured
- [ ] RBAC policies reviewed
- [ ] Network policies tested
- [ ] Disaster recovery plan documented

## 🆘 Troubleshooting

### Common Issues & Quick Fixes

**Pods stuck in Pending:**
```bash
kubectl describe pod <pod-name> -n hypercode
# Check for insufficient resources, PVC issues, or image pull failures
```

**Database not starting:**
```bash
kubectl logs -n hypercode postgres-0 --tail=50
# Check PVC binding and disk space
```

**Service connection issues:**
```bash
kubectl get endpoints -n hypercode
kubectl exec -n hypercode <pod> -- nc -zv <service> <port>
```

**See TROUBLESHOOTING.md for comprehensive guide**

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| `DEPLOYMENT_GUIDE.md` | Detailed step-by-step deployment instructions |
| `TROUBLESHOOTING.md` | Common issues and solutions |
| `PRODUCTION_READINESS_CHECKLIST.md` | Pre-production verification |
| `QUICK_REFERENCE.md` | Operator quick commands |

## 🔐 Security Considerations

### Network Security
- Network policies restrict pod-to-pod communication
- Ingress with TLS/HTTPS recommended
- API exposed via ingress only

### Data Security
- Secrets stored in Kubernetes secrets (encrypted with etcd encryption)
- PVCs backed by storage class
- Regular backups to external storage recommended

### Access Control
- RBAC recommended for multi-team environments
- Service accounts for pod authentication
- Pod Security Policies recommended

## 📦 Scaling & Performance

### Horizontal Scaling
```bash
# Scale core application
kubectl scale deployment hypercode-core --replicas=5 -n hypercode

# Scale Celery workers
kubectl scale deployment celery-worker --replicas=3 -n hypercode

# Auto-scaling (HPA) already configured
kubectl get hpa -n hypercode
```

### Performance Tuning
- Adjust resource requests/limits in manifests
- Configure HPA thresholds in `11-ingress-network-policy.yaml`
- Optimize database queries
- Monitor and adjust cache hit ratios

## 🆘 Getting Help

### View Logs
```bash
# Application logs
kubectl logs -n hypercode -l app=hypercode-core -f

# Database logs
kubectl logs -n hypercode postgres-0 --tail=50

# All recent events
kubectl get events -n hypercode --sort-by='.lastTimestamp' | tail -20
```

### Run Diagnostics
```bash
# Full health check
./k8s/comprehensive_health_check.sh

# View generated reports
cat ./health_check_report.txt
cat ./performance_report.txt
```

### Contact Support
- Troubleshooting Guide: `./k8s/TROUBLESHOOTING.md`
- Kubernetes Docs: https://kubernetes.io/docs/
- Prometheus Docs: https://prometheus.io/docs/

## 📞 Emergency Procedures

### Restart All Services
```bash
kubectl rollout restart deployment -n hypercode
```

### Scale Down Everything
```bash
kubectl scale deployment --all --replicas=0 -n hypercode
```

### Force Delete Stuck Pod
```bash
kubectl delete pod <pod> -n hypercode --grace-period=0 --force
```

### Full Reset (⚠️ DATA LOSS)
```bash
kubectl delete namespace hypercode
kubectl apply -f k8s/00-namespace.yaml
# Then apply all manifests
```

## 📊 Deployment Statistics

When fully deployed, you'll have:
- **6** Deployments
- **2** StatefulSets
- **10+** Services
- **9** PersistentVolumeClaims
- **15+** Pods (running)
- **Multiple** ConfigMaps and Secrets
- **Network Policies** for security
- **HPA** for auto-scaling
- **PDB** for availability

## 🎓 Learning Resources

### Kubernetes Fundamentals
- [Kubernetes Official Documentation](https://kubernetes.io/docs/)
- [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
- [Interactive Kubernetes Tutorial](https://kubernetes.io/docs/tutorials/kubernetes-basics/)

### Observability
- [Prometheus Querying Basics](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Grafana Dashboard Guide](https://grafana.com/docs/grafana/latest/dashboards/)
- [Loki Log Aggregation](https://grafana.com/docs/loki/latest/)

### Production Operations
- [Kubernetes Production Best Practices](https://kubernetes.io/docs/setup/production-environment/)
- [Kube Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)

## 🤝 Contributing

To improve these deployments:
1. Test changes in dev environment
2. Update manifests following Kubernetes best practices
3. Update documentation
4. Validate with health check scripts
5. Test disaster recovery

## 📝 Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024 | Initial release - complete K8s deployment |

## 📄 License

These manifests and scripts are provided as-is for HyperCode deployment.

---

## 🎯 Next Steps

1. **Read** `DEPLOYMENT_GUIDE.md` for detailed instructions
2. **Update** `02-secrets.yaml` with your values
3. **Run** `./k8s/deploy.sh` to deploy
4. **Check** `./k8s/comprehensive_health_check.sh` for status
5. **Review** `PRODUCTION_READINESS_CHECKLIST.md` before going live
6. **Monitor** using Grafana dashboards

---

**Generated**: $(date)
**Kubernetes Version**: 1.20+
**For Support**: Refer to TROUBLESHOOTING.md or contact ops-team@example.com

**Happy Deploying! 🚀**
