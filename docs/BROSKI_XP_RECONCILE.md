# BROski$ dev-XP: reconcile awards that are in Redis but missing from the Postgres wallet

**You are here because the watchdog said:** *"N BROski$ XP award(s) are banked in Redis but MISSING from the Postgres wallet ..."*

## What happened

Every git commit publishes a small XP award. The **economy consumer** (`scripts/broski_economy_consumer.py`) banks it in Redis
first (a `broski:xp:seen:<source_id>` marker with a 90-day expiry, plus an entry in the `broski:xp:log` stream) and **then**
posts it to core (`POST /api/v1/economy/award-dev-xp`), which writes the Postgres wallet. If that post fails, the award stays in
Redis only. Nothing else notices.

It has failed this way before: **63 awards / 660 XP** were lost across Aug-Oct 2026. Causes were key rotations (the consumer kept
a stale API key, core answered 401) and, once, a cold-start timeout. Find the cause and fix it **before** reconciling, or the
backfill just fails again: `docker logs broski-economy-consumer --since 2h | grep -i "pg FAILED\|ERROR"`, and core's access
log for `award-dev-xp` (the watchdog's 401/403 alert often fires first).

## Why backfilling is safe

* Core's endpoint is **idempotent on `source_id`**: it checks the ledger first, and a repeat is a no-op (`awarded: false`).
* `award_xp` has no side effects beyond the wallet XP, one ledger row and a level check.
* The `source_id` of every lost award is in its Redis marker, so nothing is guessed.
* Level 7 ("BROski Legend", 5000+ XP) is the top tier, so extra XP cannot change the level.
* The API stamps new rows with *now* (it has no timestamp field); `fix_timestamps.ps1` puts the original times back.

## Procedure (about 10 minutes)

Run from the repo root. Everything before step 5 is read-only.

```powershell
$d = "backups\backfill\$(Get-Date -Format yyyyMMdd)"

# 1. Snapshot the three datasets (Redis markers + stream, Postgres ledger). BOM-free under any PowerShell.
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\xp_reconcile\export_xp_data.ps1 -OutDir $d

# 2. Find what is missing. Exit 0 = trustworthy; exit 3 = a sanity check failed: STOP, do not backfill.
python -X utf8 -I scripts\xp_reconcile\analyse_missing.py $d        # writes $d\missing-awards.csv
```
Read the report. On 2026-10-16 the join was validated **271/271** on awards that did land. Expect `JOIN VALIDATION ... 100%`
and `SANITY: OK`. Open `missing-awards.csv` and eyeball it (time, XP, commit message).

```powershell
# 3. Rollback point + baseline (write the numbers down)
Start-ScheduledTask -TaskPath '\HyperCode\' -TaskName 'HyperCode Postgres Backup'     # wait for result 0x0
"select count(*), max(id) from broski_transactions" | docker exec -i postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At'
"select xp, level from broski_wallets where id=1"   | docker exec -i postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At'

# 4. Post from INSIDE the consumer container (it has the master key file, never printed; python 3.11)
docker cp scripts\xp_reconcile\post_missing.py broski-economy-consumer:/tmp/post_missing.py
docker cp $d\missing-awards.csv               broski-economy-consumer:/tmp/missing-awards.csv
docker exec broski-economy-consumer python /tmp/post_missing.py /tmp/missing-awards.csv --dry-run    # validates every row, sends nothing

# 5. The real run. Fail-fast: it stops at the first unexpected response.
docker exec broski-economy-consumer python /tmp/post_missing.py /tmp/missing-awards.csv

# 6. Restore the original timestamps. One guarded transaction: rolls back unless EXACTLY the CSV's row count changes.
#    -BaselineMaxId = the max(id) you wrote down in step 3.
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\xp_reconcile\fix_timestamps.ps1 -Csv $d\missing-awards.csv -BaselineMaxId <N> -DryRun
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\xp_reconcile\fix_timestamps.ps1 -Csv $d\missing-awards.csv -BaselineMaxId <N>

# 7. Prove it: re-run step 5. It must report  awarded=0, already-present=<all>  and change nothing.
#    Then re-run steps 1-2: MISSING must be 0. Delete the temp files inside the container (python os.remove).
```

Expected effect: ledger rows `+N`, wallet XP `+(sum of the CSV's xp)`, every `source_id` exactly once.

## Things that look alarming but are not

* `->pg FAILED (TimeoutError)` on the **first** award after a restart: core's first call can take > 3 s (cold start). The row is
  usually written anyway (2026-10-16: ledger row 618). The reconcile check only alerts if it is *really* absent after 10 minutes.
* A 10 XP gap between the ledger's earn rows (7350) and `broski_wallets.xp` (7340) was already there before the backfill and is unrelated.
* Redis `broski:xp:total` (6670 then) differs from the wallet: Redis also holds test awards and the wallet also holds quest/bot XP.
* Markers expire after 90 days, so the check only covers awards from the last 90 days. Older losses cannot be reconstructed this way.

## How the watchdog detects it

`scripts/backup_watchdog.ps1` (13:00 and 18:00) dot-sources `scripts/lib/xp_reconcile.ps1`: it reads every marker and its remaining
TTL (award age = 7776000 - ttl), reads all `source_id`s from `broski_transactions`, and flags markers older than
`-XpGraceMinutes` (default 10) with no ledger row. The comparison (`Find-MissingXpAwards`) is a pure function covered by
`.github/scripts/tests/test_xp_reconcile.py` (CI lane `xp-reconcile.yml`). Try it with no side effects:
`powershell -File scripts\backup_watchdog.ps1 -DryRun`.

## Not covered

An award published with **no** `source_id` has no marker, so it cannot be detected or deduplicated. Git-hook awards always have one.
