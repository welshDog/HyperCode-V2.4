"""Card (b) — the honesty check that turns a "read_only" registry claim into
a proof against the committed compose manifests.

RED-first: every test here fails until
.github/scripts/check_readonly_executor_capabilities.py exists.
"""
import os

import pytest

from check_readonly_executor_capabilities import CheckError, collect_violations, main

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _p(*names):
    return [os.path.join(FIX, n) for n in names]


# --------------------------------------------------------------------------- #
# clean case
# --------------------------------------------------------------------------- #
def test_clean_readonly_agent_has_no_violations():
    violations = collect_violations(
        os.path.join(FIX, "readonly_registry_clean.json"),
        _p("compose_readonly_clean.yml"),
    )
    assert violations == []


def test_mutation_agent_is_not_inspected():
    # coder-studio is registered "mutation" and carries docker.sock + DOCKER_HOST
    # in the same fixture — the check must ignore it. Only "read_only" claims
    # get proven.
    violations = collect_violations(
        os.path.join(FIX, "readonly_registry_clean.json"),
        _p("compose_readonly_clean.yml"),
    )
    assert not any("coder-studio" in v for v in violations)


# --------------------------------------------------------------------------- #
# grant detection
# --------------------------------------------------------------------------- #
def test_docker_sock_mount_is_a_violation():
    violations = collect_violations(
        os.path.join(FIX, "readonly_registry_dirty.json"),
        _p("compose_readonly_dirty.yml"),
    )
    assert any("docker.sock" in v for v in violations)


def test_docker_host_env_is_a_violation():
    violations = collect_violations(
        os.path.join(FIX, "readonly_registry_dirty.json"),
        _p("compose_readonly_dirty.yml"),
    )
    assert any("DOCKER_HOST" in v for v in violations)


def test_github_token_env_is_a_violation():
    violations = collect_violations(
        os.path.join(FIX, "readonly_registry_dirty.json"),
        _p("compose_readonly_dirty.yml"),
    )
    assert any("GITHUB_TOKEN" in v for v in violations)


def test_writable_host_bind_mount_is_a_violation():
    violations = collect_violations(
        os.path.join(FIX, "readonly_registry_dirty.json"),
        _p("compose_readonly_writemount.yml"),
    )
    assert any("/workspace" in v and "leaky-agent" in v for v in violations)


def test_read_only_bind_mount_is_not_a_violation():
    violations = collect_violations(
        os.path.join(FIX, "readonly_registry_dirty.json"),
        _p("compose_readonly_writemount.yml"),
    )
    assert not any("/app/shared" in v for v in violations)


def test_env_file_secret_is_a_violation():
    violations = collect_violations(
        os.path.join(FIX, "readonly_registry_dirty.json"),
        _p("compose_readonly_envfile.yml"),
    )
    assert any("AWS_SECRET_ACCESS_KEY" in v for v in violations)


def test_unreadable_env_file_is_a_violation():
    # An env_file that can't be read (gitignored .env absent in CI) is an
    # unprovable claim for a read_only agent -> violation, same doctrine as
    # service-not-found.
    violations = collect_violations(
        os.path.join(FIX, "readonly_registry_dirty.json"),
        _p("compose_readonly_missing_envfile.yml"),
    )
    assert any("could not be read" in v and "leaky-agent" in v for v in violations)


# --------------------------------------------------------------------------- #
# fail-loud on unprovable claims
# --------------------------------------------------------------------------- #
def test_read_only_service_not_found_raises():
    with pytest.raises(CheckError, match="ghost-agent"):
        collect_violations(
            os.path.join(FIX, "readonly_registry_ghost.json"),
            _p("compose_readonly_clean.yml"),
        )


def test_mutation_key_not_found_also_raises():
    # Roster drift: a typo'd key of ANY capability must fail visibly, not be
    # silently absorbed by deny-first.
    with pytest.raises(CheckError, match="phantom-mutation"):
        collect_violations(
            os.path.join(FIX, "readonly_registry_mutation_ghost.json"),
            _p("compose_readonly_clean.yml"),
        )


def test_dispatch_capability_registry_env_is_not_read():
    # DISPATCH_CAPABILITY_REGISTRY is dev/test-only for card (d)'s module; the
    # CI honesty check must never let the registry path be redirected by env.
    import inspect

    import check_readonly_executor_capabilities as m

    assert "DISPATCH_CAPABILITY_REGISTRY" not in inspect.getsource(m)


def test_missing_registry_raises():
    with pytest.raises(CheckError):
        collect_violations(
            os.path.join(FIX, "does_not_exist.json"),
            _p("compose_readonly_clean.yml"),
        )


def test_unparseable_registry_raises():
    with pytest.raises(CheckError):
        collect_violations(
            os.path.join(FIX, "readonly_registry_bad.json"),
            _p("compose_readonly_clean.yml"),
        )


# --------------------------------------------------------------------------- #
# exit codes
# --------------------------------------------------------------------------- #
def test_main_exits_nonzero_on_violations():
    rc = main(
        [
            "--registry",
            os.path.join(FIX, "readonly_registry_dirty.json"),
            "--compose",
            os.path.join(FIX, "compose_readonly_dirty.yml"),
        ]
    )
    assert rc != 0


def test_main_exits_zero_when_clean():
    rc = main(
        [
            "--registry",
            os.path.join(FIX, "readonly_registry_clean.json"),
            "--compose",
            os.path.join(FIX, "compose_readonly_clean.yml"),
        ]
    )
    assert rc == 0


def test_main_exits_nonzero_on_missing_registry():
    rc = main(
        [
            "--registry",
            os.path.join(FIX, "nope.json"),
            "--compose",
            os.path.join(FIX, "compose_readonly_clean.yml"),
        ]
    )
    assert rc != 0
