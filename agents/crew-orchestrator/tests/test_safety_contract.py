"""crew-orchestrator's strict dispatch client must satisfy the shared contract.

The contract itself lives in agents/shared/safety_contract.py so crew and
fleet-controller are held to one spec; each ships its own client.
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2] / "shared"))

import safety_client  # noqa: E402  (crew-orchestrator/, added by conftest)
from safety_contract import assert_strict_client_contract  # noqa: E402


def test_strict_dispatch_client_contract():
    assert_strict_client_contract(safety_client)
