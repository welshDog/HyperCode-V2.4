import os

import pytest

from fleet_registry import RegistryError, build

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
COMPOSE = os.path.join(FIXTURES, "compose_minimal.yml")


def test_build_parses_both_port_string_formats():
    registry = build(
        files=[COMPOSE],
        overlay_path=os.path.join(FIXTURES, "overlay_valid.yml"),
    )
    assert registry.services["service-a"].host_port == "9001"
    assert registry.services["service-a"].container_port == "8080"
    assert registry.services["service-b"].host_port == "9002"
    assert registry.services["service-b"].container_port == "8080"


def test_build_loads_roster_and_allowed_collisions():
    registry = build(
        files=[COMPOSE],
        overlay_path=os.path.join(FIXTURES, "overlay_valid.yml"),
    )
    assert registry.roster == frozenset({"service-a", "service-b"})
    assert registry.allowed_collisions == {
        "9001": frozenset({"service-a", "service-c"})
    }


def test_build_raises_on_stale_roster_entry():
    with pytest.raises(RegistryError, match="service-does-not-exist"):
        build(
            files=[COMPOSE],
            overlay_path=os.path.join(FIXTURES, "overlay_stale_roster.yml"),
        )


def test_build_raises_on_stale_allowed_collision():
    with pytest.raises(RegistryError, match="9001"):
        build(
            files=[COMPOSE],
            overlay_path=os.path.join(FIXTURES, "overlay_stale_collision.yml"),
        )


def test_build_raises_on_multi_port_service(tmp_path):
    multi_port_compose = tmp_path / "compose_multiport.yml"
    multi_port_compose.write_text(
        "services:\n"
        "  weird-service:\n"
        "    ports:\n"
        "      - \"9001:8080\"\n"
        "      - \"9002:8081\"\n"
    )
    overlay = tmp_path / "overlay_empty.yml"
    overlay.write_text("roster: []\nallowed_collisions: {}\n")
    with pytest.raises(RegistryError, match="weird-service"):
        build(files=[str(multi_port_compose)], overlay_path=str(overlay))
