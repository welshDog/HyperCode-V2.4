# 🔧 DOCKER DAEMON ERROR - DIAGNOSTIC & SOLUTIONS

**Error:** `request returned 500 Internal Server Error for API route`

**Root Cause:** Docker Desktop daemon is unresponsive or having connectivity issues

**Status:** 🔧 REQUIRES ACTION

---

## PROBLEM ANALYSIS

```
Error Message:
  request returned 500 Internal Server Error 
  for API route and version 
  http://%2F%2F.%2Fpipe%2FdockerDesktopLinuxEngine/_ping

This means:
  ❌ Docker daemon is not responding
  ❌ Docker socket connection failed
  ❌ Possible daemon crash or hang
```

---

## IMMEDIATE SOLUTIONS (Try in Order)

### Solution 1: Restart Docker Desktop (Recommended) ✅

**Windows:**
```powershell
# Close Docker Desktop completely
Stop-Process -Name "Docker Desktop" -Force -ErrorAction SilentlyContinue

# Wait a moment
Start-Sleep -Seconds 5

# Restart Docker Desktop
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

# Wait for it to start (2-3 minutes)
Write-Host "Docker Desktop restarting... please wait 2-3 minutes"
Start-Sleep -Seconds 120

# Verify it's running
docker ps
# Should succeed now
```

---

### Solution 2: Reset Docker Daemon

If restart doesn't work:

**Windows (PowerShell as Admin):**
```powershell
# Stop Docker
net stop com.docker.service

# Wait
Start-Sleep -Seconds 5

# Start Docker
net start com.docker.service

# Verify
docker ps
```

---

### Solution 3: Full Docker Reset

If still not working:

**Windows:**
```powershell
# 1. Stop Docker completely
Stop-Process -Name "Docker Desktop" -Force -ErrorAction SilentlyContinue
Stop-Process -Name "com.docker.service" -Force -ErrorAction SilentlyContinue

# 2. Clear Docker temp/socket files
Remove-Item -Path "$env:TEMP\docker*" -Force -Recurse -ErrorAction SilentlyContinue
Remove-Item -Path "\\.\pipe\docker_engine" -Force -ErrorAction SilentlyContinue

# 3. Restart Docker Desktop
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

# 4. Wait 2-3 minutes
Write-Host "Waiting for Docker to fully restart..."
Start-Sleep -Seconds 180

# 5. Verify
docker ps
docker compose config --services
```

---

### Solution 4: Check Docker Desktop Settings

If daemon keeps crashing:

**In Docker Desktop:**
1. Open Docker Desktop
2. Go to **Settings** → **Resources**
3. Check:
   - ✅ Memory: At least 2GB available
   - ✅ CPU: At least 2 cores assigned
   - ✅ Disk: At least 10GB free
4. Go to **Settings** → **General**
5. Uncheck "**Start Docker Desktop when you log in**" (restart will be manual)
6. Click **Apply & Restart**

---

### Solution 5: Use Alternative Docker Setup

If Docker Desktop is critically broken:

**Option A: Use Docker CLI directly (if installed separately)**
```powershell
# Test
docker --version
docker run --rm alpine echo test
```

**Option B: Reinstall Docker**
```powershell
# Uninstall
Add-AppxPackage -Register "C:\Program Files\Docker\Docker\AppxManifest.xml"
# Then reinstall from: https://www.docker.com/products/docker-desktop

# Or use Windows Subsystem for Linux:
# wsl --install
# apt install docker.io
```

---

## VERIFICATION STEPS

Once Docker is restarted, verify each step:

```powershell
# Step 1: Docker responding
Write-Host "Step 1: Testing Docker daemon..."
$test1 = docker ps 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Docker responding"
} else {
    Write-Host "❌ Still not responding"
    Exit 1
}

# Step 2: Compose working
Write-Host "`nStep 2: Testing Docker Compose..."
$test2 = docker compose config --services 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Docker Compose working"
    Write-Host "Services: $test2"
} else {
    Write-Host "❌ Compose failing"
    Exit 1
}

# Step 3: SkillWeaver in compose
Write-Host "`nStep 3: Checking for SkillWeaver..."
if ($test2 -contains "skillweaver") {
    Write-Host "✅ SkillWeaver found in services"
} else {
    Write-Host "❌ SkillWeaver not in compose"
    Exit 1
}

Write-Host "`n✅ ALL CHECKS PASSED - Ready to deploy"
```

---

## THEN RETRY DEPLOYMENT

Once Docker is responsive:

```powershell
# Build
Write-Host "Building SkillWeaver image..."
docker compose build skillweaver

if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed - check Docker resources"
    Exit 1
}

# Start
Write-Host "Starting SkillWeaver..."
docker compose up -d skillweaver

# Verify
Start-Sleep -Seconds 5
Write-Host "Verifying SkillWeaver..."
docker ps | Select-String skillweaver

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ SkillWeaver running!"
    
    # Test health
    Start-Sleep -Seconds 3
    Write-Host "Testing health endpoint..."
    $health = curl -s http://localhost:8051/health 2>&1
    Write-Host $health
} else {
    Write-Host "❌ Container failed to start"
    docker logs skillweaver
}
```

---

## IF NOTHING WORKS

Try direct Docker build (bypass compose):

```powershell
# Build directly
Write-Host "Building SkillWeaver image (direct)..."
docker build -f services/skillweaver/Dockerfile -t hypercode/skillweaver:latest .

if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed"
    Exit 1
}

# Run directly
Write-Host "Running SkillWeaver (direct)..."
docker run -d `
  --name skillweaver `
  -e REDIS_URL=redis://redis:6379 `
  -p 127.0.0.1:8051:8051 `
  --network hypercode_agents_net `
  --restart unless-stopped `
  hypercode/skillweaver:latest

# Check
docker ps | Select-String skillweaver
docker logs skillweaver
```

---

## COMMON CAUSES & FIXES

| Cause | Symptom | Fix |
|-------|---------|-----|
| Out of memory | Build hangs at 40.4s | Increase Docker memory in Settings |
| Out of disk space | Build fails after 40s | Free up disk space (10GB minimum) |
| CPU throttling | Build very slow | Increase CPU cores in Settings |
| Socket permission | 500 error | Restart Docker Desktop |
| Daemon crashed | No response | Restart Docker or reinstall |
| Port conflict | 8051 unavailable | `netstat -ano \| findstr 8051` to find process |

---

## DISK SPACE CHECK

```powershell
# Check available disk space
Write-Host "Checking disk space..."
Get-Volume | Where-Object { $_.DriveLetter -eq 'C' } | Select-Object DriveLetter, Size, SizeRemaining

# Expected: SizeRemaining > 10GB

# If low on space:
Write-Host "Cleaning Docker..."
docker system prune -a --volumes -f
```

---

## MEMORY CHECK

```powershell
# Check available memory
Write-Host "Checking available memory..."
Get-CimInstance Win32_ComputerSystem | Select-Object TotalPhysicalMemory
$memGB = (Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB
Write-Host "Total memory: $memGB GB"

# For Docker: Assign at least 4-6 GB in Docker Settings
```

---

## CPU CHECK

```powershell
# Check CPU cores
Write-Host "Checking CPU..."
$cpu = Get-CimInstance Win32_Processor | Select-Object NumberOfCores
Write-Host "CPU cores: $($cpu.NumberOfCores)"

# For Docker: Assign at least 2-4 cores
```

---

## NEXT STEPS

1. **Immediately:** Restart Docker Desktop
2. **Wait:** 2-3 minutes for full startup
3. **Verify:** Run `docker ps` - should work
4. **Then:** Retry the deployment command

```bash
docker compose build skillweaver && docker compose up -d skillweaver
```

---

## MONITORING DOCKER STARTUP

While Docker restarts, monitor with this script:

```powershell
Write-Host "Monitoring Docker startup..."
$maxRetries = 30
$count = 0

while ($count -lt $maxRetries) {
    $count++
    Write-Host "Attempt $count/$maxRetries..."
    
    $test = docker ps 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Docker is ready!"
        Break
    }
    
    Write-Host "  Still starting... waiting 10 seconds"
    Start-Sleep -Seconds 10
}

if ($count -ge $maxRetries) {
    Write-Host "❌ Docker failed to start after $maxRetries attempts"
    Exit 1
}
```

---

## FINAL CHECKLIST

Before trying deployment again:

- [ ] Docker Desktop is running (check system tray)
- [ ] `docker ps` returns output (not error)
- [ ] `docker compose config` shows services
- [ ] `skillweaver` appears in services list
- [ ] At least 2GB memory available
- [ ] At least 10GB disk space free
- [ ] Port 8051 is free: `netstat -ano | findstr 8051` (empty = free)

Once all checked: ✅ Ready to deploy

---

**Issue:** Docker daemon connectivity failure  
**Status:** Requires manual Docker restart  
**Expected Resolution Time:** 5-10 minutes  
**Next Command:** `docker compose build skillweaver && docker compose up -d skillweaver`
