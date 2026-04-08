@echo off
REM =================================================================================
REM HYPER STATION - SHUTDOWN
REM Centralized Shutdown Script for HyperCode V2.0
REM =================================================================================

SET "PROJECT_ROOT=%~dp0.."
SET "DOCKER_COMPOSE_FILE=%PROJECT_ROOT%\docker-compose.yml"

echo ---------------------------------------------------------------------------------
echo    HYPER STATION MISSION CONTROL - SHUTTING DOWN
echo ---------------------------------------------------------------------------------
echo [INFO] Project Root: %PROJECT_ROOT%

REM --- Step 1: Check Docker Availability ---
docker info >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Docker is not running.
    pause
    exit /b 1
)

REM --- Step 2: Stop Services ---
echo [STEP 2] Stopping Containers (this may take a moment)...
docker compose -f "%DOCKER_COMPOSE_FILE%" down

IF %ERRORLEVEL% EQU 0 (
    echo [OK] All systems safely terminated.
    echo ---------------------------------------------------------------------------------
    echo    MISSION COMPLETE
    echo ---------------------------------------------------------------------------------
) ELSE (
    echo [ERROR] Failed to stop containers. Check Docker logs.
    pause
)

timeout /t 3
