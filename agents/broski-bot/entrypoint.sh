#!/bin/bash
set -e

# Load secret from file if mounted at /run/secrets/<name>, else keep existing env.
# Fails loudly if the resolved value is empty.
load_secret() {
  local env_var="$1"
  local secret_file="/run/secrets/$2"
  local required="${3:-true}"

  if [ -f "$secret_file" ]; then
    local value
    value="$(cat "$secret_file")"
    if [ -n "$value" ]; then
      export "$env_var"="$value"
    fi
  fi

  if [ "$required" = "true" ] && [ -z "${!env_var}" ]; then
    echo "❌ FATAL: $env_var is empty (tried secret file $secret_file and env)" >&2
    exit 1
  fi
}

load_secret POSTGRES_PASSWORD postgres_password true
load_secret DISCORD_TOKEN     discord_token     true
load_secret PERPLEXITY_API_KEY perplexity_api_key false
load_secret OPENAI_API_KEY    openai_api_key    false

# Mirror POSTGRES_PASSWORD into DB_PASSWORD
export DB_PASSWORD="${POSTGRES_PASSWORD}"

export DB_HOST="${DB_HOST:-postgres}"
export DB_PORT="${DB_PORT:-5432}"
export DB_NAME="${DB_NAME:-broski}"
export DB_USER="${DB_USER:-postgres}"

export REDIS_URL="${REDIS_URL:-redis://redis:6379/0}"

exec python /app/src/main.py run
