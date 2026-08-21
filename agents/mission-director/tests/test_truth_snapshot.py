# agents/mission-director/tests/test_truth_snapshot.py
import pytest

from fleet_registry import RegistryError
from truth_snapshot import get_snapshot_ref


COMPOSE = """
services:
  service-a:
    ports:
      - "9001:8080"
"""

OVERLAY_VALID = """
roster:
  - service-a
allowed_collisions: {}
"""

OVERLAY_STALE = """
roster:
  - service-does-not-exist
allowed_collisions: {}
"""


def test_snapshot_ref_is_deterministic(tmp_path):
    compose_file = tmp_path / "compose.yml"
    compose_file.write_text(COMPOSE)
    overlay_file = tmp_path / "overlay.yml"
    overlay_file.write_text(OVERLAY_VALID)

    ref1 = get_snapshot_ref(files=[str(compose_file)], overlay_path=str(overlay_file))
    ref2 = get_snapshot_ref(files=[str(compose_file)], overlay_path=str(overlay_file))
    assert ref1 == ref2
    assert ref1.startswith("sha256:")


def test_snapshot_ref_changes_when_registry_changes(tmp_path):
    compose_file = tmp_path / "compose.yml"
    compose_file.write_text(COMPOSE)
    overlay_file = tmp_path / "overlay.yml"
    overlay_file.write_text(OVERLAY_VALID)
    ref_before = get_snapshot_ref(files=[str(compose_file)], overlay_path=str(overlay_file))

    compose_file.write_text(COMPOSE + "\n  service-b:\n    ports:\n      - \"9002:8080\"\n")
    ref_after = get_snapshot_ref(files=[str(compose_file)], overlay_path=str(overlay_file))
    assert ref_before != ref_after


def test_snapshot_ref_raises_on_stale_overlay(tmp_path):
    compose_file = tmp_path / "compose.yml"
    compose_file.write_text(COMPOSE)
    overlay_file = tmp_path / "overlay.yml"
    overlay_file.write_text(OVERLAY_STALE)

    with pytest.raises(RegistryError):
        get_snapshot_ref(files=[str(compose_file)], overlay_path=str(overlay_file))
