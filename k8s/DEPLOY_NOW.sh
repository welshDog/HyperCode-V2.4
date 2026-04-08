#!/bin/bash
# 🚀 HyperCode V2.0 - GO LIVE IN 1 HOUR (Tactical Deployment)
# Everything you need to get from zero to production Kubernetes

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  🚀 HyperCode V2.0 - PRODUCTION DEPLOYMENT TOOLKIT        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================================
# STEP 1: LOCAL CLUSTER (Choose one)
# ============================================================================
setup_minikube() {
    echo -e "${YELLOW}[1/5] Setting up Minikube cluster...${NC}"
    
    if ! command -v minikube &> /dev/null; then
        echo -e "${RED}❌ Minikube not installed. Install from:${NC}"
        echo "   https://minikube.sigs.k8s.io/docs/start/"
        exit 1
    fi
    
    echo "Starting Minikube with 8GB RAM, 4 CPUs..."
    minikube start \
        --cpus=4 \
        --memory=8096 \
        --disk-size=50g \
        --vm-driver=docker \
        --wait=all \
        2>&1 | grep -E "Done|Starting|Ready" || true
    
    echo -e "${GREEN}✅ Minikube running${NC}"
    minikube status
}

# ============================================================================
# STEP 2: VERIFY CLUSTER
# ============================================================================
verify_cluster() {
    echo ""
    echo -e "${YELLOW}[2/5] Verifying Kubernetes cluster...${NC}"
    
    if ! kubectl cluster-info &>/dev/null; then
        echo -e "${RED}❌ Cannot connect to Kubernetes cluster${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Cluster connectivity verified${NC}"
    
    # Check version
    VERSION=$(kubectl version --short | grep Server | awk '{print $3}')
    echo "   Kubernetes Version: $VERSION"
    
    # Check nodes
    NODES=$(kubectl get nodes --no-headers | wc -l)
    echo "   Nodes: $NODES"
    
    # Check storage class
    STORAGE=$(kubectl get storageclass --no-headers 2>/dev/null | wc -l)
    echo "   Storage Classes: $STORAGE"
    
    if [ "$STORAGE" -eq 0 ]; then
        echo -e "${YELLOW}⚠️  No default storage class. Creating...${NC}"
        kubectl apply -f - <<EOF
kind: StorageClass
apiVersion: storage.k8s.io/v1
metadata:
  name: standard
  namespace: kube-system
provisioner: kubernetes.io/no-provisioner
volumeBindingMode: Immediate
EOF
    fi
}

# ============================================================================
# STEP 3: UPDATE SECRETS
# ============================================================================
update_secrets() {
    echo ""
    echo -e "${YELLOW}[3/5] Securing secrets...${NC}"
    
    SECRETS_FILE="./k8s/02-secrets.yaml"
    
    if [ ! -f "$SECRETS_FILE" ]; then
        echo -e "${RED}❌ Secrets file not found: $SECRETS_FILE${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}⚠️  IMPORTANT: Update these in $SECRETS_FILE:${NC}"
    echo "   - POSTGRES_PASSWORD: Use a strong password"
    echo "   - HYPERCODE_JWT_SECRET: Use a 32+ character secret"
    echo "   - MINIO_ROOT_PASSWORD: Use a strong password"
    echo "   - API_KEY: Use a unique key"
    echo "   - PERPLEXITY_API_KEY: Add your actual key"
    echo ""
    
    read -p "Press ENTER after updating secrets, or type 'skip' to continue: " -r
    if [ "$REPLY" != "skip" ]; then
        nano "$SECRETS_FILE" 2>/dev/null || vi "$SECRETS_FILE"
    fi
    
    echo -e "${GREEN}✅ Secrets configured${NC}"
}

# ============================================================================
# STEP 4: DEPLOY EVERYTHING
# ============================================================================
deploy_hypercode() {
    echo ""
    echo -e "${YELLOW}[4/5] Deploying HyperCode...${NC}"
    
    DEPLOY_SCRIPT="./k8s/deploy.sh"
    
    if [ ! -f "$DEPLOY_SCRIPT" ]; then
        echo -e "${RED}❌ Deploy script not found: $DEPLOY_SCRIPT${NC}"
        exit 1
    fi
    
    chmod +x "$DEPLOY_SCRIPT"
    echo "Running automated deployment..."
    
    # Run deployment with live output
    "$DEPLOY_SCRIPT" 2>&1 | tee deployment.log
}

# ============================================================================
# STEP 5: VERIFY & REPORT
# ============================================================================
final_checks() {
    echo ""
    echo -e "${YELLOW}[5/5] Final verification...${NC}"
    
    echo -e "${BLUE}Checking pod status:${NC}"
    kubectl get pods -n hypercode -o wide
    
    echo ""
    echo -e "${BLUE}Checking service status:${NC}"
    kubectl get svc -n hypercode -o wide
    
    echo ""
    echo -e "${GREEN}✅ DEPLOYMENT COMPLETE!${NC}"
    echo ""
    echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}Next: Access your services via port-forward:${NC}"
    echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${GREEN}Dashboard (Frontend):${NC}"
    echo "  kubectl port-forward -n hypercode svc/dashboard 3000:3000"
    echo "  → http://localhost:3000"
    echo ""
    echo -e "${GREEN}API Documentation:${NC}"
    echo "  kubectl port-forward -n hypercode svc/hypercode-core 8000:8000"
    echo "  → http://localhost:8000/docs"
    echo ""
    echo -e "${GREEN}Grafana Monitoring:${NC}"
    echo "  kubectl port-forward -n hypercode svc/grafana 3001:3000"
    echo "  → http://localhost:3001"
    echo "  Username: admin"
    echo "  Password: password"
    echo ""
    echo -e "${GREEN}Prometheus Metrics:${NC}"
    echo "  kubectl port-forward -n hypercode svc/prometheus 9090:9090"
    echo "  → http://localhost:9090"
    echo ""
    echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"
}

# ============================================================================
# MAIN FLOW
# ============================================================================
main() {
    echo -e "${BLUE}Starting tactical deployment...${NC}"
    echo ""
    
    # Check we're in right directory
    if [ ! -d "k8s" ]; then
        echo -e "${RED}❌ Must run from HyperCode-V2.0 root directory${NC}"
        exit 1
    fi
    
    cd k8s
    
    # Execute steps
    setup_minikube
    verify_cluster
    update_secrets
    deploy_hypercode
    final_checks
    
    echo ""
    echo -e "${GREEN}🎉 You're live! Welcome to production Kubernetes! 🚀${NC}"
}

# Run
main "$@"
