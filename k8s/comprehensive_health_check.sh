#!/bin/bash

# HyperCode Kubernetes - Complete Health Check & Recommendations Report
# Generates comprehensive health assessment with actionable recommendations

NAMESPACE="hypercode"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="${SCRIPT_DIR}/HEALTH_CHECK_REPORT_${TIMESTAMP}.html"
JSON_REPORT="${SCRIPT_DIR}/health_check_${TIMESTAMP}.json"

# Color codes for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Counters and storage
declare -A CHECKS
declare -a CRITICAL_ISSUES
declare -a WARNINGS
declare -a INFO_ITEMS
declare -a RECOMMENDATIONS
HEALTH_SCORE=100

# Helper functions
log_check() {
    local status=$1
    local name=$2
    local value=$3
    
    CHECKS["$name"]="$status"
    
    case "$status" in
        "PASS")
            echo -e "${GREEN}✓${NC} $name: ${GREEN}$value${NC}"
            ;;
        "WARN")
            echo -e "${YELLOW}⚠${NC} $name: ${YELLOW}$value${NC}"
            HEALTH_SCORE=$((HEALTH_SCORE - 5))
            WARNINGS+=("$name: $value")
            ;;
        "FAIL")
            echo -e "${RED}✗${NC} $name: ${RED}$value${NC}"
            HEALTH_SCORE=$((HEALTH_SCORE - 15))
            CRITICAL_ISSUES+=("$name: $value")
            ;;
        "INFO")
            echo -e "${CYAN}ℹ${NC} $name: $value"
            INFO_ITEMS+=("$name: $value")
            ;;
    esac
}

add_recommendation() {
    local priority=$1
    local title=$2
    local description=$3
    local command=$4
    
    RECOMMENDATIONS+=("[$priority] $title|$description|$command")
}

# HTML Header
generate_html_header() {
    cat > "$REPORT_FILE" << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HyperCode Kubernetes Health Check Report</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }
        header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .timestamp { font-size: 0.9em; opacity: 0.9; }
        
        .health-score {
            text-align: center;
            padding: 30px;
            background: #f8f9fa;
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 40px;
        }
        .score-circle {
            width: 150px;
            height: 150px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 3em;
            font-weight: bold;
            color: white;
        }
        .score-excellent { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .score-good { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
        .score-warning { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); }
        .score-critical { background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%); }
        
        .score-info {
            flex: 1;
        }
        .score-info h2 { margin: 10px 0; }
        .score-info p { margin: 5px 0; color: #666; }
        
        .section {
            margin: 20px;
            border-radius: 8px;
            border-left: 5px solid #667eea;
            background: #f8f9fa;
            padding: 20px;
        }
        .section h2 {
            margin-bottom: 15px;
            color: #333;
            font-size: 1.5em;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        
        .check-item {
            padding: 12px;
            margin: 8px 0;
            border-radius: 6px;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .check-pass { background: #d4edda; color: #155724; }
        .check-warn { background: #fff3cd; color: #856404; }
        .check-fail { background: #f8d7da; color: #721c24; }
        .check-info { background: #d1ecf1; color: #0c5460; }
        
        .check-icon {
            font-size: 1.5em;
            font-weight: bold;
            min-width: 30px;
        }
        
        .recommendation {
            padding: 15px;
            margin: 10px 0;
            border-radius: 6px;
            border-left: 4px solid;
        }
        .rec-critical { background: #ffe6e6; border-color: #ff4444; }
        .rec-high { background: #fff4e6; border-color: #ff9800; }
        .rec-medium { background: #f0f4ff; border-color: #2196f3; }
        .rec-low { background: #e8f5e9; border-color: #4caf50; }
        
        .rec-priority {
            font-weight: bold;
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            margin-right: 10px;
            font-size: 0.85em;
        }
        .rec-critical .rec-priority { background: #ff4444; color: white; }
        .rec-high .rec-priority { background: #ff9800; color: white; }
        .rec-medium .rec-priority { background: #2196f3; color: white; }
        .rec-low .rec-priority { background: #4caf50; color: white; }
        
        .rec-title { font-weight: bold; margin-bottom: 8px; }
        .rec-desc { margin: 8px 0; font-size: 0.95em; }
        .rec-command {
            background: #1e1e1e;
            color: #0fb881;
            padding: 10px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 0.85em;
            overflow-x: auto;
            margin-top: 8px;
        }
        
        .action-item {
            padding: 15px;
            margin: 10px 0;
            border-radius: 6px;
            background: #fff9e6;
            border-left: 4px solid #ff9800;
        }
        .action-item strong { color: #ff6f00; }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 15px 0;
        }
        .stat-card {
            background: white;
            padding: 15px;
            border-radius: 6px;
            border: 1px solid #ddd;
            text-align: center;
        }
        .stat-card .value {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }
        .stat-card .label {
            color: #666;
            font-size: 0.9em;
            margin-top: 5px;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }
        table th {
            background: #667eea;
            color: white;
            padding: 12px;
            text-align: left;
        }
        table td {
            padding: 10px 12px;
            border-bottom: 1px solid #ddd;
        }
        table tr:nth-child(even) {
            background: #f9f9f9;
        }
        
        footer {
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            border-top: 1px solid #ddd;
        }
        
        .status-badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.9em;
        }
        .status-healthy { background: #4caf50; color: white; }
        .status-warning { background: #ff9800; color: white; }
        .status-critical { background: #f44336; color: white; }
        
        @media print {
            body { background: white; }
            .container { box-shadow: none; }
        }
    </style>
</head>
<body>
<div class="container">
EOF
}

# Main health check execution
echo -e "\n${MAGENTA}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${MAGENTA}║     HyperCode Kubernetes - Complete Health Check          ║${NC}"
echo -e "${MAGENTA}╚════════════════════════════════════════════════════════════╝${NC}\n"

# Generate HTML header
generate_html_header

# Start health check
echo -e "${BLUE}Starting comprehensive health assessment...${NC}\n"

# ============ CLUSTER HEALTH ============
echo -e "${MAGENTA}═══ CLUSTER HEALTH ===${NC}"

if kubectl cluster-info &>/dev/null; then
    KUBE_VERSION=$(kubectl version --short 2>/dev/null | grep Server | awk '{print $3}')
    log_check "PASS" "Cluster Connectivity" "Connected (v$KUBE_VERSION)"
else
    log_check "FAIL" "Cluster Connectivity" "Cannot connect to cluster"
fi

NODE_COUNT=$(kubectl get nodes --no-headers 2>/dev/null | wc -l)
log_check "PASS" "Node Count" "$NODE_COUNT nodes"

READY_NODES=$(kubectl get nodes --no-headers 2>/dev/null | grep " Ready " | wc -l)
if [ "$READY_NODES" == "$NODE_COUNT" ]; then
    log_check "PASS" "All Nodes Ready" "$READY_NODES/$NODE_COUNT"
else
    log_check "WARN" "Node Status" "$READY_NODES/$NODE_COUNT ready"
    add_recommendation "HIGH" "Fix unhealthy nodes" "Some nodes are not ready" "kubectl describe node | grep -A 10 'NotReady'"
fi

# ============ NAMESPACE ============
echo -e "\n${MAGENTA}═══ NAMESPACE CONFIGURATION ===${NC}"

if kubectl get namespace "$NAMESPACE" &>/dev/null; then
    log_check "PASS" "Namespace Exists" "$NAMESPACE"
else
    log_check "FAIL" "Namespace Exists" "$NAMESPACE not found"
    add_recommendation "CRITICAL" "Create namespace" "The namespace doesn't exist" "kubectl create namespace $NAMESPACE"
fi

# ============ STORAGE ============
echo -e "\n${MAGENTA}═══ STORAGE CONFIGURATION ===${NC}"

SC_COUNT=$(kubectl get storageclass --no-headers 2>/dev/null | wc -l)
if [ "$SC_COUNT" -gt 0 ]; then
    log_check "PASS" "Storage Classes" "$SC_COUNT available"
    
    DEFAULT_SC=$(kubectl get storageclass -o jsonpath='{.items[?(@.metadata.annotations.storageclass\.kubernetes\.io/is-default-class=="true")].metadata.name}' 2>/dev/null)
    if [ -z "$DEFAULT_SC" ]; then
        log_check "WARN" "Default Storage Class" "Not set"
        add_recommendation "MEDIUM" "Set default storage class" "No default storage class is configured" "kubectl patch storageclass <name> -p '{\"metadata\": {\"annotations\":{\"storageclass.kubernetes.io/is-default-class\":\"true\"}}}'"
    else
        log_check "PASS" "Default Storage Class" "$DEFAULT_SC"
    fi
else
    log_check "FAIL" "Storage Classes" "No storage classes found"
    add_recommendation "CRITICAL" "Create storage class" "Storage class is required for persistent volumes"
fi

PVC_COUNT=$(kubectl get pvc -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
if [ "$PVC_COUNT" -gt 0 ]; then
    log_check "PASS" "Persistent Volumes" "$PVC_COUNT PVCs"
    
    BOUND_PVC=$(kubectl get pvc -n "$NAMESPACE" -o jsonpath='{.items[?(@.status.phase=="Bound")]}' | wc -w)
    UNBOUND_PVC=$((PVC_COUNT - BOUND_PVC))
    
    if [ "$UNBOUND_PVC" -eq 0 ]; then
        log_check "PASS" "PVC Binding" "All $PVC_COUNT bound"
    else
        log_check "WARN" "PVC Binding" "$UNBOUND_PVC/$PVC_COUNT unbound"
        add_recommendation "HIGH" "Fix unbound PVCs" "Some PVCs are not bound to volumes" "kubectl describe pvc -n $NAMESPACE | grep -A 5 'Pending'"
    fi
else
    log_check "FAIL" "Persistent Volumes" "No PVCs found"
    add_recommendation "CRITICAL" "Create PVCs" "PVCs are required for data persistence" "kubectl apply -f k8s/03-pvcs.yaml"
fi

# ============ SECRETS & CONFIG ============
echo -e "\n${MAGENTA}═══ SECRETS & CONFIGURATION ===${NC}"

if kubectl get secret hypercode-secrets -n "$NAMESPACE" &>/dev/null; then
    log_check "PASS" "Secrets Exist" "hypercode-secrets found"
    
    # Check for default/insecure values
    INSECURE_SECRETS=$(kubectl get secret hypercode-secrets -n "$NAMESPACE" -o yaml 2>/dev/null | grep -E 'changeme|dev-key|admin' | wc -l)
    if [ "$INSECURE_SECRETS" -gt 0 ]; then
        log_check "FAIL" "Secrets Security" "$INSECURE_SECRETS insecure values detected"
        add_recommendation "CRITICAL" "Update default secrets" "Default secrets are still in use - SECURITY RISK" "kubectl patch secret hypercode-secrets -n $NAMESPACE -p '{\"data\":{\"API_KEY\":\"$(echo -n 'strong-key' | base64)\"}}'"
    else
        log_check "PASS" "Secrets Security" "No default values detected"
    fi
else
    log_check "FAIL" "Secrets Exist" "hypercode-secrets not found"
    add_recommendation "CRITICAL" "Create secrets" "Required secrets are missing" "kubectl apply -f k8s/02-secrets.yaml"
fi

CM_COUNT=$(kubectl get configmap -n "$NAMESPACE" --no-headers 2>/dev/null | grep -v "kube-root-ca" | wc -l)
if [ "$CM_COUNT" -gt 0 ]; then
    log_check "PASS" "ConfigMaps" "$CM_COUNT ConfigMaps"
else
    log_check "WARN" "ConfigMaps" "No ConfigMaps found"
    add_recommendation "MEDIUM" "Create ConfigMaps" "No configuration maps are deployed" "kubectl apply -f k8s/01-configmaps.yaml"
fi

# ============ DATABASE ============
echo -e "\n${MAGENTA}═══ DATABASE STATUS ===${NC}"

if kubectl get statefulset postgres -n "$NAMESPACE" &>/dev/null; then
    PG_READY=$(kubectl get statefulset postgres -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}' 2>/dev/null)
    PG_DESIRED=$(kubectl get statefulset postgres -n "$NAMESPACE" -o jsonpath='{.status.replicas}' 2>/dev/null)
    
    if [ "$PG_READY" == "$PG_DESIRED" ] && [ ! -z "$PG_READY" ]; then
        log_check "PASS" "PostgreSQL Replicas" "$PG_READY/$PG_DESIRED ready"
        
        if kubectl exec -n "$NAMESPACE" postgres-0 -- pg_isready -U postgres &>/dev/null; then
            log_check "PASS" "PostgreSQL Health" "Responding to connections"
        else
            log_check "FAIL" "PostgreSQL Health" "Not responding"
            add_recommendation "CRITICAL" "Fix PostgreSQL" "Database is not accepting connections" "kubectl logs -n $NAMESPACE postgres-0 | tail -30"
        fi
    else
        log_check "FAIL" "PostgreSQL Replicas" "$PG_READY/$PG_DESIRED"
        add_recommendation "CRITICAL" "Start PostgreSQL" "Database is not running" "kubectl apply -f k8s/04-postgres.yaml && kubectl wait --for=condition=ready pod postgres-0 -n $NAMESPACE --timeout=300s"
    fi
else
    log_check "FAIL" "PostgreSQL" "Not deployed"
    add_recommendation "CRITICAL" "Deploy PostgreSQL" "Database is required" "kubectl apply -f k8s/04-postgres.yaml"
fi

# ============ CACHE ============
echo -e "\n${MAGENTA}═══ CACHE STATUS ===${NC}"

if kubectl get statefulset redis -n "$NAMESPACE" &>/dev/null; then
    REDIS_READY=$(kubectl get statefulset redis -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}' 2>/dev/null)
    REDIS_DESIRED=$(kubectl get statefulset redis -n "$NAMESPACE" -o jsonpath='{.status.replicas}' 2>/dev/null)
    
    if [ "$REDIS_READY" == "$REDIS_DESIRED" ] && [ ! -z "$REDIS_READY" ]; then
        log_check "PASS" "Redis Replicas" "$REDIS_READY/$REDIS_DESIRED ready"
        
        if kubectl exec -n "$NAMESPACE" redis-0 -- redis-cli ping &>/dev/null; then
            log_check "PASS" "Redis Health" "Responding to pings"
            
            REDIS_MEM=$(kubectl exec -n "$NAMESPACE" redis-0 -- redis-cli info memory 2>/dev/null | grep used_memory_human | cut -d: -f2 | tr -d '\r')
            log_check "INFO" "Redis Memory Usage" "$REDIS_MEM"
        else
            log_check "FAIL" "Redis Health" "Not responding"
            add_recommendation "HIGH" "Fix Redis" "Cache is not responding" "kubectl logs -n $NAMESPACE redis-0"
        fi
    else
        log_check "WARN" "Redis Replicas" "$REDIS_READY/$REDIS_DESIRED"
        add_recommendation "HIGH" "Start Redis" "Cache is not running" "kubectl apply -f k8s/05-redis.yaml"
    fi
else
    log_check "FAIL" "Redis" "Not deployed"
    add_recommendation "HIGH" "Deploy Redis" "Cache layer is required" "kubectl apply -f k8s/05-redis.yaml"
fi

# ============ APPLICATION ============
echo -e "\n${MAGENTA}═══ APPLICATION STATUS ===${NC}"

CORE_READY=$(kubectl get deployment hypercode-core -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
CORE_DESIRED=$(kubectl get deployment hypercode-core -n "$NAMESPACE" -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "0")

if [ "$CORE_READY" == "$CORE_DESIRED" ] && [ "$CORE_READY" -gt 0 ]; then
    log_check "PASS" "HyperCode Core" "$CORE_READY/$CORE_DESIRED replicas running"
else
    log_check "WARN" "HyperCode Core" "$CORE_READY/$CORE_DESIRED replicas"
    add_recommendation "HIGH" "Start HyperCode Core" "Application is not fully running" "kubectl apply -f k8s/06-hypercode-core.yaml && kubectl wait --for=condition=ready deployment hypercode-core -n $NAMESPACE --timeout=300s"
fi

DASH_READY=$(kubectl get deployment dashboard -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
DASH_DESIRED=$(kubectl get deployment dashboard -n "$NAMESPACE" -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "0")

if [ "$DASH_READY" == "$DASH_DESIRED" ] && [ "$DASH_READY" -gt 0 ]; then
    log_check "PASS" "Dashboard" "$DASH_READY/$DASH_DESIRED replicas"
else
    log_check "WARN" "Dashboard" "$DASH_READY/$DASH_DESIRED replicas"
fi

# ============ OBSERVABILITY ============
echo -e "\n${MAGENTA}═══ OBSERVABILITY STACK ===${NC}"

for app in prometheus grafana loki tempo; do
    APP_READY=$(kubectl get deployment "$app" -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
    if [ "$APP_READY" -gt 0 ]; then
        log_check "PASS" "$(echo $app | capitalize)" "$APP_READY running"
    else
        log_check "WARN" "$(echo $app | capitalize)" "Not running"
    fi
done

# ============ NETWORKING ============
echo -e "\n${MAGENTA}═══ NETWORKING & INGRESS ===${NC}"

SVC_COUNT=$(kubectl get svc -n "$NAMESPACE" --no-headers 2>/dev/null | grep -v "kubernetes" | wc -l)
log_check "PASS" "Services" "$SVC_COUNT services"

# Check for services without endpoints
ORPHAN_SERVICES=$(kubectl get svc -n "$NAMESPACE" -o json 2>/dev/null | jq -r '.items[] | select(.spec.selector != null and (.spec.type != "ExternalName")) | select(.status.loadBalancer.ingress[0] == null and .spec.clusterIP != "None") as $svc | if $svc.status.endpoints == null or $svc.status.endpoints.subsets == null then $svc.metadata.name else empty end' | wc -l)

if [ "$ORPHAN_SERVICES" -gt 0 ]; then
    log_check "WARN" "Service Endpoints" "$ORPHAN_SERVICES services without endpoints"
    add_recommendation "MEDIUM" "Fix service endpoints" "Some services have no running pods" "kubectl get endpoints -n $NAMESPACE"
else
    log_check "PASS" "Service Endpoints" "All services have endpoints"
fi

# Check ingress
INGRESS_COUNT=$(kubectl get ingress -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
if [ "$INGRESS_COUNT" -gt 0 ]; then
    log_check "PASS" "Ingress" "$INGRESS_COUNT ingress rules"
    
    INGRESS_IP=$(kubectl get ingress -n "$NAMESPACE" -o jsonpath='{.items[0].status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")
    if [ "$INGRESS_IP" != "pending" ] && [ ! -z "$INGRESS_IP" ]; then
        log_check "PASS" "Ingress IP" "$INGRESS_IP assigned"
    else
        log_check "WARN" "Ingress IP" "IP not yet assigned (may be pending)"
        add_recommendation "MEDIUM" "Assign ingress IP" "LoadBalancer IP is still pending" "kubectl get ingress -n $NAMESPACE --watch"
    fi
else
    log_check "WARN" "Ingress" "No ingress configured"
    add_recommendation "MEDIUM" "Configure ingress" "No external access configured" "kubectl apply -f k8s/11-ingress-network-policy.yaml"
fi

# ============ POD STATUS ============
echo -e "\n${MAGENTA}═══ POD STATUS ===${NC}"

TOTAL_PODS=$(kubectl get pods -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
RUNNING_PODS=$(kubectl get pods -n "$NAMESPACE" -o jsonpath='{.items[?(@.status.phase=="Running")]}' | wc -w)
PENDING_PODS=$(kubectl get pods -n "$NAMESPACE" -o jsonpath='{.items[?(@.status.phase=="Pending")]}' | wc -w)
FAILED_PODS=$(kubectl get pods -n "$NAMESPACE" -o jsonpath='{.items[?(@.status.phase=="Failed")]}' | wc -w)

log_check "PASS" "Total Pods" "$TOTAL_PODS"
log_check "PASS" "Running Pods" "$RUNNING_PODS/$TOTAL_PODS"

if [ "$PENDING_PODS" -gt 0 ]; then
    log_check "WARN" "Pending Pods" "$PENDING_PODS pending"
    add_recommendation "MEDIUM" "Investigate pending pods" "Some pods are waiting to start" "kubectl describe pod -n $NAMESPACE | grep -A 10 'Conditions:'"
fi

if [ "$FAILED_PODS" -gt 0 ]; then
    log_check "FAIL" "Failed Pods" "$FAILED_PODS failed"
    add_recommendation "HIGH" "Fix failed pods" "Some pods have failed" "kubectl logs -n $NAMESPACE <pod-name>"
fi

# ============ RESOURCE USAGE ============
echo -e "\n${MAGENTA}═══ RESOURCE USAGE ===${NC}"

if kubectl top nodes &>/dev/null; then
    NODE_CPU=$(kubectl top nodes --no-headers 2>/dev/null | awk '{sum+=$2} END {print sum}')
    NODE_MEM=$(kubectl top nodes --no-headers 2>/dev/null | awk '{sum+=$4} END {print sum}')
    
    log_check "INFO" "Total Node CPU Usage" "${NODE_CPU}m"
    log_check "INFO" "Total Node Memory Usage" "${NODE_MEM}Mi"
    
    TOP_CPU_POD=$(kubectl top pods -n "$NAMESPACE" --sort-by=cpu --no-headers 2>/dev/null | head -1 | awk '{print $1, $2}')
    TOP_MEM_POD=$(kubectl top pods -n "$NAMESPACE" --sort-by=memory --no-headers 2>/dev/null | head -1 | awk '{print $1, $2}')
    
    log_check "INFO" "Top CPU Pod" "$TOP_CPU_POD"
    log_check "INFO" "Top Memory Pod" "$TOP_MEM_POD"
else
    log_check "WARN" "Metrics" "Metrics server not installed"
    add_recommendation "MEDIUM" "Install metrics-server" "Pod metrics are unavailable" "kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml"
fi

# ============ HA & AUTO-SCALING ============
echo -e "\n${MAGENTA}═══ HIGH AVAILABILITY & AUTO-SCALING ==={{NC}"

HPA_COUNT=$(kubectl get hpa -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
if [ "$HPA_COUNT" -gt 0 ]; then
    log_check "PASS" "HPA Configured" "$HPA_COUNT HPA policies"
else
    log_check "WARN" "HPA Configured" "No auto-scaling policies"
    add_recommendation "MEDIUM" "Configure HPA" "Auto-scaling is not configured" "kubectl apply -f k8s/11-ingress-network-policy.yaml"
fi

PDB_COUNT=$(kubectl get pdb -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
if [ "$PDB_COUNT" -gt 0 ]; then
    log_check "PASS" "PDB Configured" "$PDB_COUNT Pod Disruption Budgets"
else
    log_check "WARN" "PDB Configured" "No Pod Disruption Budgets"
    add_recommendation "MEDIUM" "Configure PDB" "Pod disruption budgets ensure availability during maintenance" "kubectl apply -f k8s/11-ingress-network-policy.yaml"
fi

# ============ NETWORK POLICIES ============
echo -e "\n${MAGENTA}═══ SECURITY & NETWORK POLICIES ==={{NC}"

NP_COUNT=$(kubectl get networkpolicy -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
if [ "$NP_COUNT" -gt 0 ]; then
    log_check "PASS" "Network Policies" "$NP_COUNT policies"
else
    log_check "WARN" "Network Policies" "No network policies"
    add_recommendation "MEDIUM" "Configure network policies" "Network policies restrict traffic between pods" "kubectl apply -f k8s/11-ingress-network-policy.yaml"
fi

# Check RBAC
ROLES=$(kubectl get roles -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
ROLEBINDINGS=$(kubectl get rolebindings -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)

if [ "$ROLES" -gt 0 ] || [ "$ROLEBINDINGS" -gt 0 ]; then
    log_check "PASS" "RBAC" "$ROLES roles, $ROLEBINDINGS bindings"
else
    log_check "WARN" "RBAC" "No RBAC rules configured"
    add_recommendation "LOW" "Configure RBAC" "Fine-grained access control is recommended" "kubectl create serviceaccount hypercode-sa -n $NAMESPACE"
fi

# ============ ALERTS & MONITORING ============
echo -e "\n${MAGENTA}═══ ALERTS & MONITORING ==={{NC}"

RULES=$(kubectl get PrometheusRule -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
if [ "$RULES" -gt 0 ]; then
    log_check "PASS" "Prometheus Rules" "$RULES alert rules"
else
    log_check "WARN" "Prometheus Rules" "No alert rules configured"
    add_recommendation "MEDIUM" "Configure alerts" "Monitoring rules are essential for production" "kubectl apply -f k8s/13-monitoring-alerts.yaml"
fi

# ============ RECENT EVENTS ============
echo -e "\n${MAGENTA}═══ RECENT EVENTS ==={{NC}"

ERROR_EVENTS=$(kubectl get events -n "$NAMESPACE" 2>/dev/null | grep -i "error\|warning" | wc -l)
if [ "$ERROR_EVENTS" -gt 0 ]; then
    log_check "WARN" "Error Events" "$ERROR_EVENTS errors/warnings in last hour"
    add_recommendation "MEDIUM" "Review events" "Recent errors detected in cluster" "kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp' | tail -20"
else
    log_check "PASS" "Recent Events" "No errors in last hour"
fi

# ============ CALCULATE HEALTH SCORE ============
echo -e "\n${MAGENTA}═══ HEALTH ASSESSMENT ==={{NC}"

if [ "$HEALTH_SCORE" -gt 90 ]; then
    HEALTH_STATUS="EXCELLENT"
    HEALTH_COLOR="$GREEN"
    STATUS_BADGE="status-healthy"
elif [ "$HEALTH_SCORE" -gt 70 ]; then
    HEALTH_STATUS="GOOD"
    HEALTH_COLOR="$YELLOW"
    STATUS_BADGE="status-warning"
elif [ "$HEALTH_SCORE" -gt 50 ]; then
    HEALTH_STATUS="WARNING"
    HEALTH_COLOR="$YELLOW"
    STATUS_BADGE="status-warning"
else
    HEALTH_STATUS="CRITICAL"
    HEALTH_COLOR="$RED"
    STATUS_BADGE="status-critical"
fi

echo -e "${HEALTH_COLOR}System Health Score: $HEALTH_SCORE/100 - $HEALTH_STATUS${NC}"
echo -e "${HEALTH_COLOR}Critical Issues: ${#CRITICAL_ISSUES[@]}${NC}"
echo -e "${HEALTH_COLOR}Warnings: ${#WARNINGS[@]}${NC}"
echo -e "${HEALTH_COLOR}Information Items: ${#INFO_ITEMS[@]}${NC}"

# ============ SUMMARY ============
echo -e "\n${MAGENTA}═══ SUMMARY OF CRITICAL ISSUES ==={{NC}"
if [ ${#CRITICAL_ISSUES[@]} -eq 0 ]; then
    echo -e "${GREEN}✓ No critical issues detected${NC}"
else
    for issue in "${CRITICAL_ISSUES[@]}"; do
        echo -e "${RED}✗ $issue${NC}"
    done
fi

echo -e "\n${MAGENTA}═══ PRIORITY RECOMMENDATIONS ==={{NC}"

# Sort and display recommendations by priority
declare -a CRIT_RECS
declare -a HIGH_RECS
declare -a MED_RECS
declare -a LOW_RECS

for rec in "${RECOMMENDATIONS[@]}"; do
    IFS='|' read -r priority title desc cmd <<< "$rec"
    case "$priority" in
        *CRITICAL*) CRIT_RECS+=("$rec") ;;
        *HIGH*) HIGH_RECS+=("$rec") ;;
        *MEDIUM*) MED_RECS+=("$rec") ;;
        *LOW*) LOW_RECS+=("$rec") ;;
    esac
done

rec_count=0
for priority in "CRITICAL" "HIGH" "MEDIUM" "LOW"; do
    case "$priority" in
        CRITICAL) recs=("${CRIT_RECS[@]}") color="$RED" ;;
        HIGH) recs=("${HIGH_RECS[@]}") color="$YELLOW" ;;
        MEDIUM) recs=("${MED_RECS[@]}") color="$CYAN" ;;
        LOW) recs=("${LOW_RECS[@]}") color="$GREEN" ;;
    esac
    
    for rec in "${recs[@]}"; do
        if [ $rec_count -lt 10 ]; then
            IFS='|' read -r p title desc cmd <<< "$rec"
            echo -e "${color}[$p] $title${NC}"
            echo -e "    Description: $desc"
            if [ ! -z "$cmd" ]; then
                echo -e "    ${CYAN}Command: $cmd${NC}"
            fi
            echo ""
            ((rec_count++))
        fi
    done
done

if [ ${#RECOMMENDATIONS[@]} -gt 10 ]; then
    echo -e "${YELLOW}... and $((${#RECOMMENDATIONS[@]} - 10)) more recommendations${NC}"
fi

# Save JSON report
save_json_report() {
    cat > "$JSON_REPORT" << EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "namespace": "$NAMESPACE",
  "health_score": $HEALTH_SCORE,
  "health_status": "$HEALTH_STATUS",
  "cluster": {
    "nodes": $NODE_COUNT,
    "ready_nodes": $READY_NODES
  },
  "pods": {
    "total": $TOTAL_PODS,
    "running": $RUNNING_PODS,
    "pending": $PENDING_PODS,
    "failed": $FAILED_PODS
  },
  "services": $SVC_COUNT,
  "ingress": $INGRESS_COUNT,
  "storage": {
    "pvc_count": $PVC_COUNT,
    "storage_classes": $SC_COUNT
  },
  "critical_issues": ${#CRITICAL_ISSUES[@]},
  "warnings": ${#WARNINGS[@]},
  "recommendations": ${#RECOMMENDATIONS[@]}
}
EOF
}

save_json_report

echo -e "\n${BLUE}Reports generated:${NC}"
echo -e "  ${GREEN}✓${NC} HTML Report: $REPORT_FILE"
echo -e "  ${GREEN}✓${NC} JSON Report: $JSON_REPORT"
echo -e "\n${MAGENTA}═══════════════════════════════════════════════════════════${NC}\n"
