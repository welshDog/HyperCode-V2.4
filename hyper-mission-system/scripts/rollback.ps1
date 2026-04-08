# Emergency Rollback Procedure

Write-Host "⚠️ INITIATING EMERGENCY ROLLBACK..." -ForegroundColor Yellow

# 1. Stop Production Services
Write-Host "Stopping Production Containers..."
docker-compose -f docker-compose.prod.yml down

# 2. Restore Database Backup (Optional - uncomment if data corruption occurred)
# Write-Host "Restoring Database..."
# docker-compose -f docker-compose.prod.yml up -d postgres
# Start-Sleep -Seconds 10
# Get-Content "../backups/production_backup.sql" | docker exec -i hyper-mission-system-postgres-1 psql -U user -d hypermission

# 3. Restart in Safe Mode (Single Replica)
Write-Host "Restarting with Minimal Configuration..."
docker-compose -f docker-compose.prod.yml up -d --scale server=1

# 4. Verification
Write-Host "Verifying Health..."
Start-Sleep -Seconds 5
$response = Invoke-WebRequest -Uri "http://localhost/api/tasks" -Method Head -ErrorAction SilentlyContinue
if ($response.StatusCode -eq 200) {
    Write-Host "✅ Rollback Successful. System is running in safe mode." -ForegroundColor Green
} else {
    Write-Host "❌ Rollback Failed. Manual intervention required." -ForegroundColor Red
}
