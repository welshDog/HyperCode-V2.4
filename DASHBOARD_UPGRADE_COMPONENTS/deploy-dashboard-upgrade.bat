@echo off
REM deploy-dashboard-upgrade.bat
REM Deploy Dashboard v2.0 with all new components (Windows)

setlocal enabledelayedexpansion

echo.
echo ========================================
echo 🚀 Dashboard v2.0 Upgrade Deployment
echo ========================================
echo.

REM Check Docker is running
echo [1/8] Checking Docker...
docker ps >nul 2>&1
if errorlevel 1 (
    echo Docker is not running!
    exit /b 1
)
echo ✓ Docker is running
echo.

REM Stop existing dashboard
echo [2/8] Stopping existing dashboard...
docker compose down hypercode-dashboard 2>nul
timeout /t 2 /nobreak >nul

REM Remove old image
echo [3/8] Removing old dashboard image...
docker rmi hypercode-v24-dashboard:v2.0 2>nul

REM Build new image
echo [4/8] Building new dashboard image (v2.0)...
docker build ^
  -t hypercode-v24-dashboard:v2.0 ^
  -f DASHBOARD_UPGRADE_COMPONENTS/Dockerfile.dashboard-v2 ^
  .

if errorlevel 1 (
    echo Build failed!
    exit /b 1
)
echo ✓ Build successful
echo.

REM Start container
echo [5/8] Starting new dashboard container...
docker compose up -d hypercode-dashboard
if errorlevel 1 (
    echo Container startup failed!
    exit /b 1
)
timeout /t 3 /nobreak >nul
echo ✓ Container started
echo.

REM Check container is running
echo [6/8] Verifying container health...
for /f "tokens=1" %%A in ('docker ps ^| find "hypercode-dashboard"') do set CONTAINER_ID=%%A
if "!CONTAINER_ID!"=="" (
    echo Container not running!
    exit /b 1
)
echo ✓ Container running: !CONTAINER_ID!
echo.

REM Wait for app
echo [7/8] Waiting for app to be ready...
set READY=0
for /L %%i in (1,1,30) do (
    curl -s http://localhost:8088/ >nul 2>&1
    if not errorlevel 1 (
        set READY=1
        goto :ready
    )
    timeout /t 1 /nobreak >nul
)
:ready
if !READY! equ 1 (
    echo ✓ App is ready
) else (
    echo App did not start!
    exit /b 1
)
echo.

REM Test endpoints
echo [8/8] Testing endpoints...
curl -s http://localhost:8088/dashboard/ >nul 2>&1 && echo ✓ Dashboard loads
echo.

echo ========================================
echo ✓ Dashboard v2.0 Deployed Successfully!
echo ========================================
echo.
echo Access at: http://localhost:8088/dashboard
echo.
echo Features:
echo   ✓ Live Agent Monitor
echo   ✓ Code IDE
echo   ✓ Mission Timeline
echo   ✓ Docker Zone
echo   ✓ MCP Tool Browser
echo.
echo Container ID: !CONTAINER_ID!
echo Image: hypercode-v24-dashboard:v2.0
echo Port: 8088 - 3000
echo.
pause
