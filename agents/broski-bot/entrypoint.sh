#!/bin/bash
set -e

# Load secrets from files
if [ -f "/run/secrets/postgres_password" ]; then
  export POSTGRES_PASSWORD=$(cat /run/secrets/postgres_password)
fi

if [ -f "/run/secrets/discord_token" ]; then
  export DISCORD_TOKEN=$(cat /run/secrets/discord_token)
fi

# Update DATABASE_URL with loaded password
export DATABASE_URL="postgresql+asyncpg://postgres:${POSTGRES_PASSWORD}@postgres:5432/broski"
export DB_PASSWORD="${POSTGRES_PASSWORD}"

# Execute the main command
exec python /app/src/main.py run
