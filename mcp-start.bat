@echo off
REM ============================================================================
REM MCP Gateway + Model Runner Quick Launcher (Windows)
REM ============================================================================
REM Usage:
REM   mcp-start.bat          - Start MCP profile
REM   mcp-start.bat check    - Health check
REM   mcp-start.bat stop     - Stop MCP services
REM ============================================================================

setlocal enabledelayedexpansion

set ACTION=%1
if "!ACTION!"=="" set ACTION=start

if "!ACTION!"=="start" (
    echo 🚀 Starting MCP Gateway + Model Runner Profile...
    docker compose -f docker-compose.yml -f docker-compose.mcp-gateway.yml up -d
    echo.
    echo ✅ Profile started. Waiting for health checks...
    timeout /t 30 /nobreak
    echo.
    echo 📋 Services should be running:
    echo    • MCP Gateway:     http://localhost:8820
    echo    • Model Runner:    http://localhost:11434
    echo    • GitHub Tool:     http://localhost:3001
    echo    • Postgres Tool:   http://localhost:3002
    echo    • FileSystem Tool: http://localhost:3003
    echo    • VectorDB Tool:   http://localhost:3004
    echo.
    echo Run: mcp-start.bat check
    goto end
)

if "!ACTION!"=="stop" (
    echo 🛑 Stopping MCP Gateway + Model Runner...
    docker compose -f docker-compose.mcp-gateway.yml down
    echo ✅ Stopped
    goto end
)

if "!ACTION!"=="check" (
    echo 🔍 Health Check:
    echo.
    
    setlocal enabledelayedexpansion
    
    for %%s in (
        "mcp-gateway:8820"
        "model-runner:11434"
        "mcp-github:3001"
        "mcp-postgres:3002"
        "mcp-filesystem:3003"
        "mcp-vectordb:3004"
    ) do (
        for /f "tokens=1,2 delims=:" %%a in ("%%s") do (
            set name=%%a
            set port=%%b
            
            powershell -Command "try { $null = [System.Net.HttpClient]::new().GetAsync('http://localhost:!port!/health').Result; Write-Host '   ✅ !name!' } catch { Write-Host '   ❌ !name! (not responding)' }" 2>nul
        )
    )
    echo.
    echo Run: mcp-start.bat verify
    goto end
)

if "!ACTION!"=="verify" (
    echo 🧪 Verifying MCP Setup...
    python scripts/verify_mcp_setup.py
    goto end
)

if "!ACTION!"=="logs" (
    echo 📜 Tailing MCP Gateway logs...
    docker compose -f docker-compose.mcp-gateway.yml logs -f mcp-gateway
    goto end
)

echo Usage: mcp-start.bat {start^|stop^|check^|verify^|logs}
echo.
echo Examples:
echo   mcp-start.bat start              - Start MCP profile
echo   mcp-start.bat check              - Health check
echo   mcp-start.bat verify             - Full verification suite
echo   mcp-start.bat logs               - View gateway logs
echo   mcp-start.bat stop               - Stop MCP services

:end
endlocal
