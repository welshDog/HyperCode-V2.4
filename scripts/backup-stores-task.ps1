<#
.SYNOPSIS
  Install / remove / inspect the Windows Task Scheduler job that runs the daily Redis + MinIO + Chroma backup.

.DESCRIPTION
  Runs scripts\backup_data_stores.ps1 once a day (default 12:15, 15 min after the Postgres backup so they never overlap):
    - as YOU, hidden, NO elevation (RunLevel Limited) - same model as the Postgres and RAM-guard tasks
    - StartWhenAvailable: if the PC was off at the trigger time it runs at the next opportunity
    - never two copies (MultipleInstances = IgnoreNew); 30 min time limit; allowed on battery
  NOTE: the Chroma part stops the chroma container for a few seconds (cold copy for consistency) and always restarts it.
  Output is appended to backups\stores\backup.log; the task's "last result" mirrors the backup script's exit code.
  Restore proof: scripts\restore_drill_stores.ps1

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\backup-stores-task.ps1 -Action install
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\backup-stores-task.ps1 -Action status
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\backup-stores-task.ps1 -Action start      # run now
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\backup-stores-task.ps1 -Action uninstall
#>
param(
    [Parameter(Mandatory = $true)][ValidateSet('install', 'uninstall', 'status', 'start')][string]$Action,
    [string]$At = '12:15'
)
$ErrorActionPreference = 'Stop'

$TaskName = 'HyperCode Stores Backup'
$TaskPath = '\HyperCode\'
$Repo      = Split-Path -Parent $PSScriptRoot
$Script    = Join-Path $Repo 'scripts\backup_data_stores.ps1'
$BackupDir = Join-Path $Repo 'backups\stores'
$Log       = Join-Path $BackupDir 'backup.log'

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
            -Description 'HyperCode: daily Redis+MinIO+Chroma backup to backups\stores (Chroma stopped for seconds). Remove with scripts\backup-stores-task.ps1 -Action uninstall' | Out-Null
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
        $newest = Get-ChildItem $BackupDir -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending | Select-Object -First 1
        if ($newest) {
            $age = [math]::Round(((Get-Date) - $newest.LastWriteTime).TotalHours, 1)
            $files = (Get-ChildItem $newest.FullName -File | Measure-Object).Count
            Write-Output ("newest set:  {0}  {1} files  age {2} h" -f $newest.Name, $files, $age)
            if ($age -gt 26) { Write-Output 'WARNING: newest backup is older than 26 h' }
        } else { Write-Output 'newest set:  none' }
    }
}
