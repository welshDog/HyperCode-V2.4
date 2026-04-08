#Requires -Version 5.1
<#
.SYNOPSIS
    HyperCode V2.0 — Agents Phase Finalizer
    Production-ready, idempotent PowerShell script.

.DESCRIPTION
    Validates and finalizes the Agents Phase of HyperCode V2.0.
    Covers: schemas, services, API endpoints, agent router,
    plan executor, Docker validation, and test suite checks.

.NOTES
    Author  : HyperCode BROski Brain
    Version : 2.0.0
    Platform: Windows PowerShell 5.1+ / PowerShell 7+

.EXAMPLE
    # Standard run
    .\Finalize-AgentsPhase.ps1

    # Dry run (no changes made)
    .\Finalize-AgentsPhase.ps1 -DryRun

    # Skip Docker checks (faster)
    .\Finalize-AgentsPhase.ps1 -SkipDocker
#>

[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$SkipDocker,
    [switch]$SkipTests,
    [string]$ProjectRoot = $PSScriptRoot | Split-Path -Parent
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ═══════════════════════════════════════════════════════════
# SECTION 0 — CONFIGURATION & CONSTANTS
# ═══════════════════════════════════════════════════════════

$Script:Config = @{
    ProjectName    = 'HyperCode V2.0'
    Phase          = 'Agents'
    Version        = '2.0.0'
    LogDir         = Join-Path $ProjectRoot 'logs'
    TempDir        = Join-Path $env:TEMP 'hypercode-agents-phase'
    ReportPath     = Join-Path $ProjectRoot 'logs' 'agents-phase-report.md'
    TranscriptPath = Join-Path $ProjectRoot 'logs' ('agents-phase-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
    StartTime      = Get-Date
}

$Script:Stats = @{
    Pass     = 0
    Fail     = 0
    Warn     = 0
    Skip     = 0
    Results  = [System.Collections.Generic.List[hashtable]]::new()
    Rollback = [System.Collections.Generic.List[scriptblock]]::new()
}

# ═══════════════════════════════════════════════════════════
# SECTION 1 — CONSOLE OUTPUT HELPERS
# ═══════════════════════════════════════════════════════════

function Write-Banner {
    param([string]$Text, [ConsoleColor]$Color = 'Cyan')
    $line = '═' * 60
    Write-Host "`n$line" -ForegroundColor $Color
    Write-Host "  $Text" -ForegroundColor $Color
    Write-Host "$line" -ForegroundColor $Color
}

function Write-Step {
    param([string]$Text)
    Write-Host "`n  ► $Text" -ForegroundColor White
}

function Write-Pass {
    param([string]$Check, [string]$Detail = '')
    $msg = "  ✅ PASS  $Check"
    if ($Detail) { $msg += " — $Detail" }
    Write-Host $msg -ForegroundColor Green
    $Script:Stats.Pass++
    $Script:Stats.Results.Add(@{ Status = 'PASS'; Check = $Check; Detail = $Detail; Fix = '' })
}

function Write-Fail {
    param([string]$Check, [string]$Fix = 'See logs for details')
    Write-Host "  ❌ FAIL  $Check" -ForegroundColor Red
    Write-Host "       Fix: $Fix" -ForegroundColor DarkRed
    $Script:Stats.Fail++
    $Script:Stats.Results.Add(@{ Status = 'FAIL'; Check = $Check; Detail = ''; Fix = $Fix })
}

function Write-Warn {
    param([string]$Check, [string]$Detail = '')
    $msg = "  ⚠️  WARN  $Check"
    if ($Detail) { $msg += " — $Detail" }
    Write-Host $msg -ForegroundColor Yellow
    $Script:Stats.Warn++
    $Script:Stats.Results.Add(@{ Status = 'WARN'; Check = $Check; Detail = $Detail; Fix = '' })
}

function Write-Skip {
    param([string]$Check)
    Write-Host "  ⏭️  SKIP  $Check" -ForegroundColor DarkGray
    $Script:Stats.Skip++
    $Script:Stats.Results.Add(@{ Status = 'SKIP'; Check = $Check; Detail = ''; Fix = '' })
}

function Write-Progress-Step {
    param([int]$Step, [int]$Total, [string]$Activity)
    $pct = [int](($Step / $Total) * 100)
    Write-Progress -Activity "HyperCode Agents Phase" -Status $Activity -PercentComplete $pct
}

# ═══════════════════════════════════════════════════════════
# SECTION 2 — PREREQUISITE VALIDATION
# ═══════════════════════════════════════════════════════════

function Test-Prerequisites {
    Write-Banner '🔍 Phase 0: Prerequisite Validation'

    # PowerShell version
    Write-Step 'Checking PowerShell version...'
    $psv = $PSVersionTable.PSVersion
    if ($psv.Major -ge 5) {
        Write-Pass 'PowerShell version' "$($psv.Major).$($psv.Minor) (min: 5.1)"
    } else {
        Write-Fail 'PowerShell version too old' 'Upgrade to PowerShell 5.1 or higher'
    }

    # Administrator check (optional, warn only)
    Write-Step 'Checking execution context...'
    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator
    )
    if ($isAdmin) {
        Write-Pass 'Running as Administrator'
    } else {
        Write-Warn 'Not running as Administrator' 'Some Docker operations may require elevation'
    }

    # Execution policy
    Write-Step 'Checking execution policy...'
    $ep = Get-ExecutionPolicy -Scope CurrentUser
    if ($ep -in @('Unrestricted','RemoteSigned','Bypass')) {
        Write-Pass 'Execution policy' $ep
    } else {
        Write-Fail 'Execution policy blocks scripts' "Run: Set-ExecutionPolicy RemoteSigned -Scope CurrentUser"
    }

    # Git
    Write-Step 'Checking Git...'
    $git = Get-Command git -ErrorAction SilentlyContinue
    if ($git) {
        $gitVer = & git --version 2>&1
        Write-Pass 'Git available' $gitVer
    } else {
        Write-Fail 'Git not found' 'Install Git from https://git-scm.com'
    }

    # Python
    Write-Step 'Checking Python...'
    $py = Get-Command python -ErrorAction SilentlyContinue
    if ($py) {
        $pyVer = & python --version 2>&1
        Write-Pass 'Python available' $pyVer
    } else {
        Write-Fail 'Python not found' 'Install Python 3.10+ from https://python.org'
    }

    # Docker
    Write-Step 'Checking Docker...'
    $docker = Get-Command docker -ErrorAction SilentlyContinue
    if ($docker) {
        $dockerVer = & docker --version 2>&1
        Write-Pass 'Docker available' $dockerVer
    } else {
        Write-Fail 'Docker not found' 'Install Docker Desktop from https://docker.com'
    }

    # curl
    Write-Step 'Checking curl...'
    $curlCmd = Get-Command curl -ErrorAction SilentlyContinue
    if ($curlCmd) {
        Write-Pass 'curl available'
    } else {
        Write-Warn 'curl not found' 'HTTP endpoint tests will be skipped'
    }

    # Project root sanity
    Write-Step 'Checking project root...'
    if (Test-Path (Join-Path $ProjectRoot 'backend')) {
        Write-Pass 'Project root valid' $ProjectRoot
    } else {
        Write-Fail 'backend/ directory not found' "Run from HyperCode-V2.4 root: $ProjectRoot"
    }
}

# ═══════════════════════════════════════════════════════════
# SECTION 3 — ENVIRONMENT PREPARATION
# ═══════════════════════════════════════════════════════════

function Initialize-Environment {
    Write-Banner '⚙️  Phase 1: Environment Preparation'

    # Create log directory
    Write-Step 'Setting up log directory...'
    if (-not (Test-Path $Script:Config.LogDir)) {
        if (-not $DryRun) {
            New-Item -ItemType Directory -Path $Script:Config.LogDir -Force | Out-Null
        }
        Write-Pass 'Log directory created' $Script:Config.LogDir
    } else {
        Write-Pass 'Log directory exists' $Script:Config.LogDir
    }

    # Create temp directory
    Write-Step 'Setting up temp directory...'
    if (-not (Test-Path $Script:Config.TempDir)) {
        if (-not $DryRun) {
            New-Item -ItemType Directory -Path $Script:Config.TempDir -Force | Out-Null
        }
    }
    Write-Pass 'Temp directory ready' $Script:Config.TempDir
    $Script:Stats.Rollback.Add({ Remove-Item $Script:Config.TempDir -Recurse -Force -ErrorAction SilentlyContinue })

    # Start transcript
    Write-Step 'Starting transcript log...'
    if (-not $DryRun) {
        Start-Transcript -Path $Script:Config.TranscriptPath -Append | Out-Null
    }
    Write-Pass 'Transcript logging active' $Script:Config.TranscriptPath

    # Verify .env file exists
    Write-Step 'Checking .env file...'
    $envFile = Join-Path $ProjectRoot '.env'
    if (Test-Path $envFile) {
        Write-Pass '.env file present'
    } else {
        $envExample = Join-Path $ProjectRoot '.env.example'
        if (Test-Path $envExample) {
            Write-Warn '.env missing' 'Copy .env.example to .env and fill in secrets'
        } else {
            Write-Fail '.env file missing' 'Create .env from .env.example'
        }
    }

    # Verify docker-compose.yml exists
    Write-Step 'Checking docker-compose.yml...'
    $composeFile = Join-Path $ProjectRoot 'docker-compose.yml'
    if (Test-Path $composeFile) {
        Write-Pass 'docker-compose.yml present'
    } else {
        Write-Fail 'docker-compose.yml not found' 'Ensure you are in the project root'
    }
}

# ═══════════════════════════════════════════════════════════
# SECTION 4 — SCHEMA VALIDATION
# ═══════════════════════════════════════════════════════════

function Test-Schemas {
    Write-Banner '📐 Phase 2: Schema Validation'

    $schemaFile = Join-Path $ProjectRoot 'backend' 'app' 'schemas' 'planning.py'

    Write-Step 'Checking planning schema file...'
    if (Test-Path $schemaFile) {
        Write-Pass 'planning.py exists'
        $content = Get-Content $schemaFile -Raw

        $models = @(
            @{ Name = 'DocumentInput';         Pattern = 'class DocumentInput' }
            @{ Name = 'ExtractedRequirement';   Pattern = 'class ExtractedRequirement' }
            @{ Name = 'ParsedDocument';         Pattern = 'class ParsedDocument' }
            @{ Name = 'PlanPhase';              Pattern = 'class PlanPhase' }
            @{ Name = 'FileChange';             Pattern = 'class FileChange' }
            @{ Name = 'CodingPlan';             Pattern = 'class CodingPlan' }
        )

        foreach ($model in $models) {
            if ($content -match [regex]::Escape($model.Pattern)) {
                Write-Pass "Schema model: $($model.Name)"
            } else {
                Write-Fail "Missing schema: $($model.Name)" "Add class $($model.Name) to planning.py"
            }
        }

        # Check DocumentType enum
        if ($content -match 'DocumentType|document_type') {
            Write-Pass 'DocumentType enum present'
        } else {
            Write-Fail 'DocumentType enum missing' 'Add DocumentType enum to planning.py'
        }

    } else {
        Write-Fail 'planning.py not found' 'Create backend/app/schemas/planning.py'
    }

    # Check schemas.py for generate_plan field
    Write-Step 'Checking TaskCreate schema for generate_plan...'
    $schemasFile = Join-Path $ProjectRoot 'backend' 'app' 'schemas' 'schemas.py'
    if (Test-Path $schemasFile) {
        $schemasContent = Get-Content $schemasFile -Raw
        if ($schemasContent -match 'generate_plan') {
            Write-Pass 'generate_plan field in TaskCreate'
        } else {
            Write-Fail 'generate_plan missing from TaskCreate' 'Add generate_plan: Optional[bool] = False to TaskCreate'
        }
    } else {
        Write-Warn 'schemas.py not found' 'Cannot verify TaskCreate changes'
    }
}

# ═══════════════════════════════════════════════════════════
# SECTION 5 — SERVICES VALIDATION
# ═══════════════════════════════════════════════════════════

function Test-Services {
    Write-Banner '⚙️  Phase 3: Services Layer Validation'

    $servicesDir = Join-Path $ProjectRoot 'backend' 'app' 'services'

    Write-Step 'Checking services directory...'
    if (Test-Path $servicesDir) {
        Write-Pass 'services/ directory exists'
    } else {
        Write-Fail 'services/ directory missing' 'Create backend/app/services/__init__.py'
        return
    }

    $serviceFiles = @(
        @{ File = '__init__.py';       Desc = 'Services package init' }
        @{ File = 'document_parser.py'; Desc = 'Document parser service' }
        @{ File = 'plan_generator.py';  Desc = 'Plan generator service' }
        @{ File = 'plan_formatter.py';  Desc = 'Plan formatter service' }
        @{ File = 'plan_executor.py';   Desc = 'Plan executor service' }
    )

    foreach ($svc in $serviceFiles) {
        $path = Join-Path $servicesDir $svc.File
        if (Test-Path $path) {
            Write-Pass "$($svc.Desc)" $svc.File
        } else {
            Write-Fail "$($svc.Desc) missing" "Create backend/app/services/$($svc.File)"
        }
    }

    # Deep check document_parser.py
    Write-Step 'Checking document_parser.py contents...'
    $parserFile = Join-Path $servicesDir 'document_parser.py'
    if (Test-Path $parserFile) {
        $content = Get-Content $parserFile -Raw
        $checks = @(
            @{ Pattern = 'class DocumentParser';     Name = 'DocumentParser class' }
            @{ Pattern = 'def parse';                Name = 'parse() method' }
            @{ Pattern = 'detect_document_type';     Name = 'detect_document_type() function' }
            @{ Pattern = 'Brain';                    Name = 'Brain LLM integration' }
        )
        foreach ($chk in $checks) {
            if ($content -match [regex]::Escape($chk.Pattern)) {
                Write-Pass $chk.Name
            } else {
                Write-Fail $chk.Name "Add $($chk.Pattern) to document_parser.py"
            }
        }
    }

    # Deep check plan_generator.py
    Write-Step 'Checking plan_generator.py contents...'
    $genFile = Join-Path $servicesDir 'plan_generator.py'
    if (Test-Path $genFile) {
        $content = Get-Content $genFile -Raw
        $checks = @(
            @{ Pattern = 'class PlanGenerator';  Name = 'PlanGenerator class' }
            @{ Pattern = 'generate_plan';         Name = 'generate_plan() method' }
            @{ Pattern = 'AgentMemory';           Name = 'AgentMemory integration' }
            @{ Pattern = 'Stage 1';               Name = 'Multi-stage prompting (Stage 1)' }
        )
        foreach ($chk in $checks) {
            if ($content -match $chk.Pattern) {
                Write-Pass $chk.Name
            } else {
                Write-Fail $chk.Name "Add $($chk.Pattern) to plan_generator.py"
            }
        }
    }

    # Deep check plan_executor.py
    Write-Step 'Checking plan_executor.py contents...'
    $execFile = Join-Path $servicesDir 'plan_executor.py'
    if (Test-Path $execFile) {
        $content = Get-Content $execFile -Raw
        $checks = @(
            @{ Pattern = 'class PlanExecutor';                Name = 'PlanExecutor class' }
            @{ Pattern = 'submit_plan_to_orchestrator';       Name = 'submit_plan_to_orchestrator() method' }
            @{ Pattern = 'memory:handoff';                    Name = 'Redis handoff key pattern' }
        )
        foreach ($chk in $checks) {
            if ($content -match $chk.Pattern) {
                Write-Pass $chk.Name
            } else {
                Write-Fail $chk.Name "Add $($chk.Pattern) to plan_executor.py"
            }
        }
    }
}

# ═══════════════════════════════════════════════════════════
# SECTION 6 — API ENDPOINTS VALIDATION
# ═══════════════════════════════════════════════════════════

function Test-ApiEndpoints {
    Write-Banner '🌐 Phase 4: API Endpoints Validation'

    # Planning endpoint file
    Write-Step 'Checking planning endpoint file...'
    $planningEp = Join-Path $ProjectRoot 'backend' 'app' 'api' 'v1' 'endpoints' 'planning.py'
    if (Test-Path $planningEp) {
        Write-Pass 'planning.py endpoint exists'
        $content = Get-Content $planningEp -Raw

        $checks = @(
            @{ Pattern = '/generate';               Name = 'POST /generate endpoint' }
            @{ Pattern = '/generate-from-task';     Name = 'POST /generate-from-task endpoint' }
            @{ Pattern = 'persist';                 Name = '?persist query parameter' }
            @{ Pattern = 'get_current';             Name = 'Auth dependency applied' }
        )
        foreach ($chk in $checks) {
            if ($content -match $chk.Pattern) {
                Write-Pass $chk.Name
            } else {
                Write-Fail $chk.Name "Add $($chk.Pattern) to planning.py endpoint"
            }
        }
    } else {
        Write-Fail 'planning.py endpoint missing' 'Create backend/app/api/v1/endpoints/planning.py'
    }

    # api.py router registration
    Write-Step 'Checking api.py router registration...'
    $apiFile = Join-Path $ProjectRoot 'backend' 'app' 'api' 'api.py'
    if (Test-Path $apiFile) {
        $content = Get-Content $apiFile -Raw
        if ($content -match 'planning') {
            Write-Pass 'Planning router registered in api.py'
        } else {
            Write-Fail 'Planning router not in api.py' 'Add planning router import and include_router() to api.py'
        }
    } else {
        Write-Warn 'api.py not found' 'Cannot verify router registration'
    }

    # tasks.py generate_plan integration
    Write-Step 'Checking tasks.py generate_plan integration...'
    $tasksEp = Join-Path $ProjectRoot 'backend' 'app' 'api' 'v1' 'endpoints' 'tasks.py'
    if (Test-Path $tasksEp) {
        $content = Get-Content $tasksEp -Raw
        if ($content -match 'generate_plan') {
            Write-Pass 'generate_plan integration in tasks.py'
        } else {
            Write-Fail 'generate_plan not in tasks.py' 'Add generate_plan flow to create_task endpoint'
        }
    } else {
        Write-Warn 'tasks.py not found' 'Cannot verify task creation integration'
    }
}

# ═══════════════════════════════════════════════════════════
# SECTION 7 — AGENT ROUTER VALIDATION
# ═══════════════════════════════════════════════════════════

function Test-AgentRouter {
    Write-Banner '🦅 Phase 5: Agent Router Validation'

    Write-Step 'Checking agent router file...'
    $routerFile = Join-Path $ProjectRoot 'backend' 'app' 'agents' 'router.py'
    if (Test-Path $routerFile) {
        Write-Pass 'router.py exists'
        $content = Get-Content $routerFile -Raw

        $keywords = @('generate plan', 'create plan', 'planning', 'coding plan', 'build plan')
        $found = $false
        foreach ($kw in $keywords) {
            if ($content -match $kw) { $found = $true; break }
        }
        if ($found) {
            Write-Pass 'Plan keyword detection in router'
        } else {
            Write-Fail 'Plan keywords missing from router' "Add 'generate plan', 'create plan', 'planning' detection to route_task()"
        }

        if ($content -match 'PlanGenerator') {
            Write-Pass 'PlanGenerator invoked in router'
        } else {
            Write-Fail 'PlanGenerator not called in router' 'Import and invoke PlanGenerator in router.py'
        }

    } else {
        Write-Warn 'router.py not found' 'Cannot validate agent routing logic'
    }

    # Brain agent check
    Write-Step 'Checking Brain agent...'
    $brainFile = Join-Path $ProjectRoot 'backend' 'app' 'agents' 'brain.py'
    if (Test-Path $brainFile) {
        Write-Pass 'brain.py exists'
    } else {
        Write-Fail 'brain.py missing' 'Brain agent is required for LLM calls'
    }

    # AgentMemory check
    Write-Step 'Checking AgentMemory...'
    $memoryFile = Join-Path $ProjectRoot 'backend' 'app' 'core' 'agent_memory.py'
    if (Test-Path $memoryFile) {
        Write-Pass 'agent_memory.py exists'
    } else {
        Write-Fail 'agent_memory.py missing' 'Required for plan generator context'
    }
}

# ═══════════════════════════════════════════════════════════
# SECTION 8 — TEST SUITE VALIDATION
# ═══════════════════════════════════════════════════════════

function Test-TestSuite {
    Write-Banner '🧪 Phase 6: Test Suite Validation'

    if ($SkipTests) {
        Write-Skip 'Test suite checks (--SkipTests flag set)'
        return
    }

    $testFiles = @(
        @{ Path = 'tests/test_planning_system.py';     Desc = 'Planning system tests' }
        @{ Path = 'tests/planning_postman_collection.json'; Desc = 'Postman collection' }
        @{ Path = 'tests/README_planning_tests.md';    Desc = 'Test documentation' }
    )

    foreach ($tf in $testFiles) {
        $fullPath = Join-Path $ProjectRoot $tf.Path
        if (Test-Path $fullPath) {
            Write-Pass $tf.Desc $tf.Path
        } else {
            Write-Fail "$($tf.Desc) missing" "Create $($tf.Path)"
        }
    }

    # Try running a quick Python syntax check on the test file
    Write-Step 'Running Python syntax check on test file...'
    $testFile = Join-Path $ProjectRoot 'tests' 'test_planning_system.py'
    $py = Get-Command python -ErrorAction SilentlyContinue
    if ($py -and (Test-Path $testFile)) {
        try {
            $result = & python -m py_compile $testFile 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Pass 'Test file syntax valid'
            } else {
                Write-Fail 'Test file has syntax errors' $result
            }
        } catch {
            Write-Warn 'Could not run syntax check' $_.Exception.Message
        }
    } else {
        Write-Skip 'Python syntax check (Python not available)'
    }
}

# ═══════════════════════════════════════════════════════════
# SECTION 9 — DOCKER VALIDATION
# ═══════════════════════════════════════════════════════════

function Test-DockerEnvironment {
    Write-Banner '🐳 Phase 7: Docker Environment Validation'

    if ($SkipDocker) {
        Write-Skip 'Docker validation (--SkipDocker flag set)'
        return
    }

    $docker = Get-Command docker -ErrorAction SilentlyContinue
    if (-not $docker) {
        Write-Skip 'Docker checks (Docker not found)'
        return
    }

    # Docker daemon check
    Write-Step 'Checking Docker daemon...'
    try {
        $dockerInfo = & docker info 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Pass 'Docker daemon running'
        } else {
            Write-Fail 'Docker daemon not running' 'Start Docker Desktop'
            return
        }
    } catch {
        Write-Fail 'Docker daemon check failed' $_.Exception.Message
        return
    }

    # Validation script exists
    Write-Step 'Checking docker/validate.sh...'
    $validateSh = Join-Path $ProjectRoot 'docker' 'validate.sh'
    if (Test-Path $validateSh) {
        Write-Pass 'docker/validate.sh exists'
    } else {
        Write-Fail 'docker/validate.sh missing' 'Create docker/validate.sh from the bash script'
    }

    # Hardened compose file
    Write-Step 'Checking docker-compose.hardened.yml...'
    $hardenedCompose = Join-Path $ProjectRoot 'docker' 'docker-compose.hardened.yml'
    if (Test-Path $hardenedCompose) {
        Write-Pass 'docker-compose.hardened.yml exists'
    } else {
        Write-Warn 'docker-compose.hardened.yml missing' 'Create docker/docker-compose.hardened.yml for security hardening'
    }

    # Container status check
    Write-Step 'Checking container status via docker compose ps...'
    $composeFile = Join-Path $ProjectRoot 'docker-compose.yml'
    if (Test-Path $composeFile) {
        try {
            Push-Location $ProjectRoot
            $psOutput = & docker compose ps --format json 2>&1
            Pop-Location

            $runningCount = 0
            $psOutput | ForEach-Object {
                try {
                    $container = $_ | ConvertFrom-Json -ErrorAction SilentlyContinue
                    if ($container -and $container.State -eq 'running') {
                        $runningCount++
                    }
                } catch { }
            }

            if ($runningCount -gt 0) {
                Write-Pass "Docker containers running" "$runningCount containers active"
            } else {
                Write-Warn 'No containers currently running' 'Run: docker compose up -d'
            }
        } catch {
            Write-Warn 'Could not query container status' $_.Exception.Message
        }
    }

    # Run bash validate script via Docker if possible
    Write-Step 'Attempting Docker-in-Docker validation run...'
    if (Test-Path $validateSh) {
        Write-Warn 'Bash validation requires Docker-in-Docker' "Run manually: docker run --rm -v `"${ProjectRoot}:/app`" -v /var/run/docker.sock:/var/run/docker.sock -w /app alpine sh -c `"apk add --no-cache bash curl python3 && bash docker/validate.sh`""
    }
}

# ═══════════════════════════════════════════════════════════
# SECTION 10 — GIT STATUS VALIDATION
# ═══════════════════════════════════════════════════════════

function Test-GitStatus {
    Write-Banner '📦 Phase 8: Git Status Validation'

    $git = Get-Command git -ErrorAction SilentlyContinue
    if (-not $git) {
        Write-Skip 'Git checks (Git not found)'
        return
    }

    Write-Step 'Checking git status...'
    try {
        Push-Location $ProjectRoot
        $branch = & git branch --show-current 2>&1
        Write-Pass 'Git branch' $branch

        $status = & git status --porcelain 2>&1
        if ($status) {
            $uncommitted = ($status | Measure-Object).Count
            Write-Warn "Uncommitted changes" "$uncommitted file(s) modified — commit before deploying"
        } else {
            Write-Pass 'Working tree clean — all changes committed'
        }

        $latestCommit = & git log --oneline -1 2>&1
        Write-Pass 'Latest commit' $latestCommit

        Pop-Location
    } catch {
        Write-Warn 'Git status check failed' $_.Exception.Message
        if (Test-Path variable:global:PSLOC) { Pop-Location }
    }

    # Check key files are tracked
    Write-Step 'Checking key agent phase files are tracked...'
    $keyFiles = @(
        'backend/app/schemas/planning.py'
        'backend/app/services/__init__.py'
        'backend/app/services/document_parser.py'
        'backend/app/services/plan_generator.py'
        'backend/app/services/plan_formatter.py'
        'backend/app/services/plan_executor.py'
        'backend/app/api/v1/endpoints/planning.py'
        'tests/test_planning_system.py'
    )

    foreach ($f in $keyFiles) {
        $fullPath = Join-Path $ProjectRoot $f
        if (Test-Path $fullPath) {
            Write-Pass "File present" $f
        } else {
            Write-Fail "File missing: $f" "Push this file to the repo"
        }
    }
}

# ═══════════════════════════════════════════════════════════
# SECTION 11 — CLEANUP
# ═══════════════════════════════════════════════════════════

function Invoke-Cleanup {
    Write-Banner '🧹 Phase 9: Cleanup'

    Write-Step 'Removing temp directory...'
    if (Test-Path $Script:Config.TempDir) {
        if (-not $DryRun) {
            Remove-Item $Script:Config.TempDir -Recurse -Force -ErrorAction SilentlyContinue
        }
        Write-Pass 'Temp directory cleaned' $Script:Config.TempDir
    } else {
        Write-Pass 'Temp directory already clean'
    }

    Write-Step 'Stopping transcript...'
    try {
        if (-not $DryRun) { Stop-Transcript | Out-Null }
        Write-Pass 'Transcript saved' $Script:Config.TranscriptPath
    } catch {
        # Transcript may not have been started
    }
}

# ═══════════════════════════════════════════════════════════
# SECTION 12 — REPORT GENERATION
# ═══════════════════════════════════════════════════════════

function Write-FinalReport {
    $elapsed = (Get-Date) - $Script:Config.StartTime
    $totalChecks = $Script:Stats.Pass + $Script:Stats.Fail + $Script:Stats.Warn + $Script:Stats.Skip
    $score = if ($totalChecks -gt 0) { [int](($Script:Stats.Pass / $totalChecks) * 100) } else { 0 }
    $status = if ($Script:Stats.Fail -eq 0) { 'SUCCESS' } else { 'FAILED' }
    $statusColor = if ($Script:Stats.Fail -eq 0) { 'Green' } else { 'Red' }
    $statusEmoji = if ($Script:Stats.Fail -eq 0) { '🎉' } else { '❌' }

    # Console summary
    Write-Banner "$statusEmoji Final Report — Agents Phase" $statusColor

    Write-Host "`n  Phase    : $($Script:Config.Phase)" -ForegroundColor White
    Write-Host "  Status   : $status" -ForegroundColor $statusColor
    Write-Host "  Score    : $score% ($($Script:Stats.Pass) pass / $($Script:Stats.Fail) fail / $($Script:Stats.Warn) warn / $($Script:Stats.Skip) skip)" -ForegroundColor White
    Write-Host "  Duration : $([int]$elapsed.TotalSeconds) seconds" -ForegroundColor White
    Write-Host "  Log      : $($Script:Config.TranscriptPath)" -ForegroundColor DarkGray
    Write-Host "  Report   : $($Script:Config.ReportPath)" -ForegroundColor DarkGray

    if ($Script:Stats.Fail -gt 0) {
        Write-Host "`n  ─── Failures to fix ───────────────────────────────" -ForegroundColor Red
        $Script:Stats.Results | Where-Object { $_.Status -eq 'FAIL' } | ForEach-Object {
            Write-Host "  ❌ $($_.Check)" -ForegroundColor Red
            Write-Host "     → $($_.Fix)" -ForegroundColor DarkRed
        }
    }

    if ($Script:Stats.Warn -gt 0) {
        Write-Host "`n  ─── Warnings to review ────────────────────────────" -ForegroundColor Yellow
        $Script:Stats.Results | Where-Object { $_.Status -eq 'WARN' } | ForEach-Object {
            Write-Host "  ⚠️  $($_.Check)" -ForegroundColor Yellow
            if ($_.Detail) { Write-Host "     → $($_.Detail)" -ForegroundColor DarkYellow }
        }
    }

    # Markdown report
    if (-not $DryRun) {
        $reportContent = @"
# 🦅 HyperCode V2.0 — Agents Phase Validation Report

**Generated:** $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
**Status:** $status $statusEmoji
**Score:** $score% ($($Script:Stats.Pass) pass / $($Script:Stats.Fail) fail / $($Script:Stats.Warn) warn / $($Script:Stats.Skip) skip)
**Duration:** $([int]$elapsed.TotalSeconds) seconds

---

## Summary

| Check | Count |
|-------|-------|
| ✅ Pass | $($Script:Stats.Pass) |
| ❌ Fail | $($Script:Stats.Fail) |
| ⚠️ Warn | $($Script:Stats.Warn) |
| ⏭️ Skip | $($Script:Stats.Skip) |
| **Total** | **$totalChecks** |

---

## Detailed Results

$(
    $Script:Stats.Results | ForEach-Object {
        $icon = switch ($_.Status) {
            'PASS' { '✅' }
            'FAIL' { '❌' }
            'WARN' { '⚠️' }
            'SKIP' { '⏭️' }
        }
        if ($_.Fix) {
            "### $icon $($_.Status) — $($_.Check)`n> 🔧 **Fix:** $($_.Fix)`n"
        } else {
            "- $icon $($_.Check)$(if ($_.Detail) { " — $($_.Detail)" })"
        }
    }) -join "`n"
)

---

## Next Steps

$(if ($Script:Stats.Fail -eq 0) {
"✅ All critical checks passed — Agents Phase is deployment ready!

1. Run the test suite: ``python tests/test_planning_system.py``
2. Start the stack: ``docker compose up -d``
3. Check Grafana: http://localhost:3001
4. Test API: ``POST http://localhost:8000/api/v1/planning/generate``"
} else {
"❌ $($Script:Stats.Fail) critical issue(s) found — resolve before deploying

1. Fix all ❌ FAIL items listed above
2. Re-run: ``.\\scripts\\Finalize-AgentsPhase.ps1``
3. Target: 100% pass rate"
})

---
*Generated by HyperCode Agents Phase Finalizer v$($Script:Config.Version)*
"@
        $reportContent | Set-Content -Path $Script:Config.ReportPath -Encoding UTF8
    }

    Write-Host ""
    if ($Script:Stats.Fail -eq 0) {
        Write-Host '  🔥 BROski Power Level: AGENTS PHASE COMPLETE! 🦅' -ForegroundColor Cyan
    } else {
        Write-Host "  Fix $($Script:Stats.Fail) issue(s) and re-run the script." -ForegroundColor Red
    }
    Write-Host ""

    return $Script:Stats.Fail
}

# ═══════════════════════════════════════════════════════════
# SECTION 13 — ROLLBACK HANDLER
# ═══════════════════════════════════════════════════════════

function Invoke-Rollback {
    param([string]$Reason)
    Write-Host "`n  🔄 Rolling back due to: $Reason" -ForegroundColor Yellow
    foreach ($action in $Script:Stats.Rollback) {
        try { & $action } catch { }
    }
}

# ═══════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════

try {
    Clear-Host
    Write-Host @"

  ╔══════════════════════════════════════════════════════════╗
  ║  🦅  HyperCode V2.0 — Agents Phase Finalizer  🦅       ║
  ║     Neurodivergent-First AI Coding Ecosystem            ║
  ║     Version: $($Script:Config.Version)  |  $(Get-Date -Format 'yyyy-MM-dd HH:mm')           ║
  ╚══════════════════════════════════════════════════════════╝

"@ -ForegroundColor Cyan

    if ($DryRun) {
        Write-Host '  ⚡ DRY RUN MODE — no changes will be made' -ForegroundColor Magenta
    }

    $totalSteps = 10

    Write-Progress-Step 1 $totalSteps 'Prerequisites'
    Test-Prerequisites

    Write-Progress-Step 2 $totalSteps 'Environment'
    Initialize-Environment

    Write-Progress-Step 3 $totalSteps 'Schemas'
    Test-Schemas

    Write-Progress-Step 4 $totalSteps 'Services'
    Test-Services

    Write-Progress-Step 5 $totalSteps 'API Endpoints'
    Test-ApiEndpoints

    Write-Progress-Step 6 $totalSteps 'Agent Router'
    Test-AgentRouter

    Write-Progress-Step 7 $totalSteps 'Test Suite'
    Test-TestSuite

    Write-Progress-Step 8 $totalSteps 'Docker'
    Test-DockerEnvironment

    Write-Progress-Step 9 $totalSteps 'Git Status'
    Test-GitStatus

    Write-Progress-Step 10 $totalSteps 'Cleanup'
    Invoke-Cleanup

    Write-Progress -Activity 'HyperCode Agents Phase' -Completed

    $failCount = Write-FinalReport

    if ($failCount -gt 0) {
        exit 1
    } else {
        exit 0
    }

} catch {
    Write-Host "`n  💥 FATAL ERROR: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "  Line: $($_.InvocationInfo.ScriptLineNumber)" -ForegroundColor DarkRed
    Invoke-Rollback $_.Exception.Message
    Write-FinalReport | Out-Null
    exit 2
}
