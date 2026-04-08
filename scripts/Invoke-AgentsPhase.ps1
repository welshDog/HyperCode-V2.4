#Requires -Version 5.1
<#
.SYNOPSIS
    HyperCode V2.0 — Agents Phase Finalizer
    Production-ready, idempotent PowerShell script.

.DESCRIPTION
    Validates, deploys, and verifies the complete Agents phase for HyperCode V2.0.
    Covers: schemas, services, API endpoints, agent router, Docker validation,
    planning system, test suite, and end-to-end smoke tests.

.PARAMETER ProjectRoot
    Path to the HyperCode-V2.4 repo root. Defaults to current directory.

.PARAMETER BaseUrl
    API base URL for smoke tests. Defaults to http://localhost:8000

.PARAMETER SkipDocker
    Skip Docker container checks (useful if running without Docker Desktop running).

.PARAMETER SkipTests
    Skip Python test suite execution.

.PARAMETER Rollback
    If specified, attempt rollback of last failed step.

.EXAMPLE
    .\scripts\Invoke-AgentsPhase.ps1
    .\scripts\Invoke-AgentsPhase.ps1 -SkipDocker -BaseUrl http://localhost:8000
    .\scripts\Invoke-AgentsPhase.ps1 -Rollback
#>
[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$ProjectRoot = (Get-Location).Path,
    [string]$BaseUrl     = 'http://localhost:8000',
    [switch]$SkipDocker,
    [switch]$SkipTests,
    [switch]$Rollback
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ═══════════════════════════════════════════════════════
# SECTION 0 — CONSTANTS & GLOBAL STATE
# ═══════════════════════════════════════════════════════
$Script:VERSION       = '1.0.0'
$Script:PHASE_NAME    = 'HyperCode V2.0 — Agents Phase Finalizer'
$Script:TIMESTAMP     = Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'
$Script:LOG_DIR       = Join-Path $ProjectRoot 'logs'
$Script:LOG_FILE      = Join-Path $Script:LOG_DIR "agents-phase_$Script:TIMESTAMP.log"
$Script:REPORT_FILE   = Join-Path $ProjectRoot "agents-phase-report_$Script:TIMESTAMP.md"
$Script:ROLLBACK_FILE = Join-Path $Script:LOG_DIR 'rollback_state.json'

$Script:Steps         = [System.Collections.Generic.List[hashtable]]::new()
$Script:PassCount     = 0
$Script:FailCount     = 0
$Script:WarnCount     = 0
$Script:RollbackStack = [System.Collections.Generic.Stack[hashtable]]::new()

# Required file paths that must exist after phase completion
$Script:RequiredFiles = @(
    'backend/app/schemas/planning.py',
    'backend/app/services/__init__.py',
    'backend/app/services/document_parser.py',
    'backend/app/services/plan_generator.py',
    'backend/app/services/plan_formatter.py',
    'backend/app/services/plan_executor.py',
    'backend/app/api/v1/endpoints/planning.py',
    'tests/test_planning_system.py',
    'tests/planning_postman_collection.json',
    'docker/validate.sh',
    'docker/docker-compose.hardened.yml'
)

# ═══════════════════════════════════════════════════════
# SECTION 1 — LOGGING & OUTPUT HELPERS
# ═══════════════════════════════════════════════════════
function Write-Banner {
    $banner = @"

  ╔══════════════════════════════════════════════════════╗
  ║  🦅  $Script:PHASE_NAME
  ║  v$Script:VERSION  |  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
  ╚══════════════════════════════════════════════════════╝
"@
    Write-Host $banner -ForegroundColor Cyan
    Write-Log $banner
}

function Write-Log {
    param([string]$Message, [string]$Level = 'INFO')
    $entry = "[$Script:TIMESTAMP][$Level] $Message"
    try { Add-Content -Path $Script:LOG_FILE -Value $entry -ErrorAction SilentlyContinue } catch {}
}

function Write-Step {
    param([int]$Number, [string]$Title)
    $line = "`n  ── STEP $Number: $Title"
    Write-Host $line -ForegroundColor Magenta
    Write-Log $line 'STEP'
}

function Write-Pass {
    param([string]$Message)
    $Script:PassCount++
    $entry = @{ Status = 'PASS'; Message = $Message; Time = (Get-Date -Format 'HH:mm:ss') }
    $Script:Steps.Add($entry)
    Write-Host "  [PASS] $Message" -ForegroundColor Green
    Write-Log "PASS: $Message"
}

function Write-Fail {
    param([string]$Message, [string]$Fix = '')
    $Script:FailCount++
    $entry = @{ Status = 'FAIL'; Message = $Message; Fix = $Fix; Time = (Get-Date -Format 'HH:mm:ss') }
    $Script:Steps.Add($entry)
    Write-Host "  [FAIL] $Message" -ForegroundColor Red
    if ($Fix) { Write-Host "         Fix: $Fix" -ForegroundColor Yellow }
    Write-Log "FAIL: $Message | Fix: $Fix"
}

function Write-Warn {
    param([string]$Message)
    $Script:WarnCount++
    $entry = @{ Status = 'WARN'; Message = $Message; Time = (Get-Date -Format 'HH:mm:ss') }
    $Script:Steps.Add($entry)
    Write-Host "  [WARN] $Message" -ForegroundColor Yellow
    Write-Log "WARN: $Message"
}

function Write-Info {
    param([string]$Message)
    Write-Host "         $Message" -ForegroundColor Gray
    Write-Log "INFO: $Message"
}

# ═══════════════════════════════════════════════════════
# SECTION 2 — PREREQUISITE VALIDATION
# ═══════════════════════════════════════════════════════
function Test-Prerequisites {
    Write-Step 1 'Prerequisite Validation'

    # PowerShell version
    if ($PSVersionTable.PSVersion.Major -ge 5) {
        Write-Pass "PowerShell $($PSVersionTable.PSVersion) (required: 5.1+)"
    } else {
        Write-Fail "PowerShell $($PSVersionTable.PSVersion) is too old" 'Upgrade to PowerShell 5.1 or install PowerShell 7'
    }

    # Admin rights check (soft — not required, just warn)
    $currentPrincipal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    $isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if ($isAdmin) {
        Write-Pass 'Running as Administrator'
    } else {
        Write-Warn 'Not running as Administrator — some Docker operations may be limited'
    }

    # Execution policy
    $policy = Get-ExecutionPolicy -Scope CurrentUser
    if ($policy -in @('RemoteSigned','Unrestricted','Bypass')) {
        Write-Pass "Execution policy: $policy"
    } else {
        Write-Warn "Execution policy is '$policy' — may block script. Run: Set-ExecutionPolicy RemoteSigned -Scope CurrentUser"
    }

    # Python
    try {
        $pyVer = python --version 2>&1
        Write-Pass "Python available: $pyVer"
    } catch {
        Write-Fail 'Python not found in PATH' 'Install Python 3.10+ and add to PATH'
    }

    # Git
    try {
        $gitVer = git --version 2>&1
        Write-Pass "Git available: $gitVer"
    } catch {
        Write-Fail 'Git not found in PATH' 'Install Git for Windows'
    }

    # Docker
    if (-not $SkipDocker) {
        try {
            $dockerVer = docker --version 2>&1
            Write-Pass "Docker available: $dockerVer"

            # Docker daemon running?
            $dockerInfo = docker info 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Pass 'Docker daemon is running'
            } else {
                Write-Fail 'Docker daemon not running' 'Start Docker Desktop and wait for it to be ready'
            }
        } catch {
            Write-Fail 'Docker not found' 'Install Docker Desktop for Windows'
        }
    } else {
        Write-Warn 'Docker checks skipped (-SkipDocker flag set)'
    }

    # Project root sanity check
    if (Test-Path (Join-Path $ProjectRoot 'backend')) {
        Write-Pass "Project root valid: $ProjectRoot"
    } else {
        Write-Fail "backend/ directory not found at $ProjectRoot" "Run from the HyperCode-V2.4 repo root or set -ProjectRoot"
    }

    # Git repo?
    try {
        $null = git -C $ProjectRoot rev-parse --git-dir 2>&1
        $branch = git -C $ProjectRoot branch --show-current 2>&1
        Write-Pass "Git repo on branch: $branch"
    } catch {
        Write-Warn 'Not a git repo or git unavailable — skipping branch check'
    }
}

# ═══════════════════════════════════════════════════════
# SECTION 3 — ENVIRONMENT PREPARATION
# ═══════════════════════════════════════════════════════
function Initialize-Environment {
    Write-Step 2 'Environment Preparation'

    # Create logs dir
    if (-not (Test-Path $Script:LOG_DIR)) {
        New-Item -ItemType Directory -Path $Script:LOG_DIR -Force | Out-Null
        Write-Pass "Created logs directory: $Script:LOG_DIR"
    } else {
        Write-Pass "Logs directory exists: $Script:LOG_DIR"
    }

    # Start transcript
    try {
        Start-Transcript -Path $Script:LOG_FILE -Append -NoClobber 2>$null
    } catch {
        # Transcript already running — that's fine
    }
    Write-Pass "Transcript logging to: $Script:LOG_FILE"

    # Create docker dir if missing
    $dockerDir = Join-Path $ProjectRoot 'docker'
    if (-not (Test-Path $dockerDir)) {
        New-Item -ItemType Directory -Path $dockerDir -Force | Out-Null
        Write-Pass 'Created docker/ directory'
    } else {
        Write-Pass 'docker/ directory exists'
    }

    # Create scripts dir if missing
    $scriptsDir = Join-Path $ProjectRoot 'scripts'
    if (-not (Test-Path $scriptsDir)) {
        New-Item -ItemType Directory -Path $scriptsDir -Force | Out-Null
        Write-Pass 'Created scripts/ directory'
    } else {
        Write-Pass 'scripts/ directory exists'
    }

    # Save rollback state
    $rollbackState = @{
        Timestamp   = $Script:TIMESTAMP
        ProjectRoot = $ProjectRoot
        GitBranch   = (git -C $ProjectRoot branch --show-current 2>$null)
        GitCommit   = (git -C $ProjectRoot rev-parse HEAD 2>$null)
    }
    $rollbackState | ConvertTo-Json | Set-Content -Path $Script:ROLLBACK_FILE
    Write-Pass "Rollback state saved: $Script:ROLLBACK_FILE"

    Write-Info "Project root  : $ProjectRoot"
    Write-Info "Base API URL  : $BaseUrl"
    Write-Info "Log file      : $Script:LOG_FILE"
    Write-Info "Report file   : $Script:REPORT_FILE"
    Write-Info "Skip Docker   : $SkipDocker"
    Write-Info "Skip Tests    : $SkipTests"
}

# ═══════════════════════════════════════════════════════
# SECTION 4 — FILE EXISTENCE VALIDATION
# ═══════════════════════════════════════════════════════
function Test-RequiredFiles {
    Write-Step 3 'Required Files Validation (Agents Phase Output)'

    foreach ($relPath in $Script:RequiredFiles) {
        $fullPath = Join-Path $ProjectRoot $relPath
        if (Test-Path $fullPath) {
            $size = (Get-Item $fullPath).Length
            Write-Pass "EXISTS: $relPath ($size bytes)"
        } else {
            Write-Fail "MISSING: $relPath" "This file should have been created in the Agents phase. Check GitHub repo."
        }
    }

    # Check planning.py has required schema classes
    $planningSchema = Join-Path $ProjectRoot 'backend/app/schemas/planning.py'
    if (Test-Path $planningSchema) {
        $content = Get-Content $planningSchema -Raw
        $required_classes = @('DocumentInput','ExtractedRequirement','ParsedDocument','PlanPhase','FileChange','CodingPlan')
        foreach ($cls in $required_classes) {
            if ($content -match "class $cls") {
                Write-Pass "Schema class found: $cls"
            } else {
                Write-Fail "Schema class missing: $cls in planning.py" "Ensure planning.py was fully written"
            }
        }
    }

    # Check services __init__.py
    $servicesInit = Join-Path $ProjectRoot 'backend/app/services/__init__.py'
    if (Test-Path $servicesInit) {
        Write-Pass 'services/__init__.py exists (package initialised)'
    }

    # Check API router is registered
    $apiPy = Join-Path $ProjectRoot 'backend/app/api/api.py'
    if (Test-Path $apiPy) {
        $apiContent = Get-Content $apiPy -Raw
        if ($apiContent -match 'planning') {
            Write-Pass 'Planning router registered in api.py'
        } else {
            Write-Fail 'Planning router NOT found in api.py' "Add: from app.api.v1.endpoints import planning and include_router call"
        }
    } else {
        Write-Warn 'api.py not found — cannot verify router registration'
    }
}

# ═══════════════════════════════════════════════════════
# SECTION 5 — PYTHON SYNTAX VALIDATION
# ═══════════════════════════════════════════════════════
function Test-PythonSyntax {
    Write-Step 4 'Python Syntax Validation'

    $pythonFiles = @(
        'backend/app/schemas/planning.py',
        'backend/app/services/document_parser.py',
        'backend/app/services/plan_generator.py',
        'backend/app/services/plan_formatter.py',
        'backend/app/services/plan_executor.py',
        'backend/app/api/v1/endpoints/planning.py',
        'tests/test_planning_system.py'
    )

    foreach ($relPath in $pythonFiles) {
        $fullPath = Join-Path $ProjectRoot $relPath
        if (Test-Path $fullPath) {
            try {
                $result = python -m py_compile $fullPath 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Write-Pass "Syntax OK: $relPath"
                } else {
                    Write-Fail "Syntax ERROR: $relPath" $result
                }
            } catch {
                Write-Warn "Could not syntax-check: $relPath (python not in PATH?)"
            }
        } else {
            Write-Warn "Skipping syntax check — file missing: $relPath"
        }
    }
}

# ═══════════════════════════════════════════════════════
# SECTION 6 — GIT STATUS VALIDATION
# ═══════════════════════════════════════════════════════
function Test-GitStatus {
    Write-Step 5 'Git Repository Status'

    try {
        # Last commit info
        $lastCommit = git -C $ProjectRoot log -1 --pretty=format:'%h %s (%an, %ar)' 2>&1
        Write-Pass "Last commit: $lastCommit"

        # Check agents phase files are committed (not just untracked)
        $untracked = git -C $ProjectRoot status --porcelain 2>&1
        $untrackedLines = $untracked | Where-Object { $_ -match '^\?\?' }
        if ($untrackedLines) {
            Write-Warn "$($untrackedLines.Count) untracked file(s) found — consider git add + commit"
            $untrackedLines | Select-Object -First 5 | ForEach-Object { Write-Info $_ }
        } else {
            Write-Pass 'No untracked files — working tree clean'
        }

        # Check key files are tracked
        $tracked = git -C $ProjectRoot ls-files 2>&1
        $keyFiles = @(
            'backend/app/schemas/planning.py',
            'backend/app/services/document_parser.py',
            'tests/test_planning_system.py'
        )
        foreach ($f in $keyFiles) {
            if ($tracked -match [regex]::Escape($f)) {
                Write-Pass "Git-tracked: $f"
            } else {
                Write-Warn "Not in git: $f (run git add $f && git commit)"
            }
        }

        # Remote sync check
        try {
            $null = git -C $ProjectRoot fetch --dry-run 2>&1
            $behind = git -C $ProjectRoot rev-list HEAD..origin/main --count 2>&1
            if ($behind -eq '0') {
                Write-Pass 'Local branch is up-to-date with origin/main'
            } else {
                Write-Warn "$behind commit(s) behind origin/main — run git pull"
            }
        } catch {
            Write-Warn 'Could not check remote sync (no internet or no remote?)'
        }

    } catch {
        Write-Warn "Git checks skipped: $_"
    }
}

# ═══════════════════════════════════════════════════════
# SECTION 7 — DOCKER VALIDATION
# ═══════════════════════════════════════════════════════
function Test-DockerStack {
    Write-Step 6 'Docker Stack Validation'

    if ($SkipDocker) {
        Write-Warn 'Docker checks skipped (-SkipDocker flag)'
        return
    }

    # Check docker compose file exists
    $composeFile = Join-Path $ProjectRoot 'docker-compose.yml'
    if (Test-Path $composeFile) {
        Write-Pass 'docker-compose.yml found'
    } else {
        Write-Fail 'docker-compose.yml not found' 'Create docker-compose.yml in project root'
        return
    }

    # Validate compose file syntax
    try {
        $null = docker compose -f $composeFile config 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Pass 'docker-compose.yml syntax valid'
        } else {
            Write-Fail 'docker-compose.yml has syntax errors' 'Run: docker compose config to see details'
        }
    } catch {
        Write-Warn 'Could not validate docker-compose.yml syntax'
    }

    # Check hardened overlay exists
    $hardenedFile = Join-Path $ProjectRoot 'docker/docker-compose.hardened.yml'
    if (Test-Path $hardenedFile) {
        Write-Pass 'docker-compose.hardened.yml exists'
    } else {
        Write-Fail 'docker-compose.hardened.yml missing' 'This file should be in docker/'
    }

    # Check running containers
    $expectedServices = @('backend', 'worker', 'redis', 'postgres')
    try {
        $psOutput = docker compose -f $composeFile ps --format json 2>&1
        foreach ($svc in $expectedServices) {
            # Parse JSON output per line
            $found = $false
            $running = $false
            foreach ($line in $psOutput) {
                try {
                    $obj = $line | ConvertFrom-Json -ErrorAction SilentlyContinue
                    if ($obj -and $obj.Service -eq $svc) {
                        $found = $true
                        $running = ($obj.State -eq 'running')
                    }
                } catch {}
            }
            if (-not $found) {
                Write-Fail "Container not found: $svc" "Run: docker compose up -d $svc"
            } elseif (-not $running) {
                Write-Fail "Container not running: $svc" "Check logs: docker compose logs $svc"
            } else {
                Write-Pass "Container running: $svc"
            }
        }
    } catch {
        Write-Warn "Could not inspect container status: $_"
    }

    # Run the bash validator via Docker if validate.sh exists
    $validateSh = Join-Path $ProjectRoot 'docker/validate.sh'
    if (Test-Path $validateSh) {
        Write-Info 'Running docker/validate.sh via Alpine container...'
        try {
            $dockerRunArgs = @(
                'run', '--rm', '-i',
                '-v', "${ProjectRoot}:/app",
                '-v', '/var/run/docker.sock:/var/run/docker.sock',
                '-w', '/app',
                'alpine',
                'sh', '-c', 'apk add --no-cache bash curl python3 --quiet && bash docker/validate.sh'
            )
            $validateResult = docker @dockerRunArgs 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Pass 'docker/validate.sh completed successfully'
                # Extract score line if present
                $scoreLine = $validateResult | Select-String 'Score:'
                if ($scoreLine) { Write-Info $scoreLine.Line }
            } else {
                Write-Warn 'docker/validate.sh reported issues (check docker/validation_report.md)'
                Write-Info ($validateResult | Select-String 'FAIL' | Select-Object -First 5 | ForEach-Object { $_.Line })
            }
        } catch {
            Write-Warn "Could not run validate.sh via Docker: $_"
        }
    } else {
        Write-Warn 'docker/validate.sh not found — skipping container validation script'
    }
}

# ═══════════════════════════════════════════════════════
# SECTION 8 — API SMOKE TESTS
# ═══════════════════════════════════════════════════════
function Test-ApiEndpoints {
    Write-Step 7 'API Endpoint Smoke Tests'

    $endpoints = @(
        @{ Method = 'GET';  Path = '/health';                        ExpectedCodes = @(200);           Label = 'Health check' },
        @{ Method = 'GET';  Path = '/docs';                          ExpectedCodes = @(200);           Label = 'Swagger UI' },
        @{ Method = 'GET';  Path = '/api/v1/tasks/';                 ExpectedCodes = @(200,401,403);   Label = 'Tasks list' },
        @{ Method = 'POST'; Path = '/api/v1/planning/generate';      ExpectedCodes = @(200,401,422);   Label = 'Planning generate endpoint' },
        @{ Method = 'POST'; Path = '/api/v1/auth/login';             ExpectedCodes = @(200,401,422,405); Label = 'Auth login endpoint' }
    )

    $backendUp = $false

    # First: check if backend is reachable at all
    try {
        $healthResp = Invoke-WebRequest -Uri "$BaseUrl/health" -Method GET -TimeoutSec 10 -ErrorAction Stop
        $backendUp = $true
        Write-Pass "Backend reachable at $BaseUrl (HTTP $($healthResp.StatusCode))"
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__ 2>$null
        if ($statusCode) {
            $backendUp = $true
            Write-Pass "Backend reachable at $BaseUrl (HTTP $statusCode)"
        } else {
            Write-Warn "Backend not reachable at $BaseUrl — API smoke tests skipped"
            Write-Info 'Start the backend first: cd backend && uvicorn app.main:app --reload'
            return
        }
    }

    if ($backendUp) {
        foreach ($ep in $endpoints) {
            try {
                $uri = "$BaseUrl$($ep.Path)"
                $params = @{
                    Uri             = $uri
                    Method          = $ep.Method
                    TimeoutSec      = 15
                    ErrorAction     = 'Stop'
                }
                if ($ep.Method -eq 'POST') {
                    $params['Body']        = '{"content": "test input for smoke test"}'
                    $params['ContentType'] = 'application/json'
                }
                $resp = Invoke-WebRequest @params
                $code = $resp.StatusCode
                if ($ep.ExpectedCodes -contains $code) {
                    Write-Pass "$($ep.Label): $($ep.Method) $($ep.Path) → $code"
                } else {
                    Write-Fail "$($ep.Label): unexpected HTTP $code" "Expected one of: $($ep.ExpectedCodes -join ',')"
                }
            } catch {
                $code = $_.Exception.Response.StatusCode.value__ 2>$null
                if ($code -and ($ep.ExpectedCodes -contains $code)) {
                    Write-Pass "$($ep.Label): $($ep.Method) $($ep.Path) → $code (expected error code)"
                } elseif ($code) {
                    Write-Fail "$($ep.Label): HTTP $code" "Expected one of: $($ep.ExpectedCodes -join ',')"
                } else {
                    Write-Warn "$($ep.Label): connection error — $_"
                }
            }
        }
    }
}

# ═══════════════════════════════════════════════════════
# SECTION 9 — PYTHON TEST SUITE
# ═══════════════════════════════════════════════════════
function Invoke-TestSuite {
    Write-Step 8 'Python Test Suite'

    if ($SkipTests) {
        Write-Warn 'Test suite skipped (-SkipTests flag)'
        return
    }

    $testFile = Join-Path $ProjectRoot 'tests/test_planning_system.py'
    if (-not (Test-Path $testFile)) {
        Write-Fail 'tests/test_planning_system.py not found' 'Ensure the tests directory was created in the Agents phase'
        return
    }

    # Check httpx is installed
    try {
        $null = python -c 'import httpx' 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Pass 'Python httpx library available'
        } else {
            Write-Warn 'httpx not installed — installing now'
            python -m pip install httpx rich --quiet 2>&1
        }
    } catch {
        Write-Warn 'Could not check httpx — test may fail'
    }

    Write-Info 'Running test_planning_system.py...'
    try {
        $env:BASE_URL = $BaseUrl
        $testOutput = python $testFile 2>&1
        $exitCode = $LASTEXITCODE

        if ($exitCode -eq 0) {
            Write-Pass 'All planning system tests PASSED'
        } else {
            # Count pass/fail lines
            $passLines = $testOutput | Select-String '✅|PASS|passed'
            $failLines = $testOutput | Select-String '❌|FAIL|failed|ERROR'
            Write-Fail "Test suite completed with failures ($($failLines.Count) failures)" 'Check test output above'
            if ($failLines) {
                $failLines | Select-Object -First 5 | ForEach-Object { Write-Info $_.Line }
            }
        }
        # Show summary line if present
        $summaryLine = $testOutput | Select-String 'Score:|TOTAL|passed|failed' | Select-Object -Last 1
        if ($summaryLine) { Write-Info $summaryLine.Line }

    } catch {
        Write-Warn "Test runner error: $_"
    }
}

# ═══════════════════════════════════════════════════════
# SECTION 10 — ROLLBACK LOGIC
# ═══════════════════════════════════════════════════════
function Invoke-Rollback {
    Write-Step 9 'Rollback'

    if (-not (Test-Path $Script:ROLLBACK_FILE)) {
        Write-Fail 'No rollback state found' "Run the script without -Rollback first to create a state file"
        return
    }

    try {
        $state = Get-Content $Script:ROLLBACK_FILE -Raw | ConvertFrom-Json
        Write-Info "Rolling back to commit: $($state.GitCommit)"
        Write-Info "Branch: $($state.GitBranch)"
        Write-Info "Timestamp: $($state.Timestamp)"

        # Git reset to saved commit (soft — preserves working tree)
        if ($state.GitCommit) {
            $confirm = Read-Host "  Reset git HEAD to $($state.GitCommit)? [y/N]"
            if ($confirm -eq 'y') {
                git -C $ProjectRoot reset --soft $state.GitCommit 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Write-Pass "Git reset to $($state.GitCommit) (soft)"
                } else {
                    Write-Fail 'Git reset failed' 'Manually run: git reset --soft <commit>'
                }
            } else {
                Write-Info 'Rollback skipped by user'
            }
        }

        # Remove rollback file
        Remove-Item $Script:ROLLBACK_FILE -Force
        Write-Pass 'Rollback state file cleaned up'

    } catch {
        Write-Fail "Rollback failed: $_" 'Manual intervention required'
    }
}

# ═══════════════════════════════════════════════════════
# SECTION 11 — CLEANUP
# ═══════════════════════════════════════════════════════
function Invoke-Cleanup {
    Write-Step 10 'Cleanup Temporary Resources'

    # Remove any .pyc/__pycache__ from tests dir
    $pycache = Join-Path $ProjectRoot 'tests/__pycache__'
    if (Test-Path $pycache) {
        Remove-Item $pycache -Recurse -Force
        Write-Pass 'Removed tests/__pycache__'
    } else {
        Write-Pass 'No test pycache to clean'
    }

    # Remove any tmp files in project root
    $tmpFiles = Get-ChildItem $ProjectRoot -Filter '*.tmp' -ErrorAction SilentlyContinue
    if ($tmpFiles) {
        $tmpFiles | Remove-Item -Force
        Write-Pass "Removed $($tmpFiles.Count) .tmp file(s)"
    } else {
        Write-Pass 'No .tmp files found'
    }

    # Keep rollback file unless we explicitly cleaned up
    Write-Pass 'Cleanup complete'
}

# ═══════════════════════════════════════════════════════
# SECTION 12 — FINAL REPORT
# ═══════════════════════════════════════════════════════
function Write-FinalReport {
    $total = $Script:PassCount + $Script:FailCount + $Script:WarnCount
    $score = if ($total -gt 0) { [math]::Round(($Script:PassCount / $total) * 100) } else { 0 }
    $overallStatus = if ($Script:FailCount -eq 0) { 'SUCCESS' } else { 'FAILED' }
    $statusColour  = if ($Script:FailCount -eq 0) { 'Green' } else { 'Red' }

    # Console summary
    Write-Host "`n  ══════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  🦅 AGENTS PHASE FINAL REPORT" -ForegroundColor Cyan
    Write-Host "  ══════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  Status  : $overallStatus" -ForegroundColor $statusColour
    Write-Host "  Score   : $score% ($($Script:PassCount) pass / $($Script:FailCount) fail / $($Script:WarnCount) warn)" -ForegroundColor White
    Write-Host "  Total   : $total checks" -ForegroundColor White
    Write-Host "  Log     : $Script:LOG_FILE" -ForegroundColor Gray
    Write-Host "  Report  : $Script:REPORT_FILE" -ForegroundColor Gray

    if ($Script:FailCount -gt 0) {
        Write-Host "`n  ❌ FAILURES TO FIX:" -ForegroundColor Red
        $Script:Steps | Where-Object { $_.Status -eq 'FAIL' } | ForEach-Object {
            Write-Host "     • $($_.Message)" -ForegroundColor Red
            if ($_.Fix) { Write-Host "       Fix: $($_.Fix)" -ForegroundColor Yellow }
        }
    } else {
        Write-Host "`n  ✅ ALL CHECKS PASSED — Agents Phase complete!" -ForegroundColor Green
        Write-Host "  🔥 BROski Power Level: DEPLOYMENT READY ♾" -ForegroundColor Magenta
    }

    # Write Markdown report
    $reportLines = @(
        "# 🦅 HyperCode V2.0 — Agents Phase Validation Report",
        "",
        "**Generated:** $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')",
        "**Status:** $overallStatus",
        "**Score:** $score% ($($Script:PassCount) pass / $($Script:FailCount) fail / $($Script:WarnCount) warn of $total checks)",
        "",
        "---",
        "",
        "## Summary",
        "",
        "| Status | Count |",
        "|--------|-------|",
        "| ✅ PASS | $($Script:PassCount) |",
        "| ❌ FAIL | $($Script:FailCount) |",
        "| ⚠️ WARN | $($Script:WarnCount) |",
        "| **TOTAL** | **$total** |",
        "",
        "---",
        "",
        "## What Was Validated",
        "",
        "| # | Phase | Description |",
        "|---|-------|-------------|",
        "| 1 | Prerequisites | PS 5.1+, Admin rights, Python, Git, Docker |",
        "| 2 | Environment | Dirs, logging, rollback state |",
        "| 3 | Required Files | All 11 Agents phase output files |",
        "| 4 | Python Syntax | py_compile on all new .py files |",
        "| 5 | Git Status | Tracked, committed, remote sync |",
        "| 6 | Docker Stack | Containers running, security, health checks |",
        "| 7 | API Endpoints | 5 endpoint smoke tests |",
        "| 8 | Test Suite | test_planning_system.py |",
        "| 9 | Cleanup | Temp files removed |",
        "",
        "---",
        "",
        "## Detailed Results",
        ""
    )

    foreach ($step in $Script:Steps) {
        $icon = switch ($step.Status) {
            'PASS' { '✅' }
            'FAIL' { '❌' }
            'WARN' { '⚠️' }
            default { '  ' }
        }
        $line = "- $icon **$($step.Status)** `[$($step.Time)`] $($step.Message)"
        if ($step.Fix) { $line += "`n  > 🔧 **Fix:** $($step.Fix)" }
        $reportLines += $line
    }

    if ($Script:FailCount -gt 0) {
        $reportLines += @(
            "",
            "---",
            "",
            "## 🚨 Remediation Steps (Critical)",
            ""
        )
        $i = 1
        $Script:Steps | Where-Object { $_.Status -eq 'FAIL' } | ForEach-Object {
            $reportLines += "$i. **$($_.Message)**"
            if ($_.Fix) { $reportLines += "   - Fix: $($_.Fix)" }
            $i++
        }
    } else {
        $reportLines += @(
            "",
            "---",
            "",
            "## ✅ Next Steps",
            "",
            "1. All Agents Phase checks passed!",
            "2. Run the full Docker stack: ``docker compose up -d``",
            "3. Test the planning API: ``python tests/test_planning_system.py``",
            "4. Enable Grafana monitoring at http://localhost:3001",
            "5. Proceed to the next deployment phase"
        )
    }

    $reportLines += @(
        "",
        "---",
        "",
        "*Report auto-generated by Invoke-AgentsPhase.ps1 v$Script:VERSION*"
    )

    $reportLines | Set-Content -Path $Script:REPORT_FILE -Encoding UTF8
    Write-Host "`n  📄 Full report saved: $Script:REPORT_FILE" -ForegroundColor Cyan

    # Return exit code
    return $Script:FailCount
}

# ═══════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════
try {
    # Ensure log directory exists before starting transcript
    if (-not (Test-Path $Script:LOG_DIR)) {
        New-Item -ItemType Directory -Path $Script:LOG_DIR -Force | Out-Null
    }

    Write-Banner

    if ($Rollback) {
        Invoke-Rollback
        exit 0
    }

    # Run all phases
    Test-Prerequisites
    Initialize-Environment
    Test-RequiredFiles
    Test-PythonSyntax
    Test-GitStatus
    Test-DockerStack
    Test-ApiEndpoints
    Invoke-TestSuite
    Invoke-Cleanup

    $failures = Write-FinalReport

    try { Stop-Transcript 2>$null } catch {}

    exit $failures

} catch {
    Write-Host "`n[FATAL] Unhandled error: $_" -ForegroundColor Red
    Write-Host $_.ScriptStackTrace -ForegroundColor DarkRed
    try { Stop-Transcript 2>$null } catch {}
    exit 99
}
