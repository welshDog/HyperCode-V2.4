# xp_reconcile.ps1 - detect BROski$ dev-XP awards that are banked in Redis but missing from the Postgres ledger.
#
# Dot-source it:   . scripts\lib\xp_reconcile.ps1
#
# Why: the economy consumer banks every award in Redis FIRST (a "seen" marker + a stream entry) and then posts it to core,
# which writes the Postgres wallet. If that post fails (stale API key after a rotation, core down, timeout) the award stays
# in Redis only, and nothing noticed: 63 awards / 660 XP went missing across Aug-Oct 2026 (the Sep 9 re-rotation and the
# Oct 15 rotation). Each marker is  broski:xp:seen:<source_id>  and is SET with a 90-day EXPIRE at consumption time, so
#   age_seconds = 7776000 - remaining_ttl.
# The ledger stores the same source_id in broski_transactions.meta->>'source_id'. Marker with no ledger row = lost award.
#
# ASCII only and Windows PowerShell 5.1 compatible (the repo's scheduled tasks run powershell.exe).

$script:XpSeenTtlSeconds = 7776000        # must match _SEEN_TTL in scripts/broski_economy_consumer.py
$script:XpMarkerPrefix   = 'broski:xp:seen:'

function Find-MissingXpAwards {
    <#
      PURE function (no docker, no I/O): which markers have no ledger row?
        -Markers       objects with .SourceId and .Ttl (seconds remaining; <0 = no expiry / gone, ignored)
        -LedgerIds     source_ids present in the ledger
        -GraceSeconds  ignore awards younger than this (they may still be on their way to Postgres)
      Returns objects { SourceId; AgeSeconds }, oldest first.
    #>
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][object[]]$Markers,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][string[]]$LedgerIds,
        [int]$GraceSeconds = 600,
        [int]$SeenTtlSeconds = $script:XpSeenTtlSeconds
    )
    $have = New-Object 'System.Collections.Generic.HashSet[string]'
    foreach ($id in $LedgerIds) { if ($id) { [void]$have.Add($id) } }
    $out = @()
    foreach ($m in $Markers) {
        if ($null -eq $m -or [int64]$m.Ttl -lt 0) { continue }
        $age = $SeenTtlSeconds - [int64]$m.Ttl
        if ($age -lt $GraceSeconds) { continue }
        if (-not $have.Contains([string]$m.SourceId)) { $out += [pscustomobject]@{ SourceId = [string]$m.SourceId; AgeSeconds = $age } }
    }
    return @($out | Sort-Object AgeSeconds -Descending)
}

function Format-XpMissingMessage {
    param([object[]]$Missing)
    $oldest = ($Missing | Measure-Object AgeSeconds -Maximum).Maximum
    $date = (Get-Date).AddSeconds(-$oldest).ToString('yyyy-MM-dd')
    return ("{0} BROski`$ XP award(s) are banked in Redis but MISSING from the Postgres wallet (oldest {1}): the economy consumer's Postgres sink is failing or core was down. Reconcile them: docs\BROSKI_XP_RECONCILE.md." -f @($Missing).Count, $date)
}

# Run a shell snippet inside a container, passed as base64 so Windows PowerShell 5.1 cannot mangle quoting or add a BOM.
function Invoke-InContainer {
    param([string]$Container, [string]$Snippet)
    $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($Snippet -replace "`r", '')))
    $out = docker exec $Container sh -c "echo $b64 | base64 -d | sh" 2>$null
    if ($LASTEXITCODE -ne 0) { throw "docker exec $Container failed (exit $LASTEXITCODE)" }
    return $out
}

function Get-XpMarkers {
    # "<key> <ttl>" per marker, computed inside the redis container (db 1 is the economy db).
    $snip = 'redis-cli -n 1 --scan --pattern "broski:xp:seen:*" | while read k; do echo "$k $(redis-cli -n 1 ttl "$k")"; done'
    $markers = @()
    foreach ($line in (Invoke-InContainer -Container 'redis' -Snippet $snip)) {
        if ($line -match '^(\S+)\s+(-?\d+)\s*$') {
            $key = $Matches[1]; $ttl = [int64]$Matches[2]
            if ($key.StartsWith($script:XpMarkerPrefix)) { $markers += [pscustomobject]@{ SourceId = $key.Substring($script:XpMarkerPrefix.Length); Ttl = $ttl } }
        }
    }
    return $markers
}

function Get-XpLedgerIds {
    $snip = 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -c "select meta->>''source_id'' from broski_transactions where meta->>''source_id'' is not null"'
    return @(Invoke-InContainer -Container 'postgres' -Snippet $snip | Where-Object { $_ -and $_.Trim() } | ForEach-Object { $_.Trim() })
}
