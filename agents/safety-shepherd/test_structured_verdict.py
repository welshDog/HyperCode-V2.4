from policy import RISK_CLASS, POLICY_VERSION, Decision


def test_risk_class_map():
    assert RISK_CLASS["docker"] == "INFRASTRUCTURE_MUTATION"
    assert RISK_CLASS.get("nonsense", "READ_ONLY") == "READ_ONLY"


def test_as_dict_has_structured_fields_for_docker():
    d = Decision("ESCALATE", "dangerous", "dangerous_category", category="docker", agent="governor")
    out = d.as_dict()
    # back-compat: old keys still present
    assert out["decision"] == "ESCALATE"
    assert out["reason"] == "dangerous"
    assert out["rule"] == "dangerous_category"
    # new keys
    assert out["risk_class"] == "INFRASTRUCTURE_MUTATION"
    assert out["policy_version"] == POLICY_VERSION
    assert out["reasons"] == ["dangerous"]
    assert "compose_profile.start" in out["blocked_actions"]
    assert "compose_profile.preview" in out["allowed_actions"]


def test_as_dict_generic_category_has_empty_action_lists():
    out = Decision("ALLOW", "ok", "default", category="generic").as_dict()
    assert out["risk_class"] == "READ_ONLY"
    assert out["allowed_actions"] == []
    assert out["blocked_actions"] == []
