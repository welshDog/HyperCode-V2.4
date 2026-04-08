#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo "Starting HyperCode Platform (Core + Crew + Monitoring)"
docker compose -f docker-compose.yml up -d --build
echo "Services starting. Grafana: http://localhost:3000, Core: http://localhost:8000, Crew: http://localhost:8080"
