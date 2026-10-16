# fix_timestamps.ps1 - after post_missing.py, set the backfilled ledger rows' created_at back to the ORIGINAL award times.
# (core's award-dev-xp stamps new rows with "now"; it has no timestamp field.)
#
# One guarded transaction: it only touches rows with id > -BaselineMaxId AND stream='dev-action' AND a source_id on the list,
# and it ABORTS (rolls back) unless EXACTLY as many rows change as the CSV has. Take a Postgres backup first.
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\xp_reconcile\fix_timestamps.ps1 -Csv missing-awards.csv -BaselineMaxId 619 [-DryRun]
param(
    [Parameter(Mandatory = $true)][string]$Csv,
    [Parameter(Mandatory = $true)][int]$BaselineMaxId,   # highest broski_transactions.id BEFORE you ran post_missing.py
    [switch]$DryRun
)
$ErrorActionPreference = 'Stop'
$rows = @(Import-Csv $Csv)
if ($rows.Count -eq 0) { throw 'CSV is empty' }
foreach ($r in $rows) { if ($r.when_utc -notmatch '^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$') { throw "bad when_utc: $($r.when_utc)" } }
$vals = ($rows | ForEach-Object { "('" + $_.source_id.Replace("'", "''") + "', '" + $_.when_utc + "+00')" }) -join ",`n"
$sql = @"
BEGIN;
DO `$`$
DECLARE n integer;
BEGIN
  UPDATE broski_transactions t
     SET created_at = v.ts::timestamptz
    FROM (VALUES
$vals
         ) AS v(sid, ts)
   WHERE t.meta->>'source_id' = v.sid
     AND t.id > $BaselineMaxId
     AND t.meta->>'stream' = 'dev-action';
  GET DIAGNOSTICS n = ROW_COUNT;
  IF n <> $($rows.Count) THEN
    RAISE EXCEPTION 'expected to update exactly $($rows.Count) rows but would update %', n;
  END IF;
  RAISE NOTICE 'updated % rows', n;
END `$`$;
$(if ($DryRun) { 'ROLLBACK;' } else { 'COMMIT;' })
"@
if ($DryRun) { Write-Host "DRY RUN (the transaction is rolled back): " -NoNewline }
# psql prints NOTICE lines on stderr. Under $ErrorActionPreference='Stop' Windows PowerShell 5.1 would turn that harmless
# line into a terminating error and could abort the script mid-transaction, so run the native call with 'Continue'.
$prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
$out = $sql | docker exec -i postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -v ON_ERROR_STOP=1' 2>&1
$rc = $LASTEXITCODE
$ErrorActionPreference = $prev
$text = ($out | ForEach-Object { "$_" }) -join ' | '
Write-Host $text
if ($rc -ne 0 -or $text -match 'ERROR:') { throw "psql failed (exit $rc) - nothing was changed (the guard rolled back)" }
