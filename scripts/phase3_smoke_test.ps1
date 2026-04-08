# Phase 3 Smoke Test — HyperCode V2.0

$pass = 0
$fail = 0

function Check($label, $cmd) {
    $result = Invoke-Expression $cmd 2>&1
    if ($LASTEXITCODE -eq 0 -or $result -match '"status"') {
        Write-Host "✅ $label" -ForegroundColor Green
        $script:pass++
    } else {
        Write-Host "❌ $label" -ForegroundColor Red
        Write-Host $result
        $script:fail++
    }
}

Write-Host "`n🦅 HyperCode Phase 3 Smoke Test`n" -ForegroundColor Cyan

Check "Core API health"           'curl -s http://127.0.0.1:8000/health'
Check "Orchestrator health"       'curl -s http://127.0.0.1:8081/health'
Check "Healer health (port 8010)" 'curl -s http://127.0.0.1:8010/health'
Check "Agent roster (/agents)"    'curl -s http://127.0.0.1:8081/agents'
Check "Dashboard reachable"       'curl -s -o $null -w "%{http_code}" http://127.0.0.1:8088'

Write-Host "`n📊 Results: $pass passed, $fail failed`n" -ForegroundColor Yellow

if ($fail -eq 0) {
    Write-Host "🔥 PHASE 3 COMPLETE — All systems GO`n" -ForegroundColor Green
    exit 0
}

Write-Host "⚠️  $fail checks failed — review above before enabling Phase 4`n" -ForegroundColor Red
exit 1
