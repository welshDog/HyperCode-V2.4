"""The deny-first routing decision — pure logic, no Shepherd, no network.

This is card (d): the smallest safe commit. It proves the classification seam
resolves correctly for every input class BEFORE anything is wired into the live
dispatch path or the gate default is touched.
"""

import json

import pytest

import dispatch_capability as dc


_REGISTRY = {"qa-engineer": "read_only", "coder-studio": "mutation"}


@pytest.mark.parametrize(
    "agent, expected",
    [
        ("qa-engineer", dc.READ_ONLY),       # explicitly registered read_only
        ("coder-studio", dc.MUTATION),       # explicitly registered mutation
        ("brand-new-agent", dc.MUTATION),    # unregistered  -> deny-first
        ("", dc.MUTATION),                   # blank name    -> deny-first
    ],
)
def test_classify_matrix(agent, expected):
    assert dc.classify(agent, _REGISTRY) == expected


def test_unknown_capability_value_never_leaks_read_only():
    # A typo or a novel class must not be trusted as read_only.
    assert dc.classify("x", {"x": "readonly"}) == dc.MUTATION
    assert dc.classify("x", {"x": "RO"}) == dc.MUTATION
    assert dc.classify("x", {"x": True}) == dc.MUTATION


def test_needs_strict_path_is_the_inverse_of_read_only():
    assert dc.needs_strict_path("coder-studio", _REGISTRY) is True
    assert dc.needs_strict_path("qa-engineer", _REGISTRY) is False
    assert dc.needs_strict_path("unlisted", _REGISTRY) is True


def test_missing_registry_file_means_all_mutation(tmp_path):
    reg = dc.load_registry(tmp_path / "nope.json")
    assert reg == {}
    assert dc.classify("qa-engineer", reg) == dc.MUTATION


def test_unparseable_registry_means_all_mutation(tmp_path):
    bad = tmp_path / "reg.json"
    bad.write_text("{ not json", encoding="utf-8")
    assert dc.load_registry(bad) == {}


def test_non_object_registry_means_all_mutation(tmp_path):
    arr = tmp_path / "reg.json"
    arr.write_text(json.dumps(["qa-engineer"]), encoding="utf-8")
    assert dc.load_registry(arr) == {}


def test_load_registry_normalises_every_value(tmp_path):
    p = tmp_path / "reg.json"
    p.write_text(
        json.dumps({"a": "read_only", "b": "mutation", "c": "bogus", "d": 3}),
        encoding="utf-8",
    )
    assert dc.load_registry(p) == {
        "a": "read_only",
        "b": "mutation",
        "c": "mutation",
        "d": "mutation",
    }


def test_default_path_is_env_overridable(tmp_path, monkeypatch):
    p = tmp_path / "custom.json"
    p.write_text(json.dumps({"reporter": "read_only"}), encoding="utf-8")
    monkeypatch.setenv("DISPATCH_CAPABILITY_REGISTRY", str(p))
    # load_registry() with no arg must read the env-pointed file
    import importlib

    importlib.reload(dc)
    assert dc.classify("reporter") == dc.READ_ONLY
    assert dc.classify("someone-else") == dc.MUTATION
    importlib.reload(dc)  # restore module default for other tests
