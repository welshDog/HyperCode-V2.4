# 🔧 SkillWeaver Diagnostics & Recovery Guide

**Comprehensive troubleshooting and verification procedures**

---

## 🚨 Docker Daemon Recovery

### Step 1: Force Stop & Restart Docker
```powershell
# Stop Docker completely
Stop-Process -Name "Docker Desktop" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 10

# Clear docker pipes/sockets (if persistent)
Remove-Item -Path "\\.\pipe\docker_engine" -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$env:TEMP\docker*" -Force -Recurse -ErrorAction SilentlyContinue

# Restart Docker
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
Write-Host "Waiting for Docker to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 180

# Verify Docker is responding
docker ps
Write-Host "✅ Docker is responding" -ForegroundColor Green
```

### Step 2: Restart SkillWeaver Service
```powershell
# Stop containers
docker compose stop skillweaver redis

# Wait
Start-Sleep -Seconds 5

# Start containers
docker compose up -d skillweaver redis

# Verify running
docker compose ps
```

---

## 📊 Complete Health Check Suite

### All-in-One Health Check
```powershell
Write-Host "🏥 SkillWeaver Complete Health Check" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Container Status
Write-Host "`n1. CONTAINER STATUS:" -ForegroundColor Yellow
docker ps --filter "name=skillweaver|redis" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 2. Redis Check
Write-Host "`n2. REDIS CONNECTION:" -ForegroundColor Yellow
docker exec redis redis-cli ping

# 3. Health Endpoint
Write-Host "`n3. HEALTH ENDPOINT:" -ForegroundColor Yellow
$health = Invoke-WebRequest -Uri "http://localhost:8051/health" -UseBasicParsing -TimeoutSec 5
$health.Content | ConvertFrom-Json | ConvertTo-Json

# 4. API Stats
Write-Host "`n4. API STATISTICS:" -ForegroundColor Yellow
$stats = Invoke-WebRequest -Uri "http://localhost:8051/api/v1/stats" -UseBasicParsing -TimeoutSec 5
$stats.Content | ConvertFrom-Json | ConvertTo-Json

# 5. Logs Check
Write-Host "`n5. RECENT LOGS:" -ForegroundColor Yellow
docker logs skillweaver --tail 20 | Select-String "ERROR|WARN" | Select-Object -First 5

# 6. Resource Usage
Write-Host "`n6. RESOURCE USAGE:" -ForegroundColor Yellow
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" skillweaver redis
```

---

## 🔍 Individual Diagnostic Tests

### Test 1: Docker Daemon Responsiveness
```powershell
Write-Host "Testing Docker daemon..." -ForegroundColor Yellow
$start = Get-Date
docker ps | Out-Null
$elapsed = ((Get-Date) - $start).TotalMilliseconds
Write-Host "Response time: ${elapsed}ms"
if ($elapsed -lt 1000) {
    Write-Host "✅ Docker responsive" -ForegroundColor Green
} else {
    Write-Host "⚠️  Docker slow ($elapsed ms)" -ForegroundColor Yellow
}
```

### Test 2: Container Health
```powershell
Write-Host "Checking SkillWeaver container..." -ForegroundColor Yellow

$container = docker inspect skillweaver --format "{{.State.Status}}"
Write-Host "Container status: $container"

if ($container -eq "running") {
    Write-Host "✅ Container running" -ForegroundColor Green
    
    # Check health status
    $health = docker inspect skillweaver --format "{{.State.Health.Status}}"
    Write-Host "Health status: $health"
    
    if ($health -eq "healthy") {
        Write-Host "✅ Health check passing" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Health check $health" -ForegroundColor Yellow
    }
} else {
    Write-Host "❌ Container not running: $container" -ForegroundColor Red
}
```

### Test 3: Port Accessibility
```powershell
Write-Host "Testing port 8051..." -ForegroundColor Yellow

try {
    $test = Test-NetConnection -ComputerName localhost -Port 8051 -WarningAction SilentlyContinue
    if ($test.TcpTestSucceeded) {
        Write-Host "✅ Port 8051 is open" -ForegroundColor Green
    } else {
        Write-Host "❌ Port 8051 is closed" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Port test failed: $_" -ForegroundColor Red
}
```

### Test 4: HTTP Endpoint
```powershell
Write-Host "Testing HTTP endpoints..." -ForegroundColor Yellow

$endpoints = @(
    "http://localhost:8051/health",
    "http://localhost:8051/docs",
    "http://localhost:8051/api/v1/stats",
    "http://localhost:8051/api/v1/skills/list"
)

foreach ($endpoint in $endpoints) {
    try {
        $response = Invoke-WebRequest -Uri $endpoint -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue
        $status = $response.StatusCode
        Write-Host "  $endpoint → HTTP $status ✅" -ForegroundColor Green
    } catch {
        Write-Host "  $endpoint → FAILED ❌" -ForegroundColor Red
    }
}
```

### Test 5: Redis Connectivity
```powershell
Write-Host "Testing Redis connectivity..." -ForegroundColor Yellow

try {
    $ping = docker exec redis redis-cli ping
    Write-Host "Redis response: $ping" -ForegroundColor Green
    
    $stats = docker exec redis redis-cli info stats
    Write-Host "Redis stats: $stats" -ForegroundColor Green
} catch {
    Write-Host "❌ Redis test failed: $_" -ForegroundColor Red
}
```

### Test 6: Skill Registry Check
```powershell
Write-Host "Checking skill registry..." -ForegroundColor Yellow

try {
    $response = Invoke-WebRequest -Uri "http://localhost:8051/api/v1/skills/list" -UseBasicParsing
    $skills = $response.Content | ConvertFrom-Json
    Write-Host "Skills registered: $($skills.Count)"
    Write-Host "✅ Skill registry accessible" -ForegroundColor Green
} catch {
    Write-Host "❌ Skill registry error: $_" -ForegroundColor Red
}
```

### Test 7: Performance Baseline
```powershell
Write-Host "Testing API performance..." -ForegroundColor Yellow

$endpoints = @(
    "http://localhost:8051/health",
    "http://localhost:8051/api/v1/stats"
)

foreach ($endpoint in $endpoints) {
    $times = @()
    for ($i = 0; $i -lt 5; $i++) {
        $start = Get-Date
        try {
            Invoke-WebRequest -Uri $endpoint -UseBasicParsing -TimeoutSec 5 | Out-Null
        } catch {}
        $elapsed = ((Get-Date) - $start).TotalMilliseconds
        $times += $elapsed
    }
    
    $avg = ($times | Measure-Object -Average).Average
    $min = ($times | Measure-Object -Minimum).Minimum
    $max = ($times | Measure-Object -Maximum).Maximum
    
    Write-Host "  $endpoint"
    Write-Host "    Avg: ${avg}ms | Min: ${min}ms | Max: ${max}ms"
    
    if ($avg -lt 100) {
        Write-Host "    ✅ Good performance" -ForegroundColor Green
    } elseif ($avg -lt 500) {
        Write-Host "    ⚠️  Acceptable performance" -ForegroundColor Yellow
    } else {
        Write-Host "    ❌ Poor performance" -ForegroundColor Red
    }
}
```

### Test 8: Skill Registration Test
```powershell
Write-Host "Testing skill registration..." -ForegroundColor Yellow

$skill = @{
    skill_id = "health_check_test_skill"
    name = "Health Check Test"
    description = "Temporary skill for health testing"
    category = "testing"
    inputs = @{ input = "str" }
    outputs = @{ output = "str" }
    execution_time_ms = 100
    cost_tokens = 50
    dependencies = @()
} | ConvertTo-Json

try {
    $response = Invoke-WebRequest `
        -Uri "http://localhost:8051/api/v1/skills/register" `
        -Method POST `
        -ContentType "application/json" `
        -Body $skill `
        -UseBasicParsing
    
    Write-Host "✅ Skill registration successful" -ForegroundColor Green
    Write-Host "Response: $($response.StatusCode)"
} catch {
    Write-Host "❌ Skill registration failed: $_" -ForegroundColor Red
}
```

---

## 🎯 Automated Health Check Script

Save as `skillweaver_health_check.ps1`:

```powershell
param(
    [switch]$Verbose,
    [switch]$Full,
    [switch]$Recovery
)

$results = @{
    timestamp = Get-Date
    checks = @()
    passed = 0
    failed = 0
    warnings = 0
}

function Test-Check {
    param($name, $scriptBlock, $severity = "error")
    
    Write-Host "Testing: $name..." -ForegroundColor Cyan
    try {
        $result = & $scriptBlock
        if ($result) {
            Write-Host "  ✅ PASS" -ForegroundColor Green
            $results.checks += @{ name = $name; status = "pass"; result = $result }
            $results.passed++
        } else {
            Write-Host "  ⚠️  WARNING" -ForegroundColor Yellow
            $results.warnings++
        }
    } catch {
        Write-Host "  ❌ FAIL: $_" -ForegroundColor Red
        $results.checks += @{ name = $name; status = "fail"; error = $_ }
        $results.failed++
    }
}

# Run recovery if requested
if ($Recovery) {
    Write-Host "🔄 Attempting Docker recovery..." -ForegroundColor Yellow
    Stop-Process -Name "Docker Desktop" -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 10
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    Start-Sleep -Seconds 180
}

# Run checks
Write-Host "`n🏥 SkillWeaver Health Check`n" -ForegroundColor Cyan

Test-Check "Docker Daemon" { docker ps | Out-Null; $true }
Test-Check "SkillWeaver Container" { 
    $status = docker inspect skillweaver --format "{{.State.Status}}"
    $status -eq "running"
}
Test-Check "Redis Container" {
    $status = docker inspect redis --format "{{.State.Status}}"
    $status -eq "running"
}
Test-Check "Port 8051 Open" {
    Test-NetConnection -ComputerName localhost -Port 8051 -WarningAction SilentlyContinue | Select-Object -ExpandProperty TcpTestSucceeded
}
Test-Check "Health Endpoint" {
    $response = Invoke-WebRequest -Uri "http://localhost:8051/health" -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue
    $response.StatusCode -eq 200
}
Test-Check "Skills List Endpoint" {
    $response = Invoke-WebRequest -Uri "http://localhost:8051/api/v1/skills/list" -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue
    $response.StatusCode -eq 200
}
Test-Check "Stats Endpoint" {
    $response = Invoke-WebRequest -Uri "http://localhost:8051/api/v1/stats" -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue
    $response.StatusCode -eq 200
}
Test-Check "Redis Ping" {
    $pong = docker exec redis redis-cli ping
    $pong -eq "PONG"
}

# Summary
Write-Host "`n📊 SUMMARY" -ForegroundColor Yellow
Write-Host "  Passed:  $($results.passed) ✅"
Write-Host "  Warnings: $($results.warnings) ⚠️"
Write-Host "  Failed:  $($results.failed) ❌"

if ($results.failed -gt 0) {
    Write-Host "`n❌ HEALTH CHECK FAILED" -ForegroundColor Red
    exit 1
} elseif ($results.warnings -gt 0) {
    Write-Host "`n⚠️  HEALTH CHECK PASSED WITH WARNINGS" -ForegroundColor Yellow
    exit 0
} else {
    Write-Host "`n✅ HEALTH CHECK PASSED" -ForegroundColor Green
    exit 0
}
```

**Usage:**
```powershell
# Basic check
.\skillweaver_health_check.ps1

# With recovery
.\skillweaver_health_check.ps1 -Recovery

# Verbose output
.\skillweaver_health_check.ps1 -Verbose
```

---

## 📈 Monitoring & Logging

### View Real-Time Logs
```powershell
# Follow logs
docker logs -f skillweaver

# Last 50 lines
docker logs skillweaver --tail 50

# Errors only
docker logs skillweaver | Select-String "ERROR"
```

### Docker Events
```powershell
# Watch Docker events
docker events --filter type=container --filter name=skillweaver
```

### Resource Monitoring
```powershell
# Real-time stats
docker stats skillweaver redis --no-stream

# With refresh
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

---

## 🔐 Security Check

```powershell
Write-Host "Checking security..." -ForegroundColor Yellow

# Check running as root (should NOT be)
docker exec skillweaver whoami

# Check network isolation
docker network inspect agents-net | Select-String "skillweaver"

# Check port exposure
docker port skillweaver
```

---

## 📝 Generate Full Report

```powershell
$report = @{
    timestamp = Get-Date
    docker_version = docker version --format "{{.Client.Version}}"
    containers = docker ps -a --format "{{.Names}}\t{{.Status}}"
    networks = docker network ls
    volumes = docker volume ls
    images = docker images | Select-String skillweaver
    compose_status = docker compose ps
    skillweaver = docker inspect skillweaver | ConvertFrom-Json | Select-Object -First 1
}

$report | ConvertTo-Json | Out-File "skillweaver_status_$(Get-Date -Format 'yyyy-MM-dd_HHmmss').json"
Write-Host "✅ Report saved" -ForegroundColor Green
```

---

## ✅ Success Criteria

All checks should show:
```
✅ Docker Daemon:         Responsive (<1s)
✅ SkillWeaver:           Running & Healthy
✅ Redis:                 Running & Responding
✅ Port 8051:             Open & Accessible
✅ Health Endpoint:       HTTP 200 (<100ms)
✅ API Endpoints:         HTTP 200 (<500ms)
✅ Skill Registration:    Working
✅ Logs:                  Clean (no errors)
```

---

**Use this guide to fully diagnose and verify SkillWeaver health.**
