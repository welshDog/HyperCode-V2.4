#!/bin/bash

# HyperCode Kubernetes Cluster Health Check Script
# Comprehensive diagnostics with recommendations for production readiness

set -e

NAMESPACE="hypercode"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPORT_FILE="${SCRIPT_DIR}/health_check_report.txt"
ISSUES_FILE="${SCRIPT_DIR}/issues_and_recommendations.txt"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
CHECKS_TOTAL=0
CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNING=0
CRITICAL_ISSUES=0
WARNINGS=0
INFO_ITEMS=0

# Storage for issues and recommendations
declare -a ISSUES
declare -a RECOMMENDATIONS
declare -a INFO_NOTES

# Helper functions
log_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}" | tee -a "$REPORT_FILE"
}

log_pass() {
    echo -e "${GREEN}✓ $1${NC}" | tee -a "$REPORT_FILE"
    ((CHECKS_PASSED++))
    ((CHECKS_TOTAL++))
}

log_fail() {
    echo -e "${RED}✗ $1${NC}" | tee -a "$REPORT_FILE"
    ((CHECKS_FAILED++))
    ((CHECKS_TOTAL++))
    ((CRITICAL_ISSUES++))
    ISSUES+=("$1")
}

log_warning() {
    echo -e "${YELLOW}⚠ $1${NC}" | tee -a "$REPORT_FILE"
    ((CHECKS_WARNING++))
    ((CHECKS_TOTAL++))
    ((WARNINGS++))
    WARNINGS_ARRAY+=("$1")
}

log_info() {
    echo -e "${BLUE}ℹ $1${NC}" | tee -a "$REPORT_FILE"
    ((INFO_ITEMS++))
    INFO_NOTES+=("$1")
}

add_recommendation() {
    RECOMMENDATIONS+=("$1")
}

# Clear previous reports
> "$REPORT_FILE"
> "$ISSUES_FILE"

echo "HyperCode Kubernetes Health Check" | tee -a "$REPORT_FILE"
echo "Timestamp: $(date)" | tee -a "$REPORT_FILE"
echo "Namespace: $NAMESPACE" | tee -a "$REPORT_FILE"

# Check 1: Cluster connectivity
log_header "1. Cluster Connectivity"
if kubectl cluster-info &>/dev/null; then
    log_pass "Cluster is accessible"
    CLUSTER_VERSION=$(kubectl version --short 2>/dev/null | grep "Server" | awk '{print $3}')
    log_info "Kubernetes version: $CLUSTER_VERSION"
else
    log_fail "Cannot connect to cluster"
    add_recommendation "Verify kubeconfig is correctly configured: kubectl config view"
    exit 1
fi

# Check 2: Namespace existence
log_header "2. Namespace Configuration"
if kubectl get namespace "$NAMESPACE" &>/dev/null; then
    log_pass "Namespace '$NAMESPACE' exists"
else
    log_fail "Namespace '$NAMESPACE' does not exist"
    add_recommendation "Create namespace: kubectl create namespace $NAMESPACE"
    exit 1
fi

# Check 3: Storage Classes
log_header "3. Storage Configuration"
if kubectl get storageclass &>/dev/null; then
    SC_COUNT=$(kubectl get storageclass --no-headers 2>/dev/null | wc -l)
    if [ "$SC_COUNT" -gt 0 ]; then
        log_pass "Storage classes available: $SC_COUNT"
        DEFAULT_SC=$(kubectl get storageclass -o jsonpath='{.items[?(@.metadata.annotations.storageclass\.kubernetes\.io/is-default-class=="true")].metadata.name}' 2>/dev/null)
        if [ -z "$DEFAULT_SC" ]; then
            log_warning "No default storage class found"
            add_recommendation "Set a default storage class: kubectl patch storageclass <storageclass-name> -p '{\"metadata\": {\"annotations\":{\"storageclass.kubernetes.io/is-default-class\":\"true\"}}}'"
        else
            log_info "Default storage class: $DEFAULT_SC"
        fi
    else
        log_fail "No storage classes available"
        add_recommendation "Create a storage class appropriate for your cluster (EBS for AWS, GCE for GCP, etc.)"
    fi
else
    log_warning "Could not retrieve storage classes"
fi

# Check 4: PVCs
log_header "4. Persistent Volumes"
PVC_COUNT=$(kubectl get pvc -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
if [ "$PVC_COUNT" -gt 0 ]; then
    log_pass "PersistentVolumeClaims found: $PVC_COUNT"
    
    # Check for unbound PVCs
    UNBOUND_PVC=$(kubectl get pvc -n "$NAMESPACE" --no-headers 2>/dev/null | grep -v "Bound" | wc -l)
    if [ "$UNBOUND_PVC" -gt 0 ]; then
        log_fail "$UNBOUND_PVC PVC(s) are not Bound"
        add_recommendation "Check PVC status: kubectl describe pvc -n $NAMESPACE"
    else
        log_pass "All PVCs are Bound"
    fi
    
    # Check storage usage
    log_info "PVC Status:"
    kubectl get pvc -n "$NAMESPACE" -o wide --no-headers 2>/dev/null | while read -r line; do
        echo "  $line" | tee -a "$REPORT_FILE"
    done
else
    log_warning "No PersistentVolumeClaims found"
    add_recommendation "Create PVCs: kubectl apply -f k8s/03-pvcs.yaml"
fi

# Check 5: Secrets
log_header "5. Secrets Management"
SECRET_COUNT=$(kubectl get secrets -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
if [ "$SECRET_COUNT" -gt 0 ]; then
    log_pass "Secrets found: $SECRET_COUNT"
    
    # Check for required secrets
    if kubectl get secret hypercode-secrets -n "$NAMESPACE" &>/dev/null; then
        log_pass "hypercode-secrets secret exists"
        
        # Verify critical secret keys
        REQUIRED_KEYS=("POSTGRES_PASSWORD" "HYPERCODE_JWT_SECRET" "API_KEY" "PERPLEXITY_API_KEY")
        for key in "${REQUIRED_KEYS[@]}"; do
            if kubectl get secret hypercode-secrets -n "$NAMESPACE" -o jsonpath="{.data.$key}" 2>/dev/null | grep -q .; then
                log_pass "Secret key '$key' is set"
            else
                log_warning "Secret key '$key' is empty or missing"
                add_recommendation "Set the '$key' in secrets: kubectl patch secret hypercode-secrets -n $NAMESPACE -p '{\"data\":{\"$key\":\"<base64-value>\"}}'"
            fi
        done
    else
        log_fail "hypercode-secrets secret not found"
        add_recommendation "Create secrets: kubectl apply -f k8s/02-secrets.yaml"
    fi
else
    log_warning "No secrets found"
    add_recommendation "Create secrets: kubectl apply -f k8s/02-secrets.yaml"
fi

# Check 6: ConfigMaps
log_header "6. Configuration Management"
CM_COUNT=$(kubectl get configmap -n "$NAMESPACE" --no-headers 2>/dev/null | grep -v "kube-root-ca.crt" | wc -l)
if [ "$CM_COUNT" -gt 0 ]; then
    log_pass "ConfigMaps found: $CM_COUNT"
else
    log_warning "No ConfigMaps found"
    add_recommendation "Create ConfigMaps: kubectl apply -f k8s/01-configmaps.yaml"
fi

# Check 7: Database (PostgreSQL)
log_header "7. Database Status"
if kubectl get statefulset postgres -n "$NAMESPACE" &>/dev/null; then
    log_pass "PostgreSQL StatefulSet exists"
    
    POSTGRES_READY=$(kubectl get statefulset postgres -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}' 2>/dev/null)
    POSTGRES_DESIRED=$(kubectl get statefulset postgres -n "$NAMESPACE" -o jsonpath='{.status.replicas}' 2>/dev/null)
    
    if [ "$POSTGRES_READY" == "$POSTGRES_DESIRED" ] && [ ! -z "$POSTGRES_READY" ]; then
        log_pass "PostgreSQL replicas ready: $POSTGRES_READY/$POSTGRES_DESIRED"
        
        # Test database connectivity
        if kubectl exec -n "$NAMESPACE" postgres-0 -- pg_isready -U postgres &>/dev/null; then
            log_pass "PostgreSQL is responding to connections"
            
            # Check replication status
            REPLICATION_STATUS=$(kubectl exec -n "$NAMESPACE" postgres-0 -- psql -U postgres -t -c "SELECT count(*) FROM pg_stat_replication;" 2>/dev/null || echo "0")
            log_info "PostgreSQL replication slots: $REPLICATION_STATUS"
        else
            log_fail "PostgreSQL is not responding to health checks"
            add_recommendation "Check PostgreSQL pod logs: kubectl logs -n $NAMESPACE postgres-0"
        fi
    else
        log_warning "PostgreSQL replicas not fully ready: $POSTGRES_READY/$POSTGRES_DESIRED"
        add_recommendation "Check PostgreSQL pod status: kubectl describe pod postgres-0 -n $NAMESPACE"
    fi
    
    # Check for pod issues
    POSTGRES_POD_STATUS=$(kubectl get pod postgres-0 -n "$NAMESPACE" -o jsonpath='{.status.phase}' 2>/dev/null)
    if [ "$POSTGRES_POD_STATUS" != "Running" ]; then
        log_fail "PostgreSQL pod status: $POSTGRES_POD_STATUS"
        add_recommendation "Check pod logs: kubectl logs -n $NAMESPACE postgres-0 --previous"
    fi
else
    log_fail "PostgreSQL StatefulSet not found"
    add_recommendation "Deploy PostgreSQL: kubectl apply -f k8s/04-postgres.yaml"
fi

# Check 8: Redis
log_header "8. Cache (Redis) Status"
if kubectl get statefulset redis -n "$NAMESPACE" &>/dev/null; then
    log_pass "Redis StatefulSet exists"
    
    REDIS_READY=$(kubectl get statefulset redis -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}' 2>/dev/null)
    REDIS_DESIRED=$(kubectl get statefulset redis -n "$NAMESPACE" -o jsonpath='{.status.replicas}' 2>/dev/null)
    
    if [ "$REDIS_READY" == "$REDIS_DESIRED" ] && [ ! -z "$REDIS_READY" ]; then
        log_pass "Redis replicas ready: $REDIS_READY/$REDIS_DESIRED"
        
        # Test Redis connectivity
        if kubectl exec -n "$NAMESPACE" redis-0 -- redis-cli ping &>/dev/null; then
            log_pass "Redis is responding to health checks"
            
            # Check memory usage
            REDIS_MEMORY=$(kubectl exec -n "$NAMESPACE" redis-0 -- redis-cli info memory 2>/dev/null | grep used_memory_human | cut -d: -f2)
            log_info "Redis memory usage: $REDIS_MEMORY"
        else
            log_fail "Redis is not responding to health checks"
            add_recommendation "Check Redis pod logs: kubectl logs -n $NAMESPACE redis-0"
        fi
    else
        log_warning "Redis replicas not fully ready: $REDIS_READY/$REDIS_DESIRED"
        add_recommendation "Check Redis pod status: kubectl describe pod redis-0 -n $NAMESPACE"
    fi
else
    log_fail "Redis StatefulSet not found"
    add_recommendation "Deploy Redis: kubectl apply -f k8s/05-redis.yaml"
fi

# Check 9: Core Application
log_header "9. HyperCode Core Service"
if kubectl get deployment hypercode-core -n "$NAMESPACE" &>/dev/null; then
    log_pass "HyperCode Core Deployment exists"
    
    CORE_READY=$(kubectl get deployment hypercode-core -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
    CORE_DESIRED=$(kubectl get deployment hypercode-core -n "$NAMESPACE" -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "0")
    
    if [ "$CORE_READY" == "$CORE_DESIRED" ] && [ "$CORE_READY" -gt 0 ]; then
        log_pass "HyperCode Core replicas ready: $CORE_READY/$CORE_DESIRED"
        
        # Test health endpoint
        CORE_POD=$(kubectl get pod -n "$NAMESPACE" -l app=hypercode-core -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
        if [ ! -z "$CORE_POD" ]; then
            if kubectl exec -n "$NAMESPACE" "$CORE_POD" -- curl -s http://localhost:8000/health &>/dev/null; then
                log_pass "HyperCode Core health endpoint responding"
            else
                log_warning "HyperCode Core health endpoint not responding"
                add_recommendation "Check pod logs: kubectl logs -n $NAMESPACE $CORE_POD"
            fi
        fi
    else
        if [ "$CORE_READY" -eq 0 ]; then
            log_fail "HyperCode Core pods not ready: $CORE_READY/$CORE_DESIRED"
        else
            log_warning "HyperCode Core pods partially ready: $CORE_READY/$CORE_DESIRED"
        fi
        add_recommendation "Check pod status: kubectl describe pod -n $NAMESPACE -l app=hypercode-core"
    fi
    
    # Check resource requests vs actual usage
    CORE_CPU=$(kubectl top pod -n "$NAMESPACE" -l app=hypercode-core --no-headers 2>/dev/null | awk '{sum+=$1} END {print sum}')
    CORE_MEM=$(kubectl top pod -n "$NAMESPACE" -l app=hypercode-core --no-headers 2>/dev/null | awk '{sum+=$2} END {print sum}')
    if [ ! -z "$CORE_CPU" ] && [ "$CORE_CPU" != "0" ]; then
        log_info "HyperCode Core resource usage - CPU: ${CORE_CPU}m, Memory: ${CORE_MEM}Mi"
    fi
else
    log_fail "HyperCode Core Deployment not found"
    add_recommendation "Deploy HyperCode Core: kubectl apply -f k8s/06-hypercode-core.yaml"
fi

# Check 10: Celery Worker
log_header "10. Celery Worker Status"
if kubectl get deployment celery-worker -n "$NAMESPACE" &>/dev/null; then
    log_pass "Celery Worker Deployment exists"
    
    WORKER_READY=$(kubectl get deployment celery-worker -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
    WORKER_DESIRED=$(kubectl get deployment celery-worker -n "$NAMESPACE" -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "0")
    
    if [ "$WORKER_READY" == "$WORKER_DESIRED" ] && [ "$WORKER_READY" -gt 0 ]; then
        log_pass "Celery Worker replicas ready: $WORKER_READY/$WORKER_DESIRED"
    else
        log_warning "Celery Worker pods not fully ready: $WORKER_READY/$WORKER_DESIRED"
        add_recommendation "Check pod status: kubectl describe pod -n $NAMESPACE -l app=celery-worker"
    fi
else
    log_fail "Celery Worker Deployment not found"
    add_recommendation "Deploy Celery Worker: kubectl apply -f k8s/06-hypercode-core.yaml"
fi

# Check 11: Dashboard
log_header "11. Dashboard (Frontend) Status"
if kubectl get deployment dashboard -n "$NAMESPACE" &>/dev/null; then
    log_pass "Dashboard Deployment exists"
    
    DASH_READY=$(kubectl get deployment dashboard -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
    DASH_DESIRED=$(kubectl get deployment dashboard -n "$NAMESPACE" -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "0")
    
    if [ "$DASH_READY" == "$DASH_DESIRED" ] && [ "$DASH_READY" -gt 0 ]; then
        log_pass "Dashboard replicas ready: $DASH_READY/$DASH_DESIRED"
    else
        log_warning "Dashboard pods not fully ready: $DASH_READY/$DASH_DESIRED"
        add_recommendation "Check pod status: kubectl describe pod -n $NAMESPACE -l app=dashboard"
    fi
else
    log_warning "Dashboard Deployment not found"
    add_recommendation "Deploy Dashboard: kubectl apply -f k8s/10-dashboard.yaml"
fi

# Check 12: Observability Stack
log_header "12. Observability Stack"
OBSERVABILITY_APPS=("prometheus" "grafana" "node-exporter")
for app in "${OBSERVABILITY_APPS[@]}"; do
    if kubectl get deployment "$app" -n "$NAMESPACE" &>/dev/null; then
        READY=$(kubectl get deployment "$app" -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
        DESIRED=$(kubectl get deployment "$app" -n "$NAMESPACE" -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "0")
        
        if [ "$READY" == "$DESIRED" ] && [ "$READY" -gt 0 ]; then
            log_pass "$app deployment is ready"
        else
            log_warning "$app deployment not fully ready: $READY/$DESIRED"
        fi
    else
        log_warning "$app deployment not found"
    fi
done

add_recommendation "Deploy observability stack: kubectl apply -f k8s/07-observability.yaml"

# Check 13: Logging and Tracing
log_header "13. Logging & Tracing Stack"
LOGGING_APPS=("loki" "tempo")
for app in "${LOGGING_APPS[@]}"; do
    if kubectl get deployment "$app" -n "$NAMESPACE" &>/dev/null; then
        READY=$(kubectl get deployment "$app" -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
        DESIRED=$(kubectl get deployment "$app" -n "$NAMESPACE" -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "0")
        
        if [ "$READY" == "$DESIRED" ] && [ "$READY" -gt 0 ]; then
            log_pass "$app deployment is ready"
        else
            log_warning "$app deployment not fully ready: $READY/$DESIRED"
        fi
    else
        log_warning "$app deployment not found"
    fi
done

add_recommendation "Deploy logging/tracing stack: kubectl apply -f k8s/08-logging-tracing.yaml"

# Check 14: Data Services
log_header "14. Data Services"
DATA_APPS=("minio" "chroma" "ollama")
for app in "${DATA_APPS[@]}"; do
    if kubectl get deployment "$app" -n "$NAMESPACE" &>/dev/null; then
        READY=$(kubectl get deployment "$app" -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
        DESIRED=$(kubectl get deployment "$app" -n "$NAMESPACE" -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "0")
        
        if [ "$READY" == "$DESIRED" ] && [ "$READY" -gt 0 ]; then
            log_pass "$app deployment is ready"
        else
            log_warning "$app deployment not fully ready: $READY/$DESIRED"
        fi
    else
        log_warning "$app deployment not found"
    fi
done

add_recommendation "Deploy data services: kubectl apply -f k8s/09-data-services.yaml"

# Check 15: Services and Endpoints
log_header "15. Service Endpoints"
SERVICES=$(kubectl get svc -n "$NAMESPACE" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null)
SERVICE_COUNT=$(echo "$SERVICES" | wc -w)
if [ "$SERVICE_COUNT" -gt 0 ]; then
    log_pass "Services configured: $SERVICE_COUNT"
    
    # Check for services without endpoints
    for svc in $SERVICES; do
        ENDPOINTS=$(kubectl get endpoints "$svc" -n "$NAMESPACE" -o jsonpath='{.subsets[*].addresses[*].ip}' 2>/dev/null | wc -w)
        if [ "$ENDPOINTS" -eq 0 ]; then
            log_warning "Service '$svc' has no active endpoints"
            add_recommendation "Check service and pod status: kubectl describe svc $svc -n $NAMESPACE"
        fi
    done
else
    log_warning "No services found"
    add_recommendation "Create services by deploying manifests"
fi

# Check 16: Ingress
log_header "16. Ingress Configuration"
if kubectl get ingress -n "$NAMESPACE" &>/dev/null; then
    INGRESS_COUNT=$(kubectl get ingress -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
    if [ "$INGRESS_COUNT" -gt 0 ]; then
        log_pass "Ingress configuration found: $INGRESS_COUNT"
        
        # Check ingress controller
        INGRESS_CLASS=$(kubectl get ingressclass --no-headers 2>/dev/null | wc -l)
        if [ "$INGRESS_CLASS" -gt 0 ]; then
            log_pass "Ingress controller available"
        else
            log_warning "No Ingress controller found"
            add_recommendation "Install ingress controller: kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/cloud/deploy.yaml"
        fi
        
        # Check ingress IPs
        INGRESS_IP=$(kubectl get ingress -n "$NAMESPACE" -o jsonpath='{.items[0].status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")
        if [ "$INGRESS_IP" != "pending" ] && [ ! -z "$INGRESS_IP" ]; then
            log_pass "Ingress IP assigned: $INGRESS_IP"
        else
            log_warning "Ingress IP not yet assigned (may be pending)"
            add_recommendation "Wait for LoadBalancer to assign IP or check cloud provider settings"
        fi
    else
        log_warning "No Ingress found"
    fi
else
    log_warning "Could not check ingress"
fi

# Check 17: Network Policies
log_header "17. Network Policies"
if kubectl get networkpolicy -n "$NAMESPACE" &>/dev/null; then
    NP_COUNT=$(kubectl get networkpolicy -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
    if [ "$NP_COUNT" -gt 0 ]; then
        log_pass "Network policies configured: $NP_COUNT"
    else
        log_warning "No network policies found"
        add_recommendation "Apply network policies: kubectl apply -f k8s/11-ingress-network-policy.yaml"
    fi
else
    log_warning "Could not check network policies"
fi

# Check 18: HorizontalPodAutoscaler
log_header "18. Auto-Scaling Configuration"
HPA_COUNT=$(kubectl get hpa -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
if [ "$HPA_COUNT" -gt 0 ]; then
    log_pass "HPA policies configured: $HPA_COUNT"
    kubectl get hpa -n "$NAMESPACE" -o wide --no-headers 2>/dev/null | while read -r line; do
        echo "  $line" | tee -a "$REPORT_FILE"
    done
else
    log_warning "No HPA policies found"
    add_recommendation "Configure HPA: kubectl apply -f k8s/11-ingress-network-policy.yaml"
fi

# Check 19: Resource Quotas
log_header "19. Resource Quotas"
QUOTA_COUNT=$(kubectl get resourcequota -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
if [ "$QUOTA_COUNT" -gt 0 ]; then
    log_pass "Resource quotas configured: $QUOTA_COUNT"
    kubectl describe resourcequota -n "$NAMESPACE" 2>/dev/null | tee -a "$REPORT_FILE"
else
    log_warning "No resource quotas found"
    add_recommendation "Configure resource quotas: kubectl apply -f k8s/11-ingress-network-policy.yaml"
fi

# Check 20: Node Status
log_header "20. Cluster Nodes"
NODE_COUNT=$(kubectl get nodes --no-headers 2>/dev/null | wc -l)
if [ "$NODE_COUNT" -gt 0 ]; then
    log_pass "Cluster nodes: $NODE_COUNT"
    
    # Check node status
    UNHEALTHY_NODES=$(kubectl get nodes --no-headers 2>/dev/null | grep -v "Ready" | wc -l)
    if [ "$UNHEALTHY_NODES" -eq 0 ]; then
        log_pass "All nodes are Ready"
    else
        log_warning "$UNHEALTHY_NODES node(s) are not Ready"
        add_recommendation "Check node status: kubectl describe node"
    fi
    
    # Check node resources
    echo "Node Resource Summary:" | tee -a "$REPORT_FILE"
    kubectl top nodes 2>/dev/null | tee -a "$REPORT_FILE" || log_info "Metrics not available (install metrics-server)"
else
    log_fail "No nodes available"
    add_recommendation "Ensure cluster is properly configured"
fi

# Check 21: Pod Resource Usage
log_header "21. Pod Resource Usage"
if kubectl top pods -n "$NAMESPACE" &>/dev/null; then
    echo "Top resource-consuming pods:" | tee -a "$REPORT_FILE"
    kubectl top pods -n "$NAMESPACE" --sort-by=memory 2>/dev/null | head -10 | tee -a "$REPORT_FILE"
else
    log_info "Metrics not available (install metrics-server if needed)"
fi

# Check 22: Pod Disruption Budgets
log_header "22. Pod Disruption Budgets (HA)"
PDB_COUNT=$(kubectl get pdb -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
if [ "$PDB_COUNT" -gt 0 ]; then
    log_pass "PDB policies configured: $PDB_COUNT"
else
    log_warning "No PDB policies found"
    add_recommendation "Configure PDB: kubectl apply -f k8s/11-ingress-network-policy.yaml"
fi

# Check 23: RBAC
log_header "23. RBAC Configuration"
ROLE_COUNT=$(kubectl get roles -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
ROLEBINDING_COUNT=$(kubectl get rolebindings -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
if [ "$ROLE_COUNT" -gt 0 ] || [ "$ROLEBINDING_COUNT" -gt 0 ]; then
    log_info "Roles: $ROLE_COUNT, RoleBindings: $ROLEBINDING_COUNT"
else
    log_warning "No RBAC rules configured"
    add_recommendation "Consider setting up RBAC for service accounts and pod access control"
fi

# Check 24: Container Image Status
log_header "24. Container Image Status"
PENDING_PODS=$(kubectl get pods -n "$NAMESPACE" -o jsonpath='{.items[?(@.status.phase=="Pending")].metadata.name}' 2>/dev/null)
if [ ! -z "$PENDING_PODS" ]; then
    log_warning "Pods pending (possibly waiting for images):"
    echo "$PENDING_PODS" | while read -r pod; do
        echo "  - $pod" | tee -a "$REPORT_FILE"
    done
    add_recommendation "Check image pull status: kubectl describe pod <pod-name> -n $NAMESPACE"
else
    log_pass "No pods pending on image pull"
fi

# Check 25: Recent Events
log_header "25. Recent Cluster Events"
echo "Recent warnings and errors (last 10 minutes):" | tee -a "$REPORT_FILE"
kubectl get events -n "$NAMESPACE" --sort-by='.lastTimestamp' 2>/dev/null | grep -E "Warning|Error" | tail -10 | tee -a "$REPORT_FILE"

# Generate Summary Report
log_header "SUMMARY REPORT"
echo "" | tee -a "$REPORT_FILE"
echo "Total Checks: $CHECKS_TOTAL" | tee -a "$REPORT_FILE"
echo "Passed: $CHECKS_PASSED" | tee -a "$REPORT_FILE"
echo "Warnings: $CHECKS_WARNING" | tee -a "$REPORT_FILE"
echo "Failed: $CHECKS_FAILED" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

# Generate Recommendations Report
{
    echo "==============================================="
    echo "ISSUES AND RECOMMENDATIONS"
    echo "==============================================="
    echo "Generated: $(date)"
    echo ""
    
    if [ ${#ISSUES[@]} -gt 0 ]; then
        echo "CRITICAL ISSUES ($CRITICAL_ISSUES):"
        echo "-----------------------------------"
        for i in "${!ISSUES[@]}"; do
            echo "$((i+1)). ${ISSUES[$i]}"
        done
        echo ""
    fi
    
    if [ ${#WARNINGS_ARRAY[@]} -gt 0 ]; then
        echo "WARNINGS ($WARNINGS):"
        echo "--------------------"
        for i in "${!WARNINGS_ARRAY[@]}"; do
            echo "$((i+1)). ${WARNINGS_ARRAY[$i]}"
        done
        echo ""
    fi
    
    if [ ${#RECOMMENDATIONS[@]} -gt 0 ]; then
        echo "RECOMMENDATIONS:"
        echo "----------------"
        # Remove duplicates and print
        printf '%s\n' "${RECOMMENDATIONS[@]}" | sort -u | nl
        echo ""
    fi
    
    echo "PRODUCTION READINESS CHECKLIST:"
    echo "--------------------------------"
    [ ${#ISSUES[@]} -eq 0 ] && echo "✓ No critical issues" || echo "✗ Critical issues present"
    [ ${#WARNINGS_ARRAY[@]} -eq 0 ] && echo "✓ No warnings" || echo "✗ Warnings present"
    kubectl get pdb -n "$NAMESPACE" &>/dev/null && echo "✓ Pod Disruption Budgets configured" || echo "✗ Pod Disruption Budgets missing"
    kubectl get hpa -n "$NAMESPACE" &>/dev/null && echo "✓ Auto-scaling configured" || echo "✗ Auto-scaling not configured"
    kubectl get networkpolicy -n "$NAMESPACE" &>/dev/null && echo "✓ Network policies configured" || echo "✗ Network policies missing"
    kubectl get ingress -n "$NAMESPACE" &>/dev/null && echo "✓ Ingress configured" || echo "✗ Ingress not configured"
    
} | tee "$ISSUES_FILE"

# Final Status
log_header "HEALTH CHECK COMPLETE"
if [ "$CHECKS_FAILED" -eq 0 ]; then
    echo -e "${GREEN}Status: ✓ HEALTHY - System is ready for operation${NC}"
    EXIT_CODE=0
elif [ "$CHECKS_WARNING" -gt 0 ] && [ "$CHECKS_FAILED" -eq 0 ]; then
    echo -e "${YELLOW}Status: ⚠ PARTIAL - Some warnings present, review recommendations${NC}"
    EXIT_CODE=1
else
    echo -e "${RED}Status: ✗ UNHEALTHY - Critical issues detected, action required${NC}"
    EXIT_CODE=2
fi

echo "" | tee -a "$REPORT_FILE"
echo "Reports saved to:" | tee -a "$REPORT_FILE"
echo "  - Health Check: $REPORT_FILE" | tee -a "$REPORT_FILE"
echo "  - Issues & Recommendations: $ISSUES_FILE" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

exit $EXIT_CODE
