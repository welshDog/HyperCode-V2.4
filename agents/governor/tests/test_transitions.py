import pytest

import transitions as t


@pytest.mark.parametrize("mode,decision,kill,expect_mint,expect_appr,cap_mode", [
    ("DRY_RUN", "ALLOW", False, True, False, "DRY_RUN"),
    ("DRY_RUN", "ESCALATE", False, False, True, None),
    ("DRY_RUN", "BLOCK", False, False, False, None),
    ("LIVE", "ALLOW", False, True, False, "LIVE"),
    ("LIVE", "ESCALATE", False, False, True, None),
    ("LIVE", "BLOCK", False, False, False, None),
    ("LIVE", "ALLOW", True, False, False, None),
    ("DRY_RUN", "ALLOW", True, False, False, None),
])
def test_table(mode, decision, kill, expect_mint, expect_appr, cap_mode):
    out = t.resolve(mode=mode, decision=decision, kill_switch=kill, risk_class="INFRASTRUCTURE_MUTATION")
    assert out.mint is expect_mint
    assert out.needs_approval is expect_appr
    assert out.capability_mode == cap_mode


def test_kill_switch_still_allows_readonly_preview():
    out = t.resolve(mode="DRY_RUN", decision="ALLOW", kill_switch=True, risk_class="READ_ONLY")
    assert out.mint is True
    assert out.capability_mode == "DRY_RUN"


def test_kill_switch_readonly_preview_forces_dry_run_even_if_live_requested():
    """CodeRabbit follow-up: the requested mode must never pass through
    verbatim in this branch. The system lease only stops renewing on kill
    (it isn't invalidated), so it can stay valid for up to one lease period
    after a kill -- long enough that main.py's LIVE-mode lease gate would
    not catch a LIVE capability minted here. The kill switch must force
    DRY_RUN unconditionally, not rely on a downstream gate that can lag it."""
    out = t.resolve(mode="LIVE", decision="ALLOW", kill_switch=True, risk_class="READ_ONLY")
    assert out.mint is True
    assert out.capability_mode == "DRY_RUN"
