import os

import pytest

from fleet_registry import RegistryError, build, build_edges, impact_set

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
COMPOSE = os.path.join(FIXTURES, "compose_minimal.yml")
FIXTURE_WITH_DEPS = os.path.join(FIXTURES, "compose_with_deps.yml")
OVERLAY_EMPTY = os.path.join(FIXTURES, "overlay_empty.yml")


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


def test_service_info_parses_depends_on_list_form():
    registry = build(files=[FIXTURE_WITH_DEPS], overlay_path=OVERLAY_EMPTY)
    assert registry.services["worker"].depends_on == frozenset({"postgres"})
    assert registry.services["always-on-consumer"].depends_on == frozenset({"worker"})
    assert registry.services["postgres"].depends_on == frozenset()


def test_service_info_parses_env_var_names_from_dict_form():
    registry = build(files=[FIXTURE_WITH_DEPS], overlay_path=OVERLAY_EMPTY)
    assert registry.services["worker"].env_var_names == frozenset({"POSTGRES_HOST"})
    assert registry.services["watcher"].env_var_names == frozenset({"DATABASE_URL"})
    assert registry.services["postgres"].env_var_names == frozenset()


def test_build_edges_includes_depends_on_and_env_var_matches():
    registry = build(files=[FIXTURE_WITH_DEPS], overlay_path=OVERLAY_EMPTY)
    edges = build_edges(registry)
    assert edges["worker"] == frozenset({"postgres"})
    assert edges["watcher"] == frozenset({"postgres"})  # env-var-only, no depends_on
    assert edges["always-on-consumer"] == frozenset({"worker"})
    assert edges["postgres"] == frozenset()


def test_impact_set_computes_upstream_and_downstream():
    registry = build(files=[FIXTURE_WITH_DEPS], overlay_path=OVERLAY_EMPTY)
    result = impact_set(registry, "agents")
    assert result.profile == "agents"
    assert result.upstream == frozenset({"postgres"})
    assert result.downstream_already_running == frozenset({"always-on-consumer"})


def test_impact_set_returns_empty_for_unknown_profile():
    registry = build(files=[FIXTURE_WITH_DEPS], overlay_path=OVERLAY_EMPTY)
    result = impact_set(registry, "no-such-profile")
    assert result.upstream == frozenset()
    assert result.downstream_already_running == frozenset()
