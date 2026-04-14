#!/usr/bin/env bash
# 🗝️ Phase 10C — HyperCode Secrets Initialiser
# Generates all secret files safely using openssl rand
# Run ONCE on fresh setup, or when rotating secrets
# Usage: bash scripts/secrets-init.sh
#        bash scripts/secrets-init.sh --rotate   (force regenerate all)

set -euo pipefail

SECRETS_DIR="$(dirname "$(realpath "$0")")"
SECRETS_DIR="$(realpath "$SECRETS_DIR/../secrets")"
ROTATE=${1:-""}

echo "🗝️  HyperCode Secrets Init"
echo "   Secrets dir: $SECRETS_DIR"
mkdir -p "$SECRETS_DIR"
chmod 700 "$SECRETS_DIR"

create_secret() {
  local name="$1"
  local value="$2"
  local path="$SECRETS_DIR/${name}.txt"

  if [[ -f "$path" && "$ROTATE" != "--rotate" ]]; then
    echo "  ⏭️  $name — already exists (use --rotate to overwrite)"
    return
  fi

  echo -n "$value" > "$path"
  chmod 600 "$path"
  echo "  ✅  $name — written"
}

echo ""
echo "🔐 Generating secrets..."
echo ""

# ── Database ────────────────────────────────────────────────────────────────
create_secret "postgres_password"      "$(openssl rand -base64 32)"

# ── Core API ────────────────────────────────────────────────────────────────
create_secret "api_key"                "hc_$(openssl rand -hex 32)"
create_secret "jwt_secret"             "$(openssl rand -base64 48)"
create_secret "memory_key"             "$(openssl rand -base64 32)"

# ── Orchestration ───────────────────────────────────────────────────────────
create_secret "orchestrator_api_key"   "hc_$(openssl rand -hex 32)"

# ── Observability ───────────────────────────────────────────────────────────
create_secret "grafana_admin_password" "$(openssl rand -base64 24)"

# ── Object Storage ──────────────────────────────────────────────────────────
create_secret "minio_root_user"        "hyperminio"
create_secret "minio_root_password"    "$(openssl rand -base64 24)"

# ── External APIs (placeholders — paste real keys) ──────────────────────────
create_secret "discord_token"          "PASTE_YOUR_DISCORD_TOKEN_HERE"
create_secret "openai_api_key"         "PASTE_YOUR_OPENAI_KEY_HERE"
create_secret "perplexity_api_key"     "PASTE_YOUR_PERPLEXITY_KEY_HERE"

echo ""
echo "⚠️  ACTION REQUIRED — paste real API keys into:"
echo "   $SECRETS_DIR/discord_token.txt"
echo "   $SECRETS_DIR/openai_api_key.txt"
echo "   $SECRETS_DIR/perplexity_api_key.txt"
echo ""
echo "🔒 Permissions set to 600 on all files (owner read/write only)"
echo "✅ Done! To apply:"
echo "   docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d"
echo ""
echo "📋 To rotate all secrets:"
echo "   bash scripts/secrets-init.sh --rotate"
