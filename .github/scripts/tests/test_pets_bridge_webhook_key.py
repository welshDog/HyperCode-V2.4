"""broski-pets-bridge sends evolve-relay its OWN key (EVOLVE_WEBHOOK_API_KEY), not the bridge's inbound key.

Why: core calls the bridge with the master key (so HYPERCODE_API_KEY on the bridge = master), but evolve-relay checks the
shared inter-agent key. The webhook call swallows errors on purpose, so a wrong key would fail silently: this keeps the
split from being undone. Source-level on purpose: importing the bridge needs fastapi/httpx, which this lane does not install.
"""
from pathlib import Path

SRC = (Path(__file__).resolve().parents[3] / "agents/broski-pets-bridge/main.py").read_text(encoding="utf-8")


def test_webhook_prefers_its_own_key_and_falls_back_to_the_inbound_one():
    assert 'read_secret("EVOLVE_WEBHOOK_API_KEY") or read_secret("HYPERCODE_API_KEY")' in SRC


def test_webhook_header_is_built_from_that_value_only():
    i = SRC.index("EVOLVE_WEBHOOK_API_KEY")
    block = SRC[i : i + 400]
    assert 'headers["X-API-Key"] = shared' in block
