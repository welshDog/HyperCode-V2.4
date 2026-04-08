#!/bin/bash

# HyperCode Kubernetes Automated Deployment Script
# Full deployment with validation and rollback capability

set -e

# Configuration
NAMESPACE="hypercode"
MANIFEST_DIR="./k8s"
TIMEOUT=300
BACKUP_DIR="./backups/k8s-$(date +%Y%m%d-%H%M%S)"
LOG_FILE="./deployment-$(date +%Y%m%d-%H%M%S).log"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Logging functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_pass() {
    echo -e "${GREEN}✓ $1${NC}" | tee -a "$LOG_FILE"
}

log_fail() {
    echo -e "${RED}✗ $1${NC}" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}⚠ $1${NC}" | tee -a "$LOG_FILE"
}

log_section() {
    echo -e "\n${MAGENTA}═══════════════════════════════════════${NC}" | tee -a "$LOG_FILE"
    echo -e "${MAGENTA}$1${NC}" | tee -a "$LOG_FILE"
    echo -e "${MAGENTA}═══════════════════════════════════════${NC}" | tee -a "$LOG_FILE"
}

# Pre-deployment checks
pre_deployment_checks() {
    log_section "PRE-DEPLOYMENT VALIDATION"
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_fail "kubectl not found. Please install kubectl."
        exit 1
    fi
    log_pass "kubectl found: $(kubectl version --client --short)"
    
    # Check cluster connectivity
    if ! kubectl cluster-info &>/dev/null; then
        log_fail "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    log_pass "Connected to Kubernetes cluster"
    
    # Check cluster version
    KUBE_VERSION=$(kubectl version --short | grep Server | awk '{print $3}')
    log_pass "Kubernetes version: $KUBE_VERSION"
    
    # Check manifests exist
    if [ ! -d "$MANIFEST_DIR" ]; then
        log_fail "Manifest directory not found: $MANIFEST_DIR"
        exit 1
    fi
    log_pass "Manifest directory found"
    
    # List manifests
    log "Found manifests:"
    ls -1 "$MANIFEST_DIR"/*.yaml 2>/dev/null | sed 's/^/  /'
    
    # Check namespace
    if kubectl get namespace "$NAMESPACE" &>/dev/null; then
        log_warn "Namespace '$NAMESPACE' already exists"
    else
        log "Namespace '$NAMESPACE' will be created"
    fi
}

# Create backup
create_backup() {
    log_section "CREATING BACKUP"
    
    mkdir -p "$BACKUP_DIR"
    
    # Backup current manifests if namespace exists
    if kubectl get namespace "$NAMESPACE" &>/dev/null; then
        log "Backing up current resources..."
        mkdir -p "$BACKUP_DIR/current"
        kubectl get all -n "$NAMESPACE" -o yaml > "$BACKUP_DIR/current/all-resources.yaml"
        kubectl get configmap -n "$NAMESPACE" -o yaml > "$BACKUP_DIR/current/configmaps.yaml"
        kubectl get secret -n "$NAMESPACE" -o yaml > "$BACKUP_DIR/current/secrets.yaml"
        kubectl get pvc -n "$NAMESPACE" -o yaml > "$BACKUP_DIR/current/pvcs.yaml"
        log_pass "Backup created: $BACKUP_DIR/current/"
    else
        log "Namespace does not exist, skipping backup"
    fi
}

# Deploy phase
deploy_phase() {
    local phase=$1
    local manifest_pattern=$2
    local description=$3
    
    log_section "DEPLOYING: $description"
    
    local manifests=$(find "$MANIFEST_DIR" -name "$manifest_pattern" -type f | sort)
    
    if [ -z "$manifests" ]; then
        log_warn "No manifests matching pattern: $manifest_pattern"
        return 0
    fi
    
    for manifest in $manifests; do
        local filename=$(basename "$manifest")
        log "Applying: $filename"
        
        if kubectl apply -f "$manifest" --record 2>&1 | tee -a "$LOG_FILE"; then
            log_pass "Applied: $filename"
        else
            log_fail "Failed to apply: $filename"
            return 1
        fi
    done
}

# Wait for deployment
wait_for_deployment() {
    local deployment=$1
    local replicas=${2:-1}
    
    log "Waiting for $deployment to be ready (replicas: $replicas)..."
    
    if kubectl wait --for=condition=available --timeout="${TIMEOUT}s" \
        deployment "$deployment" -n "$NAMESPACE" 2>/dev/null; then
        log_pass "$deployment is ready"
        return 0
    else
        log_fail "$deployment failed to become ready within ${TIMEOUT}s"
        return 1
    fi
}

# Health checks after deployment
post_deployment_checks() {
    log_section "POST-DEPLOYMENT HEALTH CHECKS"
    
    # Check all pods are running
    log "Checking pod status..."
    local pending_pods=$(kubectl get pods -n "$NAMESPACE" -o jsonpath='{.items[?(@.status.phase!="Running")].metadata.name}' 2>/dev/null)
    
    if [ -z "$pending_pods" ]; then
        log_pass "All pods are running"
    else
        log_fail "Pods not running: $pending_pods"
        return 1
    fi
    
    # Check services have endpoints
    log "Checking service endpoints..."
    local services=$(kubectl get svc -n "$NAMESPACE" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null)
    
    for svc in $services; do
        local endpoints=$(kubectl get endpoints "$svc" -n "$NAMESPACE" -o jsonpath='{.subsets[*].addresses[*].ip}' 2>/dev/null | wc -w)
        if [ "$endpoints" -eq 0 ]; then
            log_warn "Service '$svc' has no endpoints"
        else
            log_pass "Service '$svc' has endpoints"
        fi
    done
    
    # Check PVCs are bound
    log "Checking PVC status..."
    local unbound=$(kubectl get pvc -n "$NAMESPACE" -o jsonpath='{.items[?(@.status.phase!="Bound")].metadata.name}' 2>/dev/null)
    
    if [ -z "$unbound" ]; then
        log_pass "All PVCs are Bound"
    else
        log_warn "Unbound PVCs: $unbound"
    fi
    
    # Check resource quotas
    log "Checking resource usage..."
    kubectl describe resourcequota -n "$NAMESPACE" 2>/dev/null | tee -a "$LOG_FILE"
}

# Generate deployment summary
generate_summary() {
    log_section "DEPLOYMENT SUMMARY"
    
    cat > "$BACKUP_DIR/deployment-summary.txt" << EOF
Deployment Date: $(date)
Namespace: $NAMESPACE
Manifest Directory: $MANIFEST_DIR
Log File: $LOG_FILE

RESOURCES DEPLOYED:
═══════════════════════════════════════

Namespace:
EOF
    kubectl get namespace "$NAMESPACE" -o wide >> "$BACKUP_DIR/deployment-summary.txt"
    
    cat >> "$BACKUP_DIR/deployment-summary.txt" << EOF

Deployments:
EOF
    kubectl get deployment -n "$NAMESPACE" -o wide >> "$BACKUP_DIR/deployment-summary.txt"
    
    cat >> "$BACKUP_DIR/deployment-summary.txt" << EOF

StatefulSets:
EOF
    kubectl get statefulset -n "$NAMESPACE" -o wide >> "$BACKUP_DIR/deployment-summary.txt"
    
    cat >> "$BACKUP_DIR/deployment-summary.txt" << EOF

Services:
EOF
    kubectl get svc -n "$NAMESPACE" -o wide >> "$BACKUP_DIR/deployment-summary.txt"
    
    cat >> "$BACKUP_DIR/deployment-summary.txt" << EOF

Pods:
EOF
    kubectl get pods -n "$NAMESPACE" -o wide >> "$BACKUP_DIR/deployment-summary.txt"
    
    cat >> "$BACKUP_DIR/deployment-summary.txt" << EOF

PersistentVolumeClaims:
EOF
    kubectl get pvc -n "$NAMESPACE" -o wide >> "$BACKUP_DIR/deployment-summary.txt"
    
    cat "$BACKUP_DIR/deployment-summary.txt" | tee -a "$LOG_FILE"
}

# Rollback function
rollback() {
    log_section "ROLLBACK IN PROGRESS"
    
    if [ ! -f "$BACKUP_DIR/current/all-resources.yaml" ]; then
        log_fail "No backup found for rollback"
        return 1
    fi
    
    log "Restoring from backup..."
    kubectl delete namespace "$NAMESPACE" --ignore-not-found=true
    kubectl apply -f "$BACKUP_DIR/current/all-resources.yaml"
    
    log_pass "Rollback completed"
}

# Main deployment flow
main() {
    log_section "HYPERCODE KUBERNETES DEPLOYMENT"
    log "Starting deployment at $(date)"
    
    # Pre-deployment
    pre_deployment_checks || { log_fail "Pre-deployment checks failed"; exit 1; }
    
    # Backup
    create_backup
    
    # Deploy namespace and core configs
    deploy_phase 1 "00-namespace.yaml" "Namespace" || { log_fail "Namespace deployment failed"; rollback; exit 1; }
    deploy_phase 2 "01-configmaps.yaml" "ConfigMaps" || { log_fail "ConfigMap deployment failed"; rollback; exit 1; }
    deploy_phase 3 "02-secrets.yaml" "Secrets" || { log_fail "Secrets deployment failed"; rollback; exit 1; }
    deploy_phase 4 "03-pvcs.yaml" "PersistentVolumeClaims" || { log_fail "PVC deployment failed"; rollback; exit 1; }
    
    sleep 5  # Wait for PVCs to initialize
    
    # Deploy stateful services
    deploy_phase 5 "04-postgres.yaml" "PostgreSQL Database" || { log_fail "PostgreSQL deployment failed"; rollback; exit 1; }
    wait_for_deployment "postgres" 1 || { log_fail "PostgreSQL failed to start"; rollback; exit 1; }
    
    # Deploy backup cronjob
    deploy_phase 5b "05-backup-cronjob.yaml" "PostgreSQL Backup Job" || log_warn "Backup cronjob deployment failed"

    sleep 10  # Let PostgreSQL stabilize
    
    deploy_phase 6 "05-redis.yaml" "Redis Cache" || { log_fail "Redis deployment failed"; rollback; exit 1; }
    wait_for_deployment "redis" 1 || { log_fail "Redis failed to start"; rollback; exit 1; }
    
    sleep 10  # Let Redis stabilize
    
    # Deploy application services
    deploy_phase 7 "06-hypercode-core.yaml" "HyperCode Core & Celery" || { log_fail "Core deployment failed"; rollback; exit 1; }
    wait_for_deployment "hypercode-core" 2 || { log_fail "HyperCode Core failed to start"; rollback; exit 1; }
    
    # Deploy observability
    deploy_phase 8 "07-observability.yaml" "Observability Stack (Prometheus, Grafana)" || { log_fail "Observability deployment failed"; rollback; exit 1; }
    deploy_phase 9 "08-logging-tracing.yaml" "Logging & Tracing (Loki, Tempo)" || { log_fail "Logging deployment failed"; rollback; exit 1; }
    
    # Deploy data services
    deploy_phase 10 "09-data-services.yaml" "Data Services (MinIO, ChromaDB, Ollama)" || { log_fail "Data services deployment failed"; rollback; exit 1; }
    
    # Deploy frontend
    deploy_phase 11 "10-dashboard.yaml" "Dashboard (Frontend)" || { log_fail "Dashboard deployment failed"; rollback; exit 1; }
    wait_for_deployment "dashboard" 2 || { log_fail "Dashboard failed to start"; rollback; exit 1; }
    
    # Deploy networking and policies
    deploy_phase 12 "11-ingress-network-policy.yaml" "Ingress, NetworkPolicy, and HPA" || { log_fail "Ingress deployment failed"; rollback; exit 1; }
    
    # Deploy optional services
    deploy_phase 13 "12-broski-bot.yaml" "Broski Bot (Optional)" || log_warn "Broski Bot deployment had issues (optional service)"
    
    # Deploy monitoring/alerting
    deploy_phase 14 "13-monitoring-alerts.yaml" "Prometheus Rules & Alerts" || log_warn "Alerting configuration had issues"
    
    # Post-deployment checks
    post_deployment_checks || { log_warn "Some post-deployment checks failed"; }
    
    # Generate summary
    generate_summary
    
    log_section "DEPLOYMENT COMPLETE"
    log_pass "HyperCode Kubernetes deployment completed successfully!"
    
    cat << EOF

═══════════════════════════════════════════════════════════════
                    NEXT STEPS
═══════════════════════════════════════════════════════════════

1. Run comprehensive health check:
   ./k8s/health_check.sh

2. Run post-deployment verification:
   ./k8s/post_deployment_check.sh

3. Access services via port-forward:
   
   # Dashboard
   kubectl port-forward -n hypercode svc/dashboard 3000:3000
   
   # API
   kubectl port-forward -n hypercode svc/hypercode-core 8000:8000
   
   # Grafana
   kubectl port-forward -n hypercode svc/grafana 3001:3000
   
   # Prometheus
   kubectl port-forward -n hypercode svc/prometheus 9090:9090

4. Configure ingress domains:
   Update k8s/11-ingress-network-policy.yaml with your domains
   
5. Review logs and troubleshoot if needed:
   cat $LOG_FILE
   cat $BACKUP_DIR/deployment-summary.txt

6. Follow production readiness checklist:
   Review k8s/PRODUCTION_READINESS_CHECKLIST.md

═══════════════════════════════════════════════════════════════
                    IMPORTANT REMINDERS
═══════════════════════════════════════════════════════════════

✓ Update all default secrets before production
✓ Configure proper domains in ingress
✓ Set up SSL/TLS certificates
✓ Configure backup strategy
✓ Test disaster recovery procedures
✓ Set up monitoring and alerting
✓ Document runbooks and escalation procedures

═══════════════════════════════════════════════════════════════

Deployment complete! Log file: $LOG_FILE
Backup location: $BACKUP_DIR

EOF
    
    log "Deployment finished at $(date)"
}

# Parse command-line arguments
case "${1:-}" in
    rollback)
        log_section "MANUAL ROLLBACK REQUESTED"
        if [ -z "$2" ]; then
            log_fail "Usage: $0 rollback <backup-directory>"
            exit 1
        fi
        BACKUP_DIR="$2"
        rollback
        ;;
    check)
        log_section "PRE-DEPLOYMENT CHECKS ONLY"
        pre_deployment_checks
        ;;
    *)
        main
        ;;
esac
