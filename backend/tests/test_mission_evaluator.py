from app.services.mission_evaluator import TERMINAL_STATUSES, evaluate_mission


def _plan_response(decision, shepherd_available=True):
    return {
        "plan_id": "plan_x",
        "plan_hash": "sha256:x",
        "safety": {"decision": decision, "reason": "r", "shepherd_available": shepherd_available},
        "execution": {"performed": False, "would_execute": []},
    }


def test_terminal_statuses_are_exactly_the_four_expected():
    assert TERMINAL_STATUSES == frozenset(
        {"rejected_malformed", "preview_unavailable", "approved", "rejected"}
    )


def test_rejected_malformed_has_no_safety_or_human_decision():
    result = evaluate_mission("rejected_malformed", None)
    assert result["plan_malformed"] is True
    assert result["preview_failed"] is False
    assert result["safety_decision"] is None
    assert result["shepherd_available"] is None
    assert result["human_decision"] is None
    assert result["verdict"] == "clean"
    assert result["summary"] == "clean: rejected_malformed"


def test_preview_unavailable_has_no_safety_or_human_decision():
    result = evaluate_mission("preview_unavailable", None)
    assert result["preview_failed"] is True
    assert result["plan_malformed"] is False
    assert result["human_decision"] is None
    assert result["verdict"] == "clean"


def test_approved_with_allow_is_clean():
    result = evaluate_mission("approved", _plan_response("ALLOW"))
    assert result["human_decision"] == "approved"
    assert result["safety_decision"] == "ALLOW"
    assert result["anomaly_approved_despite_block"] is False
    assert result["anomaly_approved_despite_shepherd_down"] is False
    assert result["verdict"] == "clean"


def test_approved_despite_real_block_is_the_flagship_anomaly():
    result = evaluate_mission("approved", _plan_response("BLOCK", shepherd_available=True))
    assert result["anomaly_approved_despite_block"] is True
    assert result["anomaly_approved_despite_shepherd_down"] is False
    assert result["verdict"] == "anomaly"
    assert result["summary"] == "anomaly: approved despite a genuine Shepherd BLOCK verdict"


def test_approved_despite_shepherd_down_is_a_distinct_anomaly():
    result = evaluate_mission("approved", _plan_response("BLOCK", shepherd_available=False))
    assert result["anomaly_approved_despite_block"] is False
    assert result["anomaly_approved_despite_shepherd_down"] is True
    assert result["verdict"] == "anomaly"
    assert result["summary"] == "anomaly: approved while Shepherd was unreachable (fail-closed BLOCK)"


def test_rejected_despite_allow_is_a_secondary_anomaly():
    result = evaluate_mission("rejected", _plan_response("ALLOW"))
    assert result["anomaly_rejected_despite_allow"] is True
    assert result["verdict"] == "anomaly"


def test_rejected_with_escalate_is_clean():
    result = evaluate_mission("rejected", _plan_response("ESCALATE"))
    assert result["anomaly_rejected_despite_allow"] is False
    assert result["verdict"] == "clean"


def test_malformed_plan_response_degrades_to_none_never_raises():
    result = evaluate_mission("approved", {"safety": "not-a-dict"})
    assert result["safety_decision"] is None
    assert result["shepherd_available"] is None
    # human_decision is still "approved" (derived from status, not plan_response)
    assert result["human_decision"] == "approved"
    assert result["anomaly_approved_despite_block"] is False


def test_approved_despite_block_with_missing_shepherd_available_key_still_flags():
    """A plan_response.safety dict that omits shepherd_available entirely
    must still flag the more serious anomaly, not silently pass as clean --
    this is the exact case a final whole-branch review caught: neither
    'is True' nor 'is False' matches None, so the original code silently
    missed this permanently (mission_evaluations rows are write-once)."""
    plan_response = {
        "plan_id": "plan_x",
        "plan_hash": "sha256:x",
        "safety": {"decision": "BLOCK", "reason": "r"},  # no shepherd_available key at all
        "execution": {"performed": False, "would_execute": []},
    }
    result = evaluate_mission("approved", plan_response)
    assert result["shepherd_available"] is None
    assert result["anomaly_approved_despite_block"] is True
    assert result["anomaly_approved_despite_shepherd_down"] is False
    assert result["verdict"] == "anomaly"
