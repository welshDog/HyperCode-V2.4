"""Tests for scripts/lib/xp_reconcile.ps1 - the watchdog's "XP banked in Redis but missing from Postgres" check.

The comparison (Find-MissingXpAwards) is a PURE PowerShell function, so it is tested here by feeding it JSON and reading
JSON back; no docker, Redis or Postgres needed. Needs PowerShell (`pwsh`, or Windows' `powershell`); skipped otherwise.

Background: 63 awards / 660 XP were lost between Aug and Oct 2026 (key rotations broke the economy consumer's post to
core) and nothing noticed. Run: python -m pytest .github/scripts/tests/test_xp_reconcile.py
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
LIB = REPO / "scripts" / "lib" / "xp_reconcile.ps1"
PS = shutil.which("pwsh") or shutil.which("powershell")
pytestmark = pytest.mark.skipif(PS is None, reason="PowerShell not available")

SEEN_TTL = 7776000  # must match _SEEN_TTL in scripts/broski_economy_consumer.py


def age_to_ttl(age_seconds):
    return SEEN_TTL - age_seconds


def run(markers, ledger, grace=600, body=None):
    """Dot-source the module, run Find-MissingXpAwards on the inputs, return the parsed JSON."""
    env = dict(os.environ, XP_MARKERS=json.dumps(markers), XP_LEDGER=json.dumps(ledger))
    body = body or "Find-MissingXpAwards -Markers $m -LedgerIds $l -GraceSeconds %d" % grace
    cmd = (
        f". '{LIB}'; "
        "$m = @($env:XP_MARKERS | ConvertFrom-Json); $l = @($env:XP_LEDGER | ConvertFrom-Json); "
        f"$r = @({body}); ConvertTo-Json -InputObject $r -Compress -Depth 4"
    )
    out = subprocess.run([PS, "-NoProfile", "-Command", cmd], capture_output=True, text=True, env=env, timeout=120)
    assert out.returncode == 0, out.stderr
    text = out.stdout.strip()
    return json.loads(text) if text else []


def marker(sid, age):
    return {"SourceId": sid, "Ttl": age_to_ttl(age)}


def test_nothing_missing_when_every_marker_is_in_the_ledger():
    m = [marker("git:R:a", 3600), marker("git:R:b", 7200)]
    assert run(m, ["git:R:a", "git:R:b", "quest:unrelated"]) == []


def test_flags_an_award_banked_in_redis_but_absent_from_the_ledger():
    m = [marker("git:R:a", 3600), marker("git:R:lost", 7200)]
    got = run(m, ["git:R:a"])
    assert [g["SourceId"] for g in got] == ["git:R:lost"]
    assert got[0]["AgeSeconds"] == 7200


def test_grace_period_ignores_awards_still_on_their_way():
    m = [marker("git:R:fresh", 120), marker("git:R:old", 3600)]
    assert [g["SourceId"] for g in run(m, [], grace=600)] == ["git:R:old"]
    assert {g["SourceId"] for g in run(m, [], grace=0)} == {"git:R:fresh", "git:R:old"}


def test_markers_without_a_usable_ttl_are_ignored():
    # -1 = no expiry set, -2 = key vanished between SCAN and TTL
    m = [{"SourceId": "git:R:noexp", "Ttl": -1}, {"SourceId": "git:R:gone", "Ttl": -2}]
    assert run(m, []) == []


def test_empty_inputs_are_fine():
    assert run([], []) == []
    assert run([], ["git:R:a"]) == []


def test_oldest_first_and_ids_with_colons_and_dashes_survive():
    m = [marker("git:Hyper-Vibe-Coding-Course:1979437c", 4000), marker("git:BROski-Obsidian-Brain:ffff", 9000)]
    got = run(m, [])
    assert [g["SourceId"] for g in got] == ["git:BROski-Obsidian-Brain:ffff", "git:Hyper-Vibe-Coding-Course:1979437c"]


def test_duplicate_ledger_ids_do_not_matter():
    assert run([marker("git:R:a", 3600)], ["git:R:a", "git:R:a"]) == []


def test_message_names_the_count_and_does_not_crash():
    m = [marker("git:R:x", 3600), marker("git:R:y", 90000)]
    msg = run(m, [], body="Format-XpMissingMessage -Missing (Find-MissingXpAwards -Markers $m -LedgerIds $l -GraceSeconds 600)")
    text = msg[0] if isinstance(msg, list) else msg
    assert text.startswith("2 BROski$ XP award(s)") and "MISSING from the Postgres wallet" in text
