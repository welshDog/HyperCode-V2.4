@echo off
REM HyperCode Agent Crew - Windows Quick Start Script

echo ===================================
echo HyperCode Agent Crew - Setup Script
echo ===================================

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Docker is not installed. Please install Docker Desktop first.
    exit /b 1
)

echo Docker is installed

REM Check if .env.agents exists
if not exist .env.agents (
    echo.
    echo Creating .env.agents file...
    copy .env.agents.example .env.agents
    echo.
    echo Please edit .env.agents and add your PERPLEXITY_API_KEY
    echo Then run this script again.
    exit /b 0
)

REM Check if API key is set
findstr /C:"your_PERPLEXITY_API_KEY_here" .env.agents >nul
if %errorlevel% equ 0 (
    echo.
    echo Please edit .env.agents and add your PERPLEXITY_API_KEY
    echo The file is located at: .env.agents
    exit /b 1
)

echo Environment configuration found

echo.
echo What would you like to do?
echo 1) Build and start all agents
echo 2) Start agents (without rebuild)
echo 3) Stop all agents
echo 4) View logs
echo 5) Check agent status
echo 6) Clean up (remove containers and volumes)
set /p choice="Enter choice [1-6]: "

if "%choice%"=="1" (
    echo.
    echo Building and starting all agents...
    docker-compose -f docker-compose.agents.yml --env-file .env.agents build
    docker-compose -f docker-compose.agents.yml --env-file .env.agents up -d
    echo.
    echo All agents are starting up!
    echo Orchestrator API: http://localhost:8080
    echo Dashboard: http://localhost:8090
) else if "%choice%"=="2" (
    echo.
    echo Starting agents...
    docker-compose -f docker-compose.agents.yml --env-file .env.agents up -d
    echo Agents started
) else if "%choice%"=="3" (
    echo.
    echo Stopping agents...
    docker-compose -f docker-compose.agents.yml down
    echo Agents stopped
) else if "%choice%"=="4" (
    echo.
    echo Viewing logs (Ctrl+C to exit)...
    docker-compose -f docker-compose.agents.yml logs -f
) else if "%choice%"=="5" (
    echo.
    echo Checking agent status...
    docker-compose -f docker-compose.agents.yml ps
    echo.
    echo Querying orchestrator...
    curl -s http://localhost:8080/agents/status
) else if "%choice%"=="6" (
    echo.
    set /p confirm="This will remove all containers and volumes. Continue? [y/N]: "
    if /i "%confirm%"=="y" (
        docker-compose -f docker-compose.agents.yml down -v
        echo Cleanup complete
    ) else (
        echo Cancelled
    )
) else (
    echo Invalid choice
    exit /b 1
)
