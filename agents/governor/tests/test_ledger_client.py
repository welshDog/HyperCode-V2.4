import ledger_client


def test_build_body_shape():
    body = ledger_client.build_body("capability.minted", "ALLOW", {"jti": "cap_1"})
    assert body == {
        "agent": "governor",
        "action": "capability.minted",
        "decision": "ALLOW",
        "user_id": "system",
        "payload": {"jti": "cap_1"},
    }


def test_record_is_noop_without_client():
    ledger_client._client = None
    ledger_client.record("x", "ALLOW", {})  # must not raise
