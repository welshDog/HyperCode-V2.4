# Off-machine copy of the newest backups.
#   A) plain copy to a SECOND DISK (default C:\HyperCodeBackups), additive (never purges on source loss),
#      pruned to the newest $KeepLocal sets.
#   B) AES-256 encrypted 7z (headers encrypted too) of the newest Postgres dump + stores set, placed in the
#      Google Drive folder so Drive for Desktop syncs ciphertext only. If Drive isn't available yet the
#      archive waits in <LocalCopyDir>\offsite-pending and is moved over on the next run (exit code 2 = "waiting").
# Usage: ./scripts/offsite_copy.ps1 [-DriveDir "G:\My Drive\HyperCode-Backups"] [-LocalCopyDir C:\HyperCodeBackups]
# Passphrase: secrets\offsite_backup_passphrase.txt (generated once, never printed). KEEP A COPY IN YOUR PASSWORD
# MANAGER - without it the encrypted archives cannot be opened, e.g. after losing this PC.
# Decrypt: 7z x <archive.7z> -p<passphrase>
param(
    [string]$DriveDir,
    [string]$LocalCopyDir = 'C:\HyperCodeBackups',
    [int]$KeepLocal = 14,
    [int]$KeepDrive = 7
)
$ErrorActionPreference = 'Stop'
$Repo    = Split-Path -Parent $PSScriptRoot
$Backups = Join-Path $Repo 'backups'
$PassFile = Join-Path $Repo 'secrets\offsite_backup_passphrase.txt'
$code = 0
function Say($m, $c = 'Gray') { Write-Host $m -ForegroundColor $c }

# ---- sanity: need a fresh source ----
# Only COMPLETED sources: a dump is complete once its .sha256 exists; a stores set once SHA256SUMS + manifest.json
# exist (written last). Otherwise an overlapping backup run could get archived half-written.
$pgDump = Get-ChildItem (Join-Path $Backups 'postgres') -Filter 'backup_*.dump' -ErrorAction SilentlyContinue |
    Where-Object { Test-Path "$($_.FullName).sha256" } | Sort-Object Name -Descending | Select-Object -First 1
$stSet  = Get-ChildItem (Join-Path $Backups 'stores') -Directory -ErrorAction SilentlyContinue |
    Where-Object { (Test-Path (Join-Path $_.FullName 'SHA256SUMS')) -and (Test-Path (Join-Path $_.FullName 'manifest.json')) } |
    Sort-Object Name -Descending | Select-Object -First 1
if (-not $pgDump -or -not $stSet) { Say 'FAIL: no COMPLETED source backups found (run the backup scripts first)' Red; exit 1 }
Say ("source: postgres {0}  stores {1}" -f $pgDump.Name, $stSet.Name)

# ---- A) second-disk copy ----
New-Item -ItemType Directory -Force -Path $LocalCopyDir | Out-Null
robocopy $Backups $LocalCopyDir /E /XO /R:2 /W:2 /NFL /NDL /NJH /NJS /NP /XD offsite-pending | Out-Null
if ($LASTEXITCODE -ge 8) { Say "FAIL: robocopy exit $LASTEXITCODE" Red; exit 1 }
foreach ($sub in 'postgres') {
    Get-ChildItem (Join-Path $LocalCopyDir $sub) -Filter 'backup_*.dump' | Sort-Object Name -Descending | Select-Object -Skip $KeepLocal | ForEach-Object {
        Remove-Item -LiteralPath $_.FullName -Force; Remove-Item -LiteralPath "$($_.FullName).sha256" -Force -ErrorAction SilentlyContinue }
}
Get-ChildItem (Join-Path $LocalCopyDir 'stores') -Directory | Sort-Object Name -Descending | Select-Object -Skip $KeepLocal | Remove-Item -Recurse -Force
# verify the copy by checksum of the newest dump
$a = (Get-FileHash $pgDump.FullName -Algorithm SHA256).Hash
$b = (Get-FileHash (Join-Path $LocalCopyDir "postgres\$($pgDump.Name)") -Algorithm SHA256).Hash
if ($a -ne $b) { Say 'FAIL: second-disk copy checksum mismatch' Red; exit 1 }
Say "A) second disk OK: $LocalCopyDir (checksum verified)" Green

# ---- B) encrypted archive ----
$7z = (Get-Command 7z -ErrorAction SilentlyContinue).Source
if (-not $7z) { Say 'FAIL: 7z not found on PATH' Red; exit 1 }
if (-not (Test-Path $PassFile)) {
    $bytes = New-Object byte[] 32; [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    ('H' + [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+','-').Replace('/','_')) | Set-Content -NoNewline -Encoding ascii $PassFile
    Say "generated NEW passphrase at $PassFile - COPY IT TO YOUR PASSWORD MANAGER NOW" Yellow
}
$pw = (Get-Content $PassFile -Raw).Trim()

$pending = Join-Path $LocalCopyDir 'offsite-pending'
New-Item -ItemType Directory -Force -Path $pending | Out-Null
$name = "hypercode_{0}_{1}.7z" -f ($pgDump.BaseName -replace 'backup_',''), $stSet.Name

# find the Drive folder if not given
if (-not $DriveDir) {
    $cands = @()
    foreach ($d in (Get-PSDrive -PSProvider FileSystem).Name) { $cands += "${d}:\My Drive" }
    $cands += "$env:USERPROFILE\My Drive", "$env:USERPROFILE\Google Drive\My Drive"
    $root = $cands | Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($root) { $DriveDir = Join-Path $root 'HyperCode-Backups' }
}

if (-not (Test-Path (Join-Path $pending $name))) {
    $out = Join-Path $pending $name
    & $7z a -t7z -mx=1 -mhe=on "-p$pw" $out $pgDump.FullName "$($pgDump.FullName).sha256" $stSet.FullName -bso0 -bsp0
    if ($LASTEXITCODE -ne 0) { Remove-Item -LiteralPath $out -Force -ErrorAction SilentlyContinue; Say "FAIL: 7z exit $LASTEXITCODE" Red; exit 1 }
}
# verify: archive tests clean WITH the passphrase and is unreadable WITHOUT it
$arc = Join-Path $pending $name
if (Test-Path $arc) {
    & $7z t "-p$pw" $arc -bso0 -bsp0; if ($LASTEXITCODE -ne 0) { Say 'FAIL: encrypted archive does not verify' Red; exit 1 }
    # 7z prints an error to stderr here by design; that must not trip $ErrorActionPreference='Stop'.
    & { $ErrorActionPreference = 'Continue'; & $7z l -pWRONG-PASSPHRASE $arc -bso0 -bsp0 2>&1 | Out-Null }
    $leaks = ($LASTEXITCODE -eq 0)
    if ($leaks) { Say 'FAIL: archive listing readable without the passphrase (headers not encrypted)' Red; exit 1 }
    Say ("B) encrypted OK: {0}  {1:N1} MB (verifies with passphrase; unreadable without)" -f $name, ((Get-Item $arc).Length/1MB)) Green
}

# ---- deliver to Drive ----
if ($DriveDir -and (Test-Path (Split-Path $DriveDir))) {
    New-Item -ItemType Directory -Force -Path $DriveDir | Out-Null
    Get-ChildItem $pending -Filter 'hypercode_*.7z' | ForEach-Object { Move-Item -LiteralPath $_.FullName -Destination $DriveDir -Force }
    Get-ChildItem $DriveDir -Filter 'hypercode_*.7z' | Sort-Object Name -Descending | Select-Object -Skip $KeepDrive | Remove-Item -Force
    Say "Delivered to Drive folder: $DriveDir (Drive for Desktop syncs it to the cloud)" Green
} else {
    Say "WAITING: Google Drive folder not found. Encrypted archive(s) are queued in $pending." Yellow
    Say '         Start Google Drive for Desktop and sign in; the next run moves them across.' Yellow
    $code = 2
}
exit $code
