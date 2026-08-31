"""fleet-controller's strict dispatch client must satisfy the shared contract.

The contract itself lives in agents/shared/safety_contract.py so fleet and
crew-orchestrator are held to one spec; each ships its own client. This does
not touch the plan-mutation path (check_infrastructure_mutation).
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2] / "shared"))

import safety_client  # noqa: E402  (fleet-controller/, added by conftest)
from safety_contract import assert_strict_client_contract  # noqa: E402


def test_strict_dispatch_client_contract():
    assert_strict_client_contract(safety_client)
