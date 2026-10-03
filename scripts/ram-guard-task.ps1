<#
.SYNOPSIS
  Install / remove / inspect the Windows Task Scheduler job that keeps the HOST RAM-guard signal fresh.

.DESCRIPTION
  The throttle-agent (in Docker) cannot see the Windows host, so a small host-side script measures it and writes
  ram-signal\ram.json every 30 s. This job keeps that script running:
    - as YOU (the current user), at YOUR logon, hidden (pythonw), NO elevation (RunLevel Limited)
    - never two copies (MultipleInstances = IgnoreNew); restarts up to 3 times, 1 minute apart, if it dies
    - no time limit; allowed on battery
  The script it runs only MEASURES memory (host free, Windows compression, WSL available). It never stops or starts
  anything. If it ever stops, the signal file goes stale -> the throttle-agent reads UNKNOWN -> it does nothing.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\ram-guard-task.ps1 -Action install
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\ram-guard-task.ps1 -Action status
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\ram-guard-task.ps1 -Action uninstall
#>
param(
    [Parameter(Mandatory = $true)][ValidateSet('install', 'uninstall', 'status', 'start', 'stop')][string]$Action,
    [int]$IntervalSeconds = 30
)
$ErrorActionPreference = 'Stop'

$TaskName = 'HyperCode RAM Guard Signal'
$TaskPath = '\HyperCode\'
$Repo = Split-Path -Parent $PSScriptRoot
$Out = Join-Path $Repo 'ram-signal\ram.json'
$Script = Join-Path $Repo 'scripts\ram_guard.py'

function Get-Pythonw {
    $py = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
    if (-not $py) { throw 'python.exe not found on PATH' }
    $w = Join-Path (Split-Path $py) 'pythonw.exe'
    if (-not (Test-Path $w)) { throw "pythonw.exe not found next to $py" }
    return $w
}

function Get-Existing { Get-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath -ErrorAction SilentlyContinue }

switch ($Action) {
    'install' {
        if (-not (Test-Path $Script)) { throw "missing $Script" }
        New-Item -ItemType Directory -Force -Path (Split-Path $Out) | Out-Null
        $me = "$env:USERDOMAIN\$env:USERNAME"
        $arg = "`"$Script`" --loop $IntervalSeconds --skip-docker --out `"$Out`""
        $act = New-ScheduledTaskAction -Execute (Get-Pythonw) -Argument $arg -WorkingDirectory $Repo
        $trg = New-ScheduledTaskTrigger -AtLogOn -User $me
        $set = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
            -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) `
            -ExecutionTimeLimit ([TimeSpan]::Zero)
        $pri = New-ScheduledTaskPrincipal -UserId $me -LogonType Interactive -RunLevel Limited
        Register-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath -Action $act -Trigger $trg -Settings $set `
            -Principal $pri -Force `
            -Description 'HyperCode: host-side RAM guard (read-only) writing ram-signal\ram.json for the throttle-agent. Remove with scripts\ram-guard-task.ps1 -Action uninstall' | Out-Null
        Write-Output "installed: $TaskPath$TaskName (runs as $me at logon, hidden, no elevation)"
        Write-Output "command:   $(Get-Pythonw) $arg"
    }
    'uninstall' {
        if (Get-Existing) {
            Stop-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath -ErrorAction SilentlyContinue
            Unregister-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath -Confirm:$false
            Write-Output "removed: $TaskPath$TaskName"
        } else { Write-Output "not installed: $TaskPath$TaskName" }
    }
    'start' { Start-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath; Write-Output 'started' }
    'stop'  { Stop-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath; Write-Output 'stopped' }
    'status' {
        $t = Get-Existing
        if (-not $t) { Write-Output "not installed: $TaskPath$TaskName"; break }
        $i = Get-ScheduledTaskInfo -TaskName $TaskName -TaskPath $TaskPath
        Write-Output "task:        $TaskPath$TaskName"
        Write-Output "state:       $($t.State)"
        Write-Output "last run:    $($i.LastRunTime)  (result 0x$('{0:X}' -f $i.LastTaskResult))"
        Write-Output "run as:      $($t.Principal.UserId) ($($t.Principal.RunLevel))"
        if (Test-Path $Out) {
            $age = [int]((Get-Date) - (Get-Item $Out).LastWriteTime).TotalSeconds
            $overall = (Get-Content $Out -Raw | ConvertFrom-Json).overall
            Write-Output "signal file: $Out  age ${age}s  overall $overall"
        } else { Write-Output "signal file: not written yet ($Out)" }
    }
}
