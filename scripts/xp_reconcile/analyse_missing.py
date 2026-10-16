"""READ-ONLY: which BROski$ dev-XP awards are banked in Redis but missing from the Postgres ledger?

    python -X utf8 scripts/xp_reconcile/analyse_missing.py <folder from export_xp_data.ps1>

Writes <folder>/missing-awards.csv (when_utc,xp,source,reason,source_id - the format post_missing.py expects) and prints a
report. Exit code 0 = analysis trustworthy (also when nothing is missing); 3 = a sanity check failed: DO NOT backfill.

Join: each award leaves a marker broski:xp:seen:<source_id> (EXPIRE 7776000 s at consumption time) so
award_time = snapshot + remaining_ttl - 7776000, matched to the stream entry whose ENTRY ID (ms, stamped at consumption time)
is closest, in the same repo. NOT the stream's `ts` field: that is the publisher's time and bursts are consumed late.
The join is validated first on the awards that DID land (the ledger knows the right answer); on 2026-10-16 it was 271/271.
"""
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

D = Path(sys.argv[1])
SEEN_TTL = 7776000
PFX = "broski:xp:seen:"
MAX_GAP_S = 30  # a marker and its stream entry are written within moments of each other; a wider gap means a wrong join


def iso_epoch(s):
    return datetime.fromisoformat(s).astimezone(timezone.utc).timestamp()


# ---- stream
stream, cur = [], None
lines = [l.rstrip("\n") for l in (D / "stream.txt").read_text(encoding="utf-8-sig").splitlines()]
import re
for l in lines:
    if re.fullmatch(r"\d+-\d+", l):
        cur = {"id": l}
        stream.append(cur)
        cur["_kv"] = []
    elif cur is not None:
        cur["_kv"].append(l)
for e in stream:
    kv = e.pop("_kv")
    # raw redis-cli prints field,value,field,value,...  (values may be blank-free text)
    it = iter(kv)
    for k in it:
        e[k] = next(it, "")
    e["xp"] = int(e.get("xp", 0))
    e["epoch"] = int(e["id"].split("-")[0]) / 1000.0   # XADD time = consumption time (same instant the seen-marker was set)`n    e["pub_epoch"] = iso_epoch(e["ts"]) if e.get("ts") else None

# ---- markers
snap = int(re.search(r"(\d+)", (D / "snapshot.txt").read_text(encoding="utf-8-sig")).group(1))
markers = []
for l in (D / "markers.txt").read_text(encoding="utf-8-sig").splitlines():
    if not l.strip():
        continue
    parts = l.split()
    key, ttl = parts[0], int(parts[1])
    read_at = int(parts[2]) if len(parts) >= 3 else snap      # exact time THIS ttl was read (newer exports); else the shared snapshot time
    if ttl < 0:
        continue
    markers.append({"sid": key[len(PFX):], "award_epoch": read_at + ttl - SEEN_TTL})

# ---- ledger
ledger = list(csv.DictReader((D / "ledger.csv").open(encoding="utf-8-sig")))
L_by_sid = {}
for r in ledger:
    if r["source_id"]:
        L_by_sid.setdefault(r["source_id"], []).append(r)
dups = {k: v for k, v in L_by_sid.items() if len(v) > 1}

print(f"stream entries: {len(stream)}  markers: {len(markers)}  ledger dev-action rows: {len(ledger)}  (with source_id: {sum(len(v) for v in L_by_sid.values())})")
print(f"ledger source_ids appearing more than once: {len(dups)}")

# ---- nearest stream entry for a marker (same repo)
stream_sorted = [e for e in stream if e["epoch"] is not None]


def nearest(m):
    repo = m["sid"].split(":")[1] if m["sid"].count(":") >= 2 else None
    best = None
    for e in stream_sorted:
        if repo and not e.get("source", "").endswith(repo):
            continue
        d = abs(e["epoch"] - m["award_epoch"])
        if d <= MAX_GAP_S and (best is None or d < best[0]):
            best = (d, e)
    return best


# ---- 1) VALIDATE the join on awards that did land
ok = bad = 0
mism = []
for m in markers:
    if m["sid"] in L_by_sid:
        hit = nearest(m)
        row = L_by_sid[m["sid"]][0]
        if hit is None:
            bad += 1
            mism.append((m["sid"], None, "(no stream entry within %ds)" % MAX_GAP_S, row["reason"][:50]))
            continue
        d, e = hit
        if row["reason"] == "XP: " + e.get("reason", "") and int(row["amount"]) == e["xp"]:
            ok += 1
        else:
            bad += 1
            mism.append((m["sid"], round(d, 1), e.get("reason", "")[:50], row["reason"][:50]))
tot = ok + bad
print(f"\nJOIN VALIDATION on awards that landed: {ok}/{tot} correct ({100*ok/max(tot,1):.1f}%)")
for x in mism[:5]:
    print("   mismatch:", x)

# ---- 2) the missing ones
missing = [m for m in markers if m["sid"] not in L_by_sid]
print(f"\nMISSING from the ledger (marker exists, no ledger row): {len(missing)}")
rows = []
unmatched = []
for m in sorted(missing, key=lambda x: x["award_epoch"]):
    hit = nearest(m)
    if hit is None:
        unmatched.append(m["sid"])
        continue
    d, e = hit
    rows.append({
        "source_id": m["sid"], "when_utc": datetime.fromtimestamp(m["award_epoch"], timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "xp": e["xp"], "source": e.get("source"), "reason": e.get("reason"), "join_gap_s": round(d, 1),
    })
if rows:
    tot_xp = sum(r["xp"] for r in rows)
    print(f"   total XP missing: {tot_xp}   first: {rows[0]['when_utc']}   last: {rows[-1]['when_utc']}")
    print("   by repo:", dict(Counter(r["source"] for r in rows)))
    print("   by day :", dict(sorted(Counter(r["when_utc"][:10] for r in rows).items())))
    print("   join gap (s): max %.1f  >2s: %d" % (max(r["join_gap_s"] for r in rows), sum(1 for r in rows if r["join_gap_s"] > 2)))
    reasons = Counter(r["reason"] for r in rows)
    print("   duplicate reasons among the missing (same commit text twice):", sum(1 for v in reasons.values() if v > 1))
    print("   sample (first 4):")
    for r in rows[:4]:
        print("     ", r["when_utc"], r["xp"], r["source_id"][:48], "|", (r["reason"] or "")[:60])
    print("   sample (last 3):")
    for r in rows[-3:]:
        print("     ", r["when_utc"], r["xp"], r["source_id"][:48], "|", (r["reason"] or "")[:60])
(D / "missing.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
with (D / "missing-awards.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["when_utc", "xp", "source", "reason", "source_id"])
    for r in rows:
        w.writerow([r["when_utc"], r["xp"], r["source"], r["reason"], r["source_id"]])
print(f"\nwrote {D / 'missing-awards.csv'} ({len(rows)} rows)")

# ---- sanity checks: a failure here means the join cannot be trusted - do NOT backfill
problems = []
if unmatched:
    problems.append(f"{len(unmatched)} missing marker(s) have NO stream entry (export race or corrupt data): {unmatched[:3]}")
if tot and ok != tot:
    problems.append(f"join validation on landed awards was {ok}/{tot}, not 100%")
if len({r['source_id'] for r in rows}) != len(rows):
    problems.append("two missing awards share a source_id")
if len({r['reason'] for r in rows}) != len(rows):
    problems.append("two missing awards share the same commit text (ambiguous join)")
ledger_reasons_set = {r["reason"] for r in ledger}
clash = [r for r in rows if ("XP: " + (r["reason"] or "")) in ledger_reasons_set]
if clash:
    problems.append(f"{len(clash)} 'missing' awards already exist in the ledger under another source_id (wrong join?)")
print("SANITY: " + ("OK" if not problems else "FAILED - " + "; ".join(problems)))
if problems:
    sys.exit(3)

# ---- 3) stream entries that have NO marker (no source_id) and no obvious ledger twin
marker_epochs = [m["award_epoch"] for m in markers]
ledger_reasons = Counter(r["reason"] for r in ledger)
no_marker = []
for e in stream_sorted:
    if any(abs(e["epoch"] - t) < 3 for t in marker_epochs):
        continue
    no_marker.append(e)
print(f"\nstream entries with NO seen-marker nearby: {len(no_marker)}")
cat = Counter()
for e in no_marker:
    in_ledger = ("XP: " + e.get("reason", "")) in ledger_reasons
    cat[(e.get("source", "")[:28], "reason already in ledger" if in_ledger else "NOT in ledger")] += 1
for k, v in sorted(cat.items(), key=lambda x: -x[1])[:12]:
    print(f"   {v:4d}  {k[0]:30s} {k[1]}")
print("\nledger source_ids that have no marker (older than the 90-day marker TTL, expected):",
      len([s for s in L_by_sid if s not in {m['sid'] for m in markers}]))
