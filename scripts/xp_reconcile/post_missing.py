"""Post missing dev-XP awards to core's idempotent POST /api/v1/economy/award-dev-xp.

Runs INSIDE the broski-economy-consumer container (it has the master key file, the discord id and a route to core).
The key is read from HYPERCODE_API_KEY_FILE and is never printed. Fail-fast: stops at the first unexpected response.
    python /tmp/post_missing.py /tmp/missing-awards.csv --dry-run     # parse + validate only, no network
    python /tmp/post_missing.py /tmp/missing-awards.csv               # post (oldest first)
"""
import csv
import json
import os
import sys
import urllib.error
import urllib.request

path = sys.argv[1]
dry = "--dry-run" in sys.argv
rows = sorted(csv.DictReader(open(path, encoding="utf-8-sig")), key=lambda r: r["when_utc"])

# ---- validate everything BEFORE sending anything
errs = []
seen = set()
for i, r in enumerate(rows, 1):
    if not r["source_id"].startswith("git:"):
        errs.append(f"row {i}: odd source_id {r['source_id'][:40]!r}")
    if r["source_id"] in seen:
        errs.append(f"row {i}: duplicate source_id")
    seen.add(r["source_id"])
    if not (0 < int(r["xp"]) <= 100):
        errs.append(f"row {i}: unexpected xp {r['xp']}")
    if len(r["reason"]) > 255 or len(r["source"]) > 128 or len(r["source_id"]) > 128:
        errs.append(f"row {i}: field too long for the API")
if errs:
    print("VALIDATION FAILED:\n  " + "\n  ".join(errs))
    sys.exit(2)
total_xp = sum(int(r["xp"]) for r in rows)
print(f"validated {len(rows)} awards, {total_xp} XP, oldest {rows[0]['when_utc']}, newest {rows[-1]['when_utc']}")

url = os.environ["HYPERCODE_API_URL"].rstrip("/") + "/api/v1/economy/award-dev-xp"
discord_id = os.environ["DEV_XP_DISCORD_ID"]
if dry:
    for r in rows[:3]:
        print("  would POST:", json.dumps({"discord_id": discord_id, "xp": int(r["xp"]), "source": r["source"],
                                           "reason": r["reason"][:60] + "...", "source_id": r["source_id"][:40] + "..."}))
    print("DRY RUN - nothing was sent")
    sys.exit(0)

key = open(os.environ["HYPERCODE_API_KEY_FILE"], encoding="utf-8-sig").read().strip()
awarded = dup = 0
awarded_xp = 0
balance = None
for i, r in enumerate(rows, 1):
    body = json.dumps({"discord_id": discord_id, "xp": int(r["xp"]), "source": r["source"],
                       "reason": r["reason"], "source_id": r["source_id"]}).encode()
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": "application/json", "X-API-Key": key})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            out = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"\nSTOP at row {i}/{len(rows)}: HTTP {e.code} {e.read()[:150]!r}")
        print(f"so far: awarded={awarded} already-present={dup}")
        sys.exit(3)
    except Exception as e:  # noqa: BLE001
        print(f"\nSTOP at row {i}/{len(rows)}: {type(e).__name__}: {e}")
        print(f"so far: awarded={awarded} already-present={dup}")
        sys.exit(4)
    if out.get("awarded"):
        awarded += 1
        awarded_xp += int(r["xp"])
    else:
        dup += 1
    balance = out.get("xp_balance")
    if i % 10 == 0 or i == len(rows):
        print(f"  {i:3d}/{len(rows)}  awarded={awarded}  already-present={dup}  balance={balance}")
print(f"\nDONE: awarded={awarded} ({awarded_xp} XP), already-present (no-op)={dup}, final wallet xp={balance}")
