#Requires -Version 5.1
[CmdletBinding(SupportsShouldProcess=$true)]
param (
    [Parameter(Mandatory)][ValidateSet('Development','Staging','Production')][string]$Environment,
    [Parameter(Mandatory)][ValidatePattern('^\d+\.\d+\.\d+$')][string]$Version,
    [string]$GitRemote     = 'https://github.com/welshDog/HyperCode-V2.4.git',
    [string]$GitBranch     = 'main',
    [string]$ProjectRoot   = 'H:\HyperStation zone\HyperCode\deploy\dashboard',
    [string]$DeployTarget  = 'H:\HyperStation zone\HyperCode\services\dashboard',
    [string]$IISTarget     = 'C:\inetpub\wwwroot\dashboard',
    [string]$DeployArchive = 'H:\HyperStation zone\HyperCode\deployments',
    [string]$LogRoot       = 'H:\HyperStation zone\HyperCode\logs',
    [string]$TeamsWebhookUrl = '',
    [int]$CoverageMin      = 80,
    [int]$MaxArtifacts     = 3
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Timestamp           = Get-Date -Format 'yyyyMMdd-HHmmss'
$LogFile             = "$LogRoot\dashboard-deploy-$Timestamp.log"
$BuildId             = "$Version-$Timestamp"
$global:CommitSHA    = 'unknown'
$script:DeployFailed = $false

if (-not (Test-Path $LogRoot)) { New-Item -ItemType Directory -Path $LogRoot -Force | Out-Null }

# ██ FUNCTIONS FIRST ██

function Write-Log {
    param([string]$Message, [ValidateSet('INFO','WARN','ERROR','VERBOSE','SUCCESS')][string]$Level='INFO')
    $entry  = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] [$Level] $Message"
    $colour = switch ($Level) {
        'SUCCESS'{'Green'} 'WARN'{'Yellow'} 'ERROR'{'Red'} 'VERBOSE'{'Gray'} default{'Cyan'}
    }
    if ($Level -eq 'VERBOSE') { Write-Verbose $entry } else { Write-Host $entry -ForegroundColor $colour }
    try { $entry | Out-File $LogFile -Append -Encoding utf8 } catch {}
}

function Invoke-Cmd {
    param([string]$Exe, [string[]]$ArgList, [string]$WorkDir = $PWD)
    Write-Log "▶ $Exe $($ArgList -join ' ')" 'VERBOSE'
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName         = $Exe
    $psi.Arguments        = ($ArgList | ForEach-Object { if ($_ -match '\s') { "`"$_`"" } else { $_ } }) -join ' '
    $psi.WorkingDirectory = $WorkDir
    $psi.UseShellExecute  = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError  = $true
    $proc   = [System.Diagnostics.Process]::Start($psi)
    $stdout = $proc.StandardOutput.ReadToEnd()
    $stderr = $proc.StandardError.ReadToEnd()
    $proc.WaitForExit()
    try { if ($stdout) { $stdout | Out-File $LogFile -Append -Encoding utf8 } } catch {}
    try { if ($stderr) { $stderr | Out-File $LogFile -Append -Encoding utf8 } } catch {}
    if ($proc.ExitCode -ne 0) { throw "Exit $($proc.ExitCode): $Exe $($ArgList -join ' ')`n$stderr" }
    return $stdout
}

function Send-Notification {
    param([string]$Status, [string]$ErrorMsg = '')
    $facts = @(
        @{name='Environment';value=$Environment}
        @{name='Version';value=$Version}
        @{name='Commit';value=$global:CommitSHA}
        @{name='Timestamp';value=$Timestamp}
        @{name='Log';value=$LogFile}
    )
    if ($ErrorMsg) { $facts += @{name='Error';value=$ErrorMsg} }
    if ($TeamsWebhookUrl) {
        try {
            $body = @{
                '@type'='MessageCard';'@context'='http://schema.org/extensions'
                themeColor = if ($Status -eq 'SUCCESS') {'00FF00'} else {'FF0000'}
                summary    = "HyperCode Deploy $Status"
                sections   = @(@{activityTitle="HyperCode v$Version $Status";facts=$facts})
            } | ConvertTo-Json -Depth 5
            Invoke-RestMethod -Uri $TeamsWebhookUrl -Method Post -ContentType 'application/json' -Body $body
        } catch { Write-Log "⚠ Webhook failed: $_" 'WARN' }
    }
}

function Invoke-Step {
    param([string]$Name, [scriptblock]$Action)
    Write-Log "━━━ STARTING: $Name ━━━" 'INFO'
    try { & $Action; Write-Log "━━━ DONE: $Name ✅ ━━━" 'SUCCESS' }
    catch {
        Write-Log "━━━ FAILED: $Name ❌ — $_" 'ERROR'
        Send-Notification -Status "FAILED at $Name" -ErrorMsg "$_"
        $script:DeployFailed = $true
    }
}

function Invoke-Rollback {
    [CmdletBinding(SupportsShouldProcess)] param(
        [string]$ArchivePath = 'H:\HyperStation zone\HyperCode\deployments',
        [string]$DeployDest  = 'H:\HyperStation zone\HyperCode\services\dashboard',
        [string]$ServiceName = 'HyperCodeDashboard'
    )
    Write-Host "`n↩ ROLLBACK INITIATED" -ForegroundColor Yellow
    $arts = Get-ChildItem "$ArchivePath\artifacts\*.zip" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
    if ($null -eq $arts -or $arts.Count -lt 2) { Write-Host "❌ No previous artifact found!" -ForegroundColor Red; return }
    $prev = $arts[1]
    Write-Host "↩ Restoring: $($prev.Name)" -ForegroundColor Yellow
    $svc = Get-Service $ServiceName -ErrorAction SilentlyContinue
    if ($svc -and $svc.Status -eq 'Running' -and $PSCmdlet.ShouldProcess($ServiceName,'Stop')) {
        Stop-Service $ServiceName -Force; Start-Sleep 3
    }
    if ($PSCmdlet.ShouldProcess($DeployDest,"Restore $($prev.Name)")) {
        if (-not (Test-Path $DeployDest)) { New-Item -ItemType Directory $DeployDest -Force | Out-Null }
        Expand-Archive $prev.FullName $DeployDest -Force
        Write-Host "✅ ROLLBACK COMPLETE → $($prev.Name)" -ForegroundColor Green
    }
    $bk = Get-ChildItem "$ArchivePath\db-backups\*.sql" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($bk) { Write-Host "🗄 DB backup: psql --dbname=<URL> -f `"$($bk.FullName)`"" -ForegroundColor Cyan }
}

# ██ MAIN ██

Write-Log "🦅 HyperCode Deploy STARTING — v$Version → $Environment" 'SUCCESS'
Write-Log "📋 Log: $LogFile" 'INFO'

# PHASE 1
$RepoPath = "$ProjectRoot\repo"
Invoke-Step '1 · Environment Preparation' {
    $tools = @(
        @{Name='git';   WinGet='Git.Git';             MinVer=[version]'2.40';Check='git --version'}
        @{Name='node';  WinGet='OpenJS.NodeJS.LTS';   MinVer=[version]'18.0';Check='node --version'}
        @{Name='npm';   WinGet=$null;                  MinVer=[version]'9.0'; Check='npm --version'}
        @{Name='python';WinGet='Python.Python.3.12';  MinVer=[version]'3.11';Check='python --version'}
        @{Name='docker';WinGet='Docker.DockerDesktop';MinVer=[version]'24.0';Check='docker --version'}
    )
    foreach ($t in $tools) {
        try {
            $raw = Invoke-Expression $t.Check 2>&1
            if (($raw -replace '[^\d\.]','') -match '(\d+\.\d+)') {
                $v = [version]$Matches[1]
                if ($v -lt $t.MinVer) { Write-Log "⚠ $($t.Name) v$v below min" 'WARN' }
                else                  { Write-Log "✅ $($t.Name) v$v — OK" 'INFO' }
            }
        } catch {
            Write-Log "⚠ $($t.Name) not found — installing..." 'WARN'
            if ($t.WinGet -and $PSCmdlet.ShouldProcess($t.Name,'winget install')) {
                Invoke-Cmd 'winget' @('install','--id',$t.WinGet,'--silent','--accept-package-agreements','--accept-source-agreements')
            }
        }
    }
    foreach ($d in @($ProjectRoot,$DeployTarget,$DeployArchive,"$DeployArchive\logs","$DeployArchive\artifacts","$DeployArchive\db-backups",$LogRoot)) {
        if (-not (Test-Path $d) -and $PSCmdlet.ShouldProcess($d,'mkdir')) {
            New-Item -ItemType Directory $d -Force | Out-Null
            Write-Log "📁 Created: $d" 'VERBOSE'
        }
    }
    Write-Log "📁 Folder structure ready." 'INFO'
}
if ($script:DeployFailed) { return }

# PHASE 2
Invoke-Step '2 · Source Code Acquisition' {
    if (Test-Path "$RepoPath\.git") {
        Write-Log "🔄 Pulling latest..." 'INFO'
        if ($PSCmdlet.ShouldProcess($RepoPath,'git pull')) {
            Invoke-Cmd 'git' @('-C',$RepoPath,'fetch','--all','--prune')
            Invoke-Cmd 'git' @('-C',$RepoPath,'checkout',$GitBranch)
            Invoke-Cmd 'git' @('-C',$RepoPath,'pull','--ff-only')
        }
    } else {
        Write-Log "⬇ Cloning → $RepoPath..." 'INFO'
        if ($PSCmdlet.ShouldProcess($RepoPath,'git clone')) {
            Invoke-Cmd 'git' @('clone','--branch',$GitBranch,'--depth','50',$GitRemote,$RepoPath)
        }
    }
    if (Test-Path $RepoPath) {
        $sha = Invoke-Cmd 'git' @('-C',$RepoPath,'rev-parse','HEAD')
        $global:CommitSHA = $sha.Trim()
        Write-Log "📌 Commit: $($global:CommitSHA)" 'INFO'
    } else {
        $global:CommitSHA = 'whatif-mode'
        Write-Log "ℹ WhatIf — no clone yet" 'VERBOSE'
    }
}
if ($script:DeployFailed) { return }

# PHASE 3
Invoke-Step '3 · Dependency Installation' {
    $venv = "$RepoPath\.venv"
    if (-not (Test-Path $venv) -and $PSCmdlet.ShouldProcess($venv,'venv create')) {
        Invoke-Cmd 'python' @('-m','venv',$venv)
    }
    $pip = "$venv\Scripts\pip.exe"
    if ((Test-Path $pip) -and $PSCmdlet.ShouldProcess('pip','install')) {
        Invoke-Cmd 'python' @('-m','pip','install','--upgrade','pip','--quiet') $RepoPath
        Invoke-Cmd $pip @('install','-r',"$RepoPath\requirements.txt",'--quiet','--cache-dir',"$ProjectRoot\.pip_cache")
        Write-Log "🐍 Python deps done." 'INFO'
    }
    if ((Test-Path "$RepoPath\package.json") -and $PSCmdlet.ShouldProcess('npm','ci')) {
        Invoke-Cmd 'npm' @('ci','--prefer-offline','--cache',"$ProjectRoot\.npm_cache") $RepoPath
        Write-Log "📦 Root Node deps done." 'INFO'
    }
    if ((Test-Path "$RepoPath\dashboard\package.json") -and $PSCmdlet.ShouldProcess('dashboard npm','ci')) {
        Invoke-Cmd 'npm' @('ci','--prefer-offline','--cache',"$ProjectRoot\.npm_cache") "$RepoPath\dashboard"
        Write-Log "📦 Dashboard Node deps done." 'INFO'
    }
}
if ($script:DeployFailed) { return }

# PHASE 4
$BuildDir = "$ProjectRoot\build-$BuildId"
Invoke-Step '4 · Build & Compile' {
    $env:NODE_ENV = $Environment.ToLower()
    $env:APP_VERSION = $Version
    if ($PSCmdlet.ShouldProcess($BuildDir,'mkdir')) { New-Item -ItemType Directory $BuildDir -Force | Out-Null }
    $py = "$RepoPath\.venv\Scripts\python.exe"
    if ((Test-Path "$RepoPath\backend\main.py") -and (Test-Path $py) -and $PSCmdlet.ShouldProcess('backend','compile')) {
        Invoke-Cmd $py @('-m','py_compile',"$RepoPath\backend\main.py")
        Write-Log "🔧 Backend syntax OK." 'INFO'
    }
    if ((Test-Path "$RepoPath\dashboard\package.json") -and $PSCmdlet.ShouldProcess('dashboard','build')) {
        Invoke-Cmd 'npm' @('run','build') "$RepoPath\dashboard"
        if (Test-Path "$RepoPath\dashboard\.next") {
            Copy-Item "$RepoPath\dashboard\.next" "$BuildDir\dashboard" -Recurse -Force
        }
        Write-Log "✅ Dashboard built → $BuildDir" 'SUCCESS'
    }
}
if ($script:DeployFailed) { return }

# PHASE 5
Invoke-Step '5 · Configuration & Secrets' {
    $envFile = "$BuildDir\.env.production"
    if ($PSCmdlet.ShouldProcess($envFile,'create')) {
        $src = "$RepoPath\.env.example"
        if (Test-Path $src) { Copy-Item $src $envFile -Force } else { New-Item -ItemType File $envFile -Force | Out-Null }
        @"
NODE_ENV=$($Environment.ToLower())
APP_VERSION=$Version
DEPLOY_TIMESTAMP=$Timestamp
"@ | Add-Content $envFile
    }
    foreach ($s in @('DB_URL','REDIS_URL','SECRET_KEY','OPENAI_API_KEY','DISCORD_TOKEN')) {
        $out = cmdkey /list:HyperCode_$s 2>&1
        if ($out -match "HyperCode_$s") { Write-Log "🔐 Found: HyperCode_$s" 'VERBOSE' }
        else { Write-Log "⚠ Missing: HyperCode_$s" 'WARN' }
    }
    Write-Log "🔐 Config ready: $envFile" 'INFO'
}
if ($script:DeployFailed) { return }

# PHASE 6
Invoke-Step '6 · Database Migration' {
    $alembic = "$RepoPath\.venv\Scripts\alembic.exe"
    if (Test-Path $alembic) {
        Write-Log "🗄 Running Alembic migrations..." 'INFO'
        if ($PSCmdlet.ShouldProcess('db','alembic upgrade head')) { Invoke-Cmd $alembic @('upgrade','head') $RepoPath }
        if (-not $WhatIfPreference) {
            $rev = Invoke-Cmd $alembic @('current') $RepoPath
            Write-Log "📋 Schema: $rev" 'INFO'
        }
    } else { Write-Log "ℹ No alembic — skipping." 'VERBOSE' }
}
if ($script:DeployFailed) { return }

# PHASE 7
Invoke-Step '7 · Static Asset Optimisation' {
    $assets   = Get-ChildItem $BuildDir -Recurse -Include '*.js','*.css','*.png','*.jpg','*.svg' -ErrorAction SilentlyContinue
    $manifest = @{}
    foreach ($a in $assets) {
        $manifest[$a.FullName.Replace($BuildDir,'').TrimStart('\')] = (Get-FileHash $a.FullName -Algorithm SHA256).Hash.Substring(0,8).ToLower()
    }
    if ($PSCmdlet.ShouldProcess("$BuildDir\asset-manifest.json",'write')) {
        $manifest | ConvertTo-Json -Depth 3 | Out-File "$BuildDir\asset-manifest.json" -Encoding utf8
    }
    Write-Log "📋 Manifest: $($manifest.Count) assets." 'INFO'
}
if ($script:DeployFailed) { return }

# PHASE 8
Invoke-Step '8 · Test Execution' {
    $pytest    = "$RepoPath\.venv\Scripts\pytest.exe"
    $reportDir = "$ProjectRoot\test-reports-$Timestamp"
    if ($PSCmdlet.ShouldProcess($reportDir,'mkdir')) { New-Item -ItemType Directory $reportDir -Force | Out-Null }
    if ((Test-Path $pytest) -and (Test-Path "$RepoPath\tests") -and $PSCmdlet.ShouldProcess('pytest','run')) {
        Invoke-Cmd $pytest @("$RepoPath\tests",'--tb=short','-q',"--junitxml=$reportDir\pytest-results.xml","--cov=$RepoPath","--cov-report=xml:$reportDir\coverage.xml","--cov-fail-under=$CoverageMin") $RepoPath
        Write-Log "✅ Python tests passed." 'SUCCESS'
    } else { Write-Log "ℹ No tests found — skipping." 'VERBOSE' }
}
if ($script:DeployFailed) { return }

# PHASE 9
$ArtifactPath = "$DeployArchive\artifacts\dashboard-$BuildId.zip"
Invoke-Step '9 · Packaging' {
    if ($PSCmdlet.ShouldProcess($BuildDir,'zip')) { Compress-Archive "$BuildDir\*" $ArtifactPath -Force -Exclude ".env.production" }
    if (Test-Path $ArtifactPath) {
        $sha256 = (Get-FileHash $ArtifactPath -Algorithm SHA256).Hash
        "$sha256  $ArtifactPath" | Out-File ($ArtifactPath -replace '\.zip$','.sha256') -Encoding utf8
        @{version=$Version;buildId=$BuildId;commitSHA=$global:CommitSHA;environment=$Environment;sha256=$sha256;artifact=$ArtifactPath} |
            ConvertTo-Json | Out-File ($ArtifactPath -replace '\.zip$','.manifest.json') -Encoding utf8
        Write-Log "🔑 SHA256: $sha256" 'INFO'
    }
    Get-ChildItem "$DeployArchive\artifacts\*.zip" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -Skip $MaxArtifacts |
        ForEach-Object { Remove-Item $_.FullName,$($_.FullName -replace '\.zip$','.sha256'),$($_.FullName -replace '\.zip$','.manifest.json') -Force -ErrorAction SilentlyContinue }
}
if ($script:DeployFailed) { return }

# PHASE 10
Invoke-Step '10 · Deployment' {
    $svc = Get-Service 'HyperCodeDashboard' -ErrorAction SilentlyContinue
    if ($svc -and $svc.Status -eq 'Running' -and $PSCmdlet.ShouldProcess('HyperCodeDashboard','Stop')) {
        Stop-Service 'HyperCodeDashboard' -Force; Start-Sleep 3
    }
    $dest = $DeployTarget
    if ($PSCmdlet.ShouldProcess($dest,'deploy')) {
        if (-not (Test-Path $dest)) { New-Item -ItemType Directory $dest -Force | Out-Null }
        if (Test-Path $ArtifactPath) { Expand-Archive $ArtifactPath $dest -Force }
        if (Test-Path "$BuildDir\.env.production") { Copy-Item "$BuildDir\.env.production" "$dest\.env.production" -Force }
    }
    if ($svc -and $PSCmdlet.ShouldProcess('HyperCodeDashboard','Start')) { Start-Service 'HyperCodeDashboard' -ErrorAction SilentlyContinue }
    if (-not $WhatIfPreference) {
        $w = 0
        do {
            Start-Sleep 2; $w += 2
            try { if ((Invoke-WebRequest 'http://localhost:8088' -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200) { Write-Log "✅ HTTP 200 in ${w}s" 'SUCCESS'; break } }
            catch { Write-Log "⏳ Waiting ${w}s..." 'VERBOSE' }
        } while ($w -lt 30)
        if ($w -ge 30) { throw "Dashboard not responding after 30s!" }
    }
}
if ($script:DeployFailed) { return }

# PHASE 11
Invoke-Step '11 · Post-Deploy Validation' {
    if (-not $WhatIfPreference) {
        foreach ($ep in @('/health','/api/agents','/api/status')) {
            try {
                $sw = [System.Diagnostics.Stopwatch]::StartNew()
                $r  = Invoke-WebRequest "http://localhost:8088$ep" -UseBasicParsing -TimeoutSec 5
                Write-Log "$(if($r.StatusCode -eq 200 -and $sw.ElapsedMilliseconds -lt 2000){'✅'}else{'⚠'}) $ep HTTP $($r.StatusCode) $($sw.ElapsedMilliseconds)ms" 'INFO'
            } catch { Write-Log "❌ $ep — $_" 'WARN' }
        }
    }
    if ($PSCmdlet.ShouldProcess("$DeployArchive\logs\rollback-$Timestamp.txt",'write')) {
        @"
ROLLBACK — Build: $BuildId
Artifact : $ArtifactPath
Log      : $LogFile
Run      : Invoke-Rollback
"@ | Out-File "$DeployArchive\logs\rollback-$Timestamp.txt" -Encoding utf8
    }
    Send-Notification -Status 'SUCCESS'
}

Write-Log "╔══════════════════════════════════════════╗" 'SUCCESS'
Write-Log "║  🦅 DEPLOYED! NICE ONE BROski♾! 🔥       ║" 'SUCCESS'
Write-Log "║  v$Version | $Environment | $($global:CommitSHA.Substring(0,[Math]::Min(8,$global:CommitSHA.Length)))" 'SUCCESS'
Write-Log "║  Log: $LogFile" 'SUCCESS'
Write-Log "╚══════════════════════════════════════════╝" 'SUCCESS'

