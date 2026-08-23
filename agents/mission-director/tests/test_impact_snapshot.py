# agents/mission-director/tests/test_impact_snapshot.py
from impact_snapshot import get_impact

COMPOSE = """
services:
  postgres:
    ports:
      - "5432:5432"
  worker:
    profiles: ["agents"]
    ports:
      - "9010:8080"
    depends_on:
      - postgres
  always-on-consumer:
    ports:
      - "9012:8080"
    depends_on:
      - worker
"""

OVERLAY_EMPTY = """
roster: []
allowed_collisions: {}
"""


def test_get_impact_happy_path(tmp_path):
    compose_file = tmp_path / "compose.yml"
    compose_file.write_text(COMPOSE)
    overlay_file = tmp_path / "overlay.yml"
    overlay_file.write_text(OVERLAY_EMPTY)

    views = get_impact(["agents"], files=[str(compose_file)], overlay_path=str(overlay_file))

    assert len(views) == 1
    view = views[0]
    assert view.profile == "agents"
    assert view.available is True
    assert view.upstream == ["postgres"]
    assert view.downstream_already_running == ["always-on-consumer"]


def test_get_impact_degrades_on_registry_error(tmp_path):
    compose_file = tmp_path / "compose.yml"
    compose_file.write_text(COMPOSE)
    overlay_file = tmp_path / "overlay.yml"
    overlay_file.write_text("roster:\n  - nonexistent-service\nallowed_collisions: {}\n")

    views = get_impact(["agents"], files=[str(compose_file)], overlay_path=str(overlay_file))

    assert len(views) == 1
    assert views[0].available is False
    assert views[0].reason is not None
    assert views[0].upstream == []


def test_get_impact_empty_profiles_returns_empty_list():
    assert get_impact([]) == []
