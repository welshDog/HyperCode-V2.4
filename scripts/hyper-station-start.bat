@echo off
REM =================================================================================
REM HYPER STATION - ALL SYSTEMS GO
REM Centralized Startup Script for HyperCode V2.0
REM =================================================================================

SETLOCAL EnableDelayedExpansion

REM --- Configuration ---
SET "PROJECT_ROOT=%~dp0.."
SET "DOCKER_COMPOSE_FILE=%PROJECT_ROOT%\docker-compose.yml"
SET "DASHBOARD_URL=http://localhost:8088"
SET "ORCHESTRATOR_URL=http://localhost:8081"
SET "MAX_RETRIES=30"
SET "RETRY_DELAY=2"

echo ---------------------------------------------------------------------------------
echo    HYPER STATION MISSION CONTROL - INITIALIZING
echo ---------------------------------------------------------------------------------
echo [INFO] Project Root: %PROJECT_ROOT%
echo [INFO] Docker Compose: %DOCKER_COMPOSE_FILE%

REM --- Step 1: Check Docker Availability ---
echo [STEP 1] Checking Docker Engine...
docker info >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Docker is not running. Please start Docker Desktop and try again.
    pause
    exit /b 1
)
echo [OK] Docker is online.

REM --- Step 2: Launch Core Infrastructure ---
echo [STEP 2] Igniting Core Services (This may take a moment)...
docker compose -f "%DOCKER_COMPOSE_FILE%" up -d --remove-orphans
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to start containers. Check Docker logs.
    pause
    exit /b 1
)
echo [OK] Containers dispatched.

REM --- Step 3: Health Verification Loop ---
echo [STEP 3] Verifying System Vitals...

SET "CORE_HEALTHY=0"
SET "DASHBOARD_HEALTHY=0"

FOR /L %%i IN (1,1,%MAX_RETRIES%) DO (
    REM Check Orchestrator
    curl -s -f %ORCHESTRATOR_URL%/health >nul 2>&1
    IF !ERRORLEVEL! EQU 0 (
        SET "CORE_HEALTHY=1"
        echo [OK] Orchestrator is pulse-positive.
    ) ELSE (
        echo [WAIT] Waiting for Orchestrator... (Attempt %%i/%MAX_RETRIES%)
    )

    REM Check Dashboard
    curl -s -f %DASHBOARD_URL% >nul 2>&1
    IF !ERRORLEVEL! EQU 0 (
        SET "DASHBOARD_HEALTHY=1"
        echo [OK] Dashboard is visual-positive.
    ) ELSE (
        echo [WAIT] Waiting for Dashboard... (Attempt %%i/%MAX_RETRIES%)
    )

    IF "!CORE_HEALTHY!"=="1" IF "!DASHBOARD_HEALTHY!"=="1" GOTO :LAUNCH_UI

    timeout /t %RETRY_DELAY% /nobreak >nul
)

echo [WARNING] Startup timed out. Services might still be initializing.
echo [WARNING] Proceeding to launch UI anyway...

:LAUNCH_UI
REM --- Step 4: Launch Interfaces ---
echo [STEP 4] Engaging Interfaces...

REM Open Default Browser to Dashboard
start "" "%DASHBOARD_URL%"

REM Open Windows Terminal (if available) with useful tabs
echo [DEBUG] Checking for Windows Terminal...
where wt >nul 2>&1
IF %ERRORLEVEL% NEQ 0 GOTO :NO_WT

:HAS_WT
echo [INFO] Opening Hyper Station Terminal Matrix...
start wt -w 0 -d "%PROJECT_ROOT%" ; split-pane -V -d "%PROJECT_ROOT%" cmd /k "docker logs -f healer-agent" ; split-pane -H -d "%PROJECT_ROOT%" cmd /k "docker logs -f crew-orchestrator"
GOTO :END_LAUNCH

:NO_WT
echo [INFO] Windows Terminal (wt.exe) not found. Opening standard console.
start "HyperStation Console" cmd /k "cd /d "%PROJECT_ROOT%""

:END_LAUNCH
echo ---------------------------------------------------------------------------------
echo    MISSION CONTROL ACTIVE - ALL SYSTEMS GO
echo ---------------------------------------------------------------------------------
timeout /t 5
