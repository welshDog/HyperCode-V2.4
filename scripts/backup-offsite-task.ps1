<#
.SYNOPSIS
  Install / remove / inspect the Windows Task Scheduler job that runs the daily off-machine copy (second-disk mirror + AES-256 archive to the Google Drive folder).

.DESCRIPTION
  Runs scripts\offsite_copy.ps1 once a day (default 12:15, 30 min after the Postgres backup, after the stores backup):
    - as YOU, hidden, NO elevation (RunLevel Limited) - same model as the Postgres and RAM-guard tasks
    - StartWhenAvailable: if the PC was off at the trigger time it runs at the next opportunity
    - never two copies (MultipleInstances = IgnoreNew); 30 min time limit; allowed on battery
  Exit code 2 = encrypted copy is queued because Google Drive for Desktop is not signed in yet (task shows non-zero until it is).
  Output is appended to backups\offsite.log; the task's "last result" mirrors the backup script's exit code.
  Passphrase: secrets\offsite_backup_passphrase.txt - keep a copy in your password manager.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\backup-offsite-task.ps1 -Action install
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\backup-offsite-task.ps1 -Action status
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\backup-offsite-task.ps1 -Action start      # run now
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\backup-offsite-task.ps1 -Action uninstall
#>
param(
    [Parameter(Mandatory = $true)][ValidateSet('install', 'uninstall', 'status', 'start')][string]$Action,
    [string]$At = '12:30'
)
$ErrorActionPreference = 'Stop'

$TaskName = 'HyperCode Offsite Copy'
$TaskPath = '\HyperCode\'
$Repo      = Split-Path -Parent $PSScriptRoot
$Script    = Join-Path $Repo 'scripts\offsite_copy.ps1'
$BackupDir = Join-Path $Repo 'backups'
$Log       = Join-Path $BackupDir 'offsite.log'

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
            -Description 'HyperCode: daily off-machine copy: second-disk mirror + encrypted archive to the Google Drive folder. Remove with scripts\backup-offsite-task.ps1 -Action uninstall' | Out-Null
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
        $local = 'C:\HyperCodeBackups'
        $pend = Get-ChildItem (Join-Path $local 'offsite-pending') -Filter 'hypercode_*.7z' -ErrorAction SilentlyContinue
        $nl = Get-ChildItem (Join-Path $local 'postgres') -Filter 'backup_*.dump' -ErrorAction SilentlyContinue | Sort-Object Name -Descending | Select-Object -First 1
        if ($nl) { Write-Output ("second disk: newest dump {0}  age {1} h" -f $nl.Name, [math]::Round(((Get-Date) - $nl.LastWriteTime).TotalHours, 1)) } else { Write-Output 'second disk: nothing yet' }
        $drive = $null
        foreach ($d in (Get-PSDrive -PSProvider FileSystem).Name) { $p = "${d}:\My Drive\HyperCode-Backups"; if (Test-Path $p) { $drive = $p } }
        if ($drive) {
            $n = Get-ChildItem $drive -Filter 'hypercode_*.7z' | Sort-Object Name -Descending
            Write-Output ("google drive: {0} encrypted archive(s) in {1}; newest {2}" -f @($n).Count, $drive, $(if ($n) { $n[0].Name } else { '-' }))
        } else { Write-Output 'google drive: NOT FOUND - Drive for Desktop not signed in' }
        Write-Output ("queued (encrypted, waiting for Drive): {0}" -f @($pend).Count)
    }
}

