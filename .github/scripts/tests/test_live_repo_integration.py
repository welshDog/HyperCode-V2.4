"""Integration tests against the REAL, live compose files + overlay — not
fixtures. This is the test that would have caught the stale :8011 bug
(frontend-specialist) before it shipped, and keeps the fixture tests honest
against reality. Must run with the repo root as the working directory —
fleet_registry.build()'s default file list is relative to CWD, matching how
the CI workflows invoke the consumer scripts."""
from fleet_registry import build


def test_build_succeeds_against_real_repo_state():
    registry = build()
    assert registry.roster, "roster should not be empty"
    assert all(name in registry.services for name in registry.roster)


def test_no_unexpected_duplicate_ports_in_real_repo_state():
    registry = build()
    ports_to_services = {}
    for svc in registry.services.values():
        if svc.host_port:
            ports_to_services.setdefault(svc.host_port, set()).add(svc.name)

    for port, names in ports_to_services.items():
        if len(names) <= 1:
            continue
        allowed = registry.allowed_collisions.get(port)
        assert allowed and names <= allowed, (
            f"unexpected duplicate port {port}: {sorted(names)} — either a "
            f"real collision needing a compose fix, or a new intentional "
            f"pair missing from fleet_overlay.yml's allowed_collisions"
        )


def test_check_expected_ports_script_passes():
    import check_expected_ports

    try:
        check_expected_ports.main()
    except SystemExit as e:
        raise AssertionError(f"check_expected_ports.py failed: exit code {e.code}")


def test_check_duplicate_ports_script_passes():
    import check_duplicate_ports

    try:
        check_duplicate_ports.main()
    except SystemExit as e:
        raise AssertionError(f"check_duplicate_ports.py failed: exit code {e.code}")
