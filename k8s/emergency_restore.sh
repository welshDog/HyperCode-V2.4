#!/bin/bash
echo "🔥 HyperCode Emergency Restore Protocol Initiated..."

# 1. Apply Storage & Secrets (Base)
echo "1. Applying Storage & Secrets..."
kubectl apply -f k8s/01-configmaps.yaml
kubectl apply -f k8s/02-configmap.yaml
kubectl apply -f k8s/02-secrets.yaml
kubectl apply -f k8s/03-pvcs.yaml

# 2. Apply Core Services (DB, Redis, Core)
echo "2. Applying Core Services..."
kubectl apply -f k8s/04-postgres.yaml
kubectl apply -f k8s/04-redis.yaml
kubectl apply -f k8s/05-postgres.yaml
kubectl apply -f k8s/05-redis.yaml
kubectl apply -f k8s/06-hypercode-core.yaml

# 3. Apply Orchestrator & Agents
echo "3. Applying Orchestrator & Agents..."
kubectl apply -f k8s/07-crew-orchestrator.yaml
kubectl apply -f k8s/08-agents.yaml --validate=false

# 4. Apply UI & Bots
echo "4. Applying UI & Bots..."
kubectl apply -f k8s/09-dashboard.yaml
kubectl apply -f k8s/12-broski-bot.yaml --validate=false

# 5. Force Restart Pods
echo "5. Restarting all pods to pick up changes..."
kubectl delete pods --all -n hypercode --grace-period=0 --force

echo "✅ Restore Sequence Complete. Monitor status with: kubectl get pods -n hypercode -w"
