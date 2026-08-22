"""Structural regression guards -- mirrors agents/fleet-controller/tests/
test_no_execution.py's style. broski-coo's whole value proposition is a
trust property (never mutates, never invents facts); these tests exist so
a mutation call path or Docker dependency can never be silently added
later without a test failing."""
import sys


def test_no_docker_module_imported_anywhere():
    import main  # noqa: F401 -- import is the assertion

    assert "docker" not in sys.modules


def test_no_restart_or_reset_attribute():
    import main

    suspicious = [name for name in dir(main) if "restart" in name.lower() or "reset" in name.lower()]
    assert suspicious == []


def test_no_docker_host_functionally_read():
    """Checks for an actual os.getenv/os.environ read of DOCKER_HOST or a
    docker.sock path, not a bare substring match -- main.py's own docstring
    and HYPER-AGENT-BIBLE.md legitimately document DOCKER_HOST's *absence*
    by name, which a naive substring check would misflag."""
    import inspect

    import main

    source = inspect.getsource(main)
    assert 'getenv("DOCKER_HOST"' not in source
    assert "environ[\"DOCKER_HOST\"]" not in source
    assert "docker.sock" not in source


def test_only_expected_routes_exist():
    import main

    app_routes = sorted(
        (route.path, tuple(sorted(m for m in route.methods if m != "HEAD")))
        for route in main.app.routes
        if hasattr(route, "endpoint") and getattr(route.endpoint, "__module__", None) == "main"
    )
    assert app_routes == sorted(
        [
            ("/", ("GET",)),
            ("/health", ("GET",)),
            ("/brief", ("POST",)),
        ]
    )
