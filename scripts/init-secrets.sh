#!/usr/bin/env bash
# scripts/init-secrets.sh — Create Docker secret files from .env values
# Run once before first `docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d`
#
# Reads .env (if present) for default values; prompts for any that are missing.

set -euo pipefail

SECRETS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/secrets"
ENV_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/.env"

# Load .env if present
if [[ -f "$ENV_FILE" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
fi

mkdir -p "$SECRETS_DIR"
chmod 700 "$SECRETS_DIR"

_write_secret() {
    local name="$1"
    local value="$2"
    local file="$SECRETS_DIR/${name}.txt"

    if [[ -f "$file" ]]; then
        echo "  [SKIP] $name already exists"
        return
    fi

    if [[ -z "$value" ]]; then
        echo "  [PROMPT] Enter value for $name:"
        read -rs value
        echo
    fi

    printf '%s' "$value" > "$file"
    chmod 600 "$file"
    echo "  [OK]   $name written to $file"
}

echo ""
echo "HyperCode V2.4 — Docker Secrets Initialisation"
echo "================================================"
echo "Secrets directory: $SECRETS_DIR"
echo ""

_write_secret "postgres_password"        "${POSTGRES_PASSWORD:-}"
_write_secret "api_key"                  "${API_KEY:-}"
_write_secret "jwt_secret"               "${JWT_SECRET:-${HYPERCODE_JWT_SECRET:-}}"
_write_secret "memory_key"               "${HYPERCODE_MEMORY_KEY:-}"
_write_secret "orchestrator_api_key"     "${ORCHESTRATOR_API_KEY:-}"
_write_secret "grafana_admin_password"   "${GF_SECURITY_ADMIN_PASSWORD:-}"
_write_secret "minio_root_user"          "${MINIO_ROOT_USER:-}"
_write_secret "minio_root_password"      "${MINIO_ROOT_PASSWORD:-}"
_write_secret "discord_token"            "${DISCORD_TOKEN:-}"
_write_secret "openai_api_key"           "${OPENAI_API_KEY:-}"
_write_secret "perplexity_api_key"       "${PERPLEXITY_API_KEY:-}"
_write_secret "anthropic_api_key"        "${ANTHROPIC_API_KEY:-}"

echo ""
echo "Done. Validate with:"
echo "  docker compose -f docker-compose.yml -f docker-compose.secrets.yml config --quiet"
echo ""
