<#
.SYNOPSIS
  Install / remove / inspect the Windows Task Scheduler job that runs the daily Postgres backup.

.DESCRIPTION
  Runs scripts\backup_postgres.ps1 once a day (default 12:00):
    - as YOU, hidden, NO elevation (RunLevel Limited) - same model as the RAM-guard task
    - StartWhenAvailable: if the PC was off at 12:00 it runs at the next opportunity
    - never two copies (MultipleInstances = IgnoreNew); 30 min time limit; allowed on battery
  Output is appended to backups\postgres\backup.log and the task's "last result" mirrors the
  backup script's exit code, so a failed backup is visible in `-Action status` (and goes stale in age).
  The backup is read-only against the database (pg_dump). Restore proof: scripts\restore_drill_postgres.ps1

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\backup-postgres-task.ps1 -Action install
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\backup-postgres-task.ps1 -Action status
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\backup-postgres-task.ps1 -Action start      # run now
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\backup-postgres-task.ps1 -Action uninstall
#>
param(
    [Parameter(Mandatory = $true)][ValidateSet('install', 'uninstall', 'status', 'start')][string]$Action,
    [string]$At = '12:00'
)
$ErrorActionPreference = 'Stop'

$TaskName = 'HyperCode Postgres Backup'
$TaskPath = '\HyperCode\'
$Repo   = Split-Path -Parent $PSScriptRoot
$Script = Join-Path $Repo 'scripts\backup_postgres.ps1'
$BackupDir = Join-Path $Repo 'backups\postgres'
$Log    = Join-Path $BackupDir 'backup.log'

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
        $trg = New-ScheduledTaskTrigger -Daily -At $At
        $set = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
            -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
        $pri = New-ScheduledTaskPrincipal -UserId $me -LogonType Interactive -RunLevel Limited
        Register-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath -Action $act -Trigger $trg -Settings $set `
            -Principal $pri -Force `
            -Description 'HyperCode: daily Postgres pg_dump backup (read-only) to backups\postgres. Remove with scripts\backup-postgres-task.ps1 -Action uninstall' | Out-Null
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
        $newest = Get-ChildItem $BackupDir -Filter 'backup_*.dump' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($newest) {
            $age = [math]::Round(((Get-Date) - $newest.LastWriteTime).TotalHours, 1)
            Write-Output ("newest dump: {0}  {1:N1} MB  age {2} h" -f $newest.Name, ($newest.Length / 1MB), $age)
            if ($age -gt 26) { Write-Output 'WARNING: newest backup is older than 26 h' }
        } else { Write-Output 'newest dump: none' }
    }
}
