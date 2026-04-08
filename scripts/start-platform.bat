@echo off
setlocal enabledelayedexpansion
cd /d %~dp0\..
echo Starting HyperCode Platform (Core + Crew + Monitoring)
docker compose -f docker-compose.yml up -d --build
echo Services starting. Grafana: http://localhost:3000, Core: http://localhost:8000, Crew: http://localhost:8080
endlocal
