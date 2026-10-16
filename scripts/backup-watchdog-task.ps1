<#
.SYNOPSIS
  Install / remove / inspect the Windows Task Scheduler job that runs the backup watchdog: checks the 3 backup jobs + freshness and alerts to Discord/toast on problems.

.DESCRIPTION
  Runs scripts\backup_watchdog.ps1 once a day (default 12:15, 45 min after the Postgres backup (after the 12:00/12:15/12:30 jobs), and again at 18:00):
    - as YOU, hidden, NO elevation (RunLevel Limited) - same model as the Postgres and RAM-guard tasks
    - StartWhenAvailable: if the PC was off at the trigger time it runs at the next opportunity
    - never two copies (MultipleInstances = IgnoreNew); 30 min time limit; allowed on battery
  Exit code 1 = it found (and alerted on) a problem; 0 = all healthy.
  Output is appended to backups\offsite.log; the task's "last result" mirrors the backup script's exit code.
  Test the alert path any time: scripts\backup_watchdog.ps1 -Test   (dry run: -DryRun)

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\backup-watchdog-task.ps1 -Action install
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\backup-watchdog-task.ps1 -Action status
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\backup-watchdog-task.ps1 -Action start      # run now
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\backup-watchdog-task.ps1 -Action uninstall
#>
param(
    [Parameter(Mandatory = $true)][ValidateSet('install', 'uninstall', 'status', 'start')][string]$Action,
    [string]$At = '13:00'
)
$ErrorActionPreference = 'Stop'

$TaskName = 'HyperCode Backup Watchdog'
$TaskPath = '\HyperCode\'
$Repo      = Split-Path -Parent $PSScriptRoot
$Script    = Join-Path $Repo 'scripts\backup_watchdog.ps1'
$BackupDir = Join-Path $Repo 'backups'
$Log       = Join-Path $BackupDir 'watchdog-run.log'

function Get-Existing { Get-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath -ErrorAction SilentlyContinue }

switch ($Action) {
    'install' {
        if (-not (Test-Path $Script)) { throw "missing $Script" }
        New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
        $me  = "$env:USERDOMAIN\$env:USERNAME"
        # One UTF-8 writer for everything: powershell.exe 5.1's `*>>` would write UTF-16 and garble the log.
        $cmd = @"
`$ts = Get-Date -Format s
(& '$Script' *>&1 | Out-String -Stream | ForEach-Object { "`$ts `$_" }) | Out-File -Append -Encoding utf8 '$Log'
exit `$LASTEXITCODE
"@
        # -EncodedCommand (base64 UTF-16) sidesteps every layer of nested-quote escaping.
        $enc = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($cmd))
        $arg = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -EncodedCommand $enc"
        $act = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arg -WorkingDirectory $Repo
        $trg = @((New-ScheduledTaskTrigger -Daily -At $At), (New-ScheduledTaskTrigger -Daily -At '18:00'))
        $set = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
            -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
        $pri = New-ScheduledTaskPrincipal -UserId $me -LogonType Interactive -RunLevel Limited
        Register-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath -Action $act -Trigger $trg -Settings $set `
            -Principal $pri -Force `
            -Description 'HyperCode: backup watchdog: alerts (Discord health webhook + toast) when a backup fails or goes stale. Remove with scripts\backup-watchdog-task.ps1 -Action uninstall' | Out-Null
        Write-Output "installed: $TaskPath$TaskName (daily $At as $me, hidden, no elevation)"
        Write-Output "log:       $Log"
    }
    'uninstall' {
        if (Get-Existing) {
            Unregister-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath -Confirm:$false
            Write-Output "removed: $TaskPath$TaskName"
        } else { Write-Output "not installed: $TaskPath$TaskName" }
    }
    'start' { Start-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath; Write-Output 'started (see -Action status / backup.log)' }
    'status' {
        $t = Get-Existing
        if (-not $t) { Write-Output "not installed: $TaskPath$TaskName"; break }
        $i = Get-ScheduledTaskInfo -TaskName $TaskName -TaskPath $TaskPath
        Write-Output "task:        $TaskPath$TaskName"
        Write-Output "state:       $($t.State)"
        Write-Output "next run:    $($i.NextRunTime)"
        Write-Output "last run:    $($i.LastRunTime)  (result 0x$('{0:X}' -f $i.LastTaskResult); 0x0 = ok)"
        $st = Join-Path $BackupDir 'watchdog-state.json'
        if (Test-Path $st) {
            $s = Get-Content $st -Raw | ConvertFrom-Json
            if ($s.problems) { Write-Output "open alert:  $($s.problems)  (last sent $($s.lastSent))" } else { Write-Output 'open alert:  none (all healthy at last check)' }
        } else { Write-Output 'open alert:  no state yet (has not run)' }
        Write-Output 'live check:  run  scripts\backup_watchdog.ps1 -DryRun  for a no-send report'
    }
}


