# 🦅 Agents Phase — PowerShell Finalizer

## Quick Start

```powershell
# From repo root
.\scripts\Invoke-AgentsPhase.ps1
```

## Options

| Flag | What it does |
|------|-------------|
| `-ProjectRoot <path>` | Set repo root (default: current dir) |
| `-BaseUrl <url>` | API URL for smoke tests (default: http://localhost:8000) |
| `-SkipDocker` | Skip Docker container checks |
| `-SkipTests` | Skip Python test suite |
| `-Rollback` | Roll back last failed run via saved git state |

## Examples

```powershell
# Full validation
.\scripts\Invoke-AgentsPhase.ps1

# Without Docker (if not running)
.\scripts\Invoke-AgentsPhase.ps1 -SkipDocker

# Custom API URL
.\scripts\Invoke-AgentsPhase.ps1 -BaseUrl http://myserver:8000

# Quick syntax check only (no docker/tests)
.\scripts\Invoke-AgentsPhase.ps1 -SkipDocker -SkipTests

# Roll back if something went wrong
.\scripts\Invoke-AgentsPhase.ps1 -Rollback
```

## What It Checks

| Step | Phase | Checks |
|------|-------|--------|
| 1 | Prerequisites | PS 5.1+, admin rights, Python, Git, Docker daemon |
| 2 | Environment | Log dirs, rollback state, transcript |
| 3 | Required Files | All 11 Agents phase output files exist |
| 4 | Python Syntax | py_compile on every new .py file |
| 5 | Git Status | Files tracked, committed, remote sync |
| 6 | Docker Stack | Containers running, validate.sh via Alpine |
| 7 | API Endpoints | 5 smoke tests against live backend |
| 8 | Test Suite | runs test_planning_system.py |
| 9 | Cleanup | .pyc, __pycache__, .tmp removal |

## Output

- **Console**: Coloured PASS/FAIL/WARN output
- **Log file**: `logs/agents-phase_<timestamp>.log`
- **Report**: `agents-phase-report_<timestamp>.md`
- **Exit code**: `0` = all pass, `>0` = number of failures

## Fixing Execution Policy Errors

```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```
