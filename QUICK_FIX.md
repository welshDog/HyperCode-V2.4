# ⚡ QUICK FIX: Docker Daemon Error (500 Internal Server Error)

## The Error
```
❌ request returned 500 Internal Server Error
   http://%2F%2F.%2Fpipe%2FdockerDesktopLinuxEngine/_ping
```

## The Fix (Do This Now)

### Step 1: Restart Docker Desktop
- Close Docker Desktop completely (icon in system tray → Quit)
- Wait 10 seconds
- Reopen Docker Desktop
- Wait 2-3 minutes for full startup

### Step 2: Verify Docker Works
```powershell
docker ps
# Should show your containers (even if empty list)
```

### Step 3: Check Resources
- Memory free: At least 2 GB
- Disk space free: At least 10 GB
- CPU: At least 2 cores available

If resources low:
```powershell
# Free disk space
docker system prune -a --volumes -f
```

### Step 4: Retry Deployment
```powershell
docker compose build skillweaver && docker compose up -d skillweaver
```

---

## If Still Failing

### Reset 1: Service Restart
```powershell
# As Administrator
net stop com.docker.service
Start-Sleep -Seconds 5
net start com.docker.service
Start-Sleep -Seconds 60
docker ps
```

### Reset 2: Full Docker Reset
```powershell
# Stop Docker
Stop-Process -Name "Docker Desktop" -Force -ErrorAction SilentlyContinue

# Clear sockets
Remove-Item -Path "\\.\pipe\docker_engine" -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$env:TEMP\docker*" -Force -Recurse -ErrorAction SilentlyContinue

# Restart
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

# Wait 3 minutes
Start-Sleep -Seconds 180

# Verify
docker ps
```

### Reset 3: Reinstall Docker
```powershell
# Via Settings
Settings → Apps → Docker Desktop → Uninstall
# Then download fresh from docker.com/download and reinstall
```

---

## Check List

Before trying again:

- [ ] Docker Desktop running (check taskbar)
- [ ] `docker ps` works (no errors)
- [ ] `docker compose config` works
- [ ] 2+ GB memory available
- [ ] 10+ GB disk space free
- [ ] Port 8051 not in use

If all checked ✅ → Try deployment

---

## Command to Deploy

```powershell
docker compose build skillweaver && docker compose up -d skillweaver
```

---

## Wait Time

Docker Desktop restart: **2-3 minutes**
Build SkillWeaver image: **1-2 minutes** (first time)
Total: **3-5 minutes**

---

**Status:** Follow steps above  
**Expected Outcome:** SkillWeaver running on port 8051  
**Verify:** `curl http://localhost:8051/health`
