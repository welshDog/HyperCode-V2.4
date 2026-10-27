# agents/mission-director/tests/test_no_execution.py
"""Mission Director is a proposal/preview service, not an executor.

Guard the HTTP surface and source against adding queue publishing or a local
execution route before a separately reviewed, capability-gated phase."""
import ast
import inspect
from pathlib import Path

import main


def test_main_module_never_hardcodes_performed_true():
    source = inspect.getsource(main)
    assert "performed=True" not in source
    assert "performed = True" not in source


def test_mission_director_exposes_no_execute_route():
    paths = {route.path for route in main.app.routes}
    assert "/v1/missions/{mission_id}/execute" not in paths
    assert "/v1/plan" in paths


def test_mission_director_has_no_redis_execution_publisher():
    source = inspect.getsource(main)
    tree = ast.parse(source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not any(name == "redis" or name.startswith("redis.") for name in imports)
    assert "MISSION_EXECUTION_CHANNEL" not in source
    assert "redis.from_url" not in source
    assert "publish(" not in source
    assert "mission_store.update_status" not in source


def test_only_truth_grounded_preview_and_health_routes_are_registered():
    paths = {
        route.path
        for route in main.app.routes
        if route.path not in {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}
    }
    assert paths == {"/health", "/v1/plan"}


def test_terminal_helper_never_sets_plan_response():
    """_terminal() is used for every failure path -- plan_response must
    always be None there, since fleet-controller was never successfully
    reached (or never called) on any path that uses it."""
    source = inspect.getsource(main._terminal)
    assert "plan_response=None" in source
