# ═══════════════════════════════════════════════
# ONE-TIME SECRETS INJECTION (local only, never committed)
# ═══════════════════════════════════════════════

kubectl create namespace hypercode-staging --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic hypercode-secrets `
  --namespace=hypercode-staging `
  --from-literal=PERPLEXITY-api-key="YOUR_PERPLEXITY_KEY_HERE" `
  --from-literal=hypercode-jwt-secret="YOUR_JWT_SECRET_HERE" `
  --from-literal=postgres-password="YOUR_DB_PASSWORD_HERE" `
  --from-literal=redis-password="YOUR_REDIS_PASSWORD_HERE" `
  --from-literal=grafana-admin-password="YOUR_GRAFANA_PASSWORD_HERE" `
  --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic api-keys `
  --namespace=hypercode-staging `
  --from-literal=xSK8d8hMR+NfoRHd/XgwxYB5Yop4e1zrAM7g3C8hTWY `
  --from-literal=memory-key=zmbJ1kN3bNL5HQ9+FCMyyBCxM0xT6Avab1TTQ3UsE2c" `
  --dry-run=client -o yaml | kubectl apply -f -
