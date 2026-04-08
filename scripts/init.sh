#!/usr/bin/env bash
# scripts/init.sh — HyperCode V2.0 First-Run Setup (bash / WSL / Linux / macOS)
# Usage: bash scripts/init.sh
# Idempotent: safe to re-run at any time.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PASS=0; WARN=0; FAIL=0

pass() { echo "  [PASS] $1"; PASS=$((PASS+1)); }
warn() { echo "  [WARN] $1"; WARN=$((WARN+1)); }
fail() { echo "  [FAIL] $1"; FAIL=$((FAIL+1)); }

echo ""
echo "========================================"
echo "  HyperCode V2.0 — First-Run Init"
echo "========================================"
echo ""

# ── 1. Docker availability ──────────────────────────────────────────────────
echo "[ 1 ] Docker"
if docker info > /dev/null 2>&1; then
    pass "Docker is running"
else
    fail "Docker is not running — start Docker Desktop (or Docker daemon) and retry"
    exit 1
fi

# ── 2. Create required Docker networks ─────────────────────────────────────
echo "[ 2 ] Docker Networks"

create_network() {
    local name="$1" label="$2"
    if docker network ls --format '{{.Name}}' | grep -q "^${name}$"; then
        pass "${label} already exists (${name})"
    else
        docker network create "$name" > /dev/null
        pass "${label} created (${name})"
    fi
}

create_network "hypercode_public_net"   "backend-net (external)"
create_network "hypercode_frontend_net" "frontend-net"

# ── 3. Validate .env ────────────────────────────────────────────────────────
echo "[ 3 ] Environment File"

ENV_FILE="$PROJECT_ROOT/.env"
ENV_EXAMPLE="$PROJECT_ROOT/.env.example"

if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$ENV_EXAMPLE" ]; then
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        warn ".env not found — copied from .env.example. Edit it before starting."
    else
        fail ".env and .env.example both missing — cannot continue"
        exit 1
    fi
else
    pass ".env file exists"
fi

# Parse .env (ignores comments, handles quoted values)
parse_env() {
    grep -E '^\s*[^#[:space:]]+=.' "$ENV_FILE" \
        | sed -e 's/^[[:space:]]*//' -e "s/['\"]//g" \
        | while IFS='=' read -r key rest; do
            echo "${key}=${rest}"
        done
}

get_env() {
    parse_env | grep "^${1}=" | head -1 | cut -d= -f2-
}

HC_DATA_ROOT_VAL="$(get_env HC_DATA_ROOT)"
if [ -z "$HC_DATA_ROOT_VAL" ] || echo "$HC_DATA_ROOT_VAL" | grep -q "absolute/path"; then
    fail "HC_DATA_ROOT is not set in .env — edit .env with a real path"
else
    pass "HC_DATA_ROOT = $HC_DATA_ROOT_VAL"
fi

for key in POSTGRES_PASSWORD API_KEY HYPERCODE_JWT_SECRET; do
    val="$(get_env "$key")"
    if [ -z "$val" ] || echo "$val" | grep -qE "^(changeme|your_)"; then
        warn "$key is not set or still has placeholder value"
    else
        pass "$key is set"
    fi
done

# ── 4. Create data directories ───────────────────────────────────────────────
echo "[ 4 ] Data Directories"

if [ -n "$HC_DATA_ROOT_VAL" ] && ! echo "$HC_DATA_ROOT_VAL" | grep -q "absolute/path"; then
    # Normalise: on WSL, convert Windows path H:/Foo to /mnt/h/Foo
    DATA_ROOT="$HC_DATA_ROOT_VAL"
    if echo "$DATA_ROOT" | grep -qE '^[A-Za-z]:'; then
        DRIVE_LETTER=$(echo "$DATA_ROOT" | cut -c1 | tr '[:upper:]' '[:lower:]')
        REST=$(echo "$DATA_ROOT" | cut -c3-)
        DATA_ROOT="/mnt/${DRIVE_LETTER}${REST}"
    fi
    DATA_ROOT="${DATA_ROOT//\\//}"  # backslash → forward slash

    for sub in redis postgres grafana prometheus ollama agent_memory minio chroma tempo; do
        dir="${DATA_ROOT}/${sub}"
        if [ -d "$dir" ]; then
            pass "Exists:  $dir"
        else
            mkdir -p "$dir"
            pass "Created: $dir"
        fi
    done
else
    warn "Skipping data directory creation — HC_DATA_ROOT not configured"
fi

# ── 5. Summary ───────────────────────────────────────────────────────────────
echo ""
echo "========================================"
echo "  Init Summary"
echo "========================================"
if [ "$FAIL" -gt 0 ]; then
    echo "  $FAIL issue(s) must be fixed before starting."
    echo "  Run 'make start' after resolving them."
    exit 1
elif [ "$WARN" -gt 0 ]; then
    echo "  Init complete with $WARN warning(s)."
    echo "  Run 'make start' to launch HyperCode V2.0."
else
    echo "  All checks passed. Run 'make start' to launch!"
fi
echo ""
