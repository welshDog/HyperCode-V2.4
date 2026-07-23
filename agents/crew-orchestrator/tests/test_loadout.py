"""TDD tests for the crew-orchestrator loadout injection helper (loadout.py)."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from loadout import resolve_loadout_skills, loadout_block  # noqa: E402

REGISTRY = {"skills": [
    {"id": "HS-098", "hero_name": "THE SACRED SIX", "emoji": "⚖️", "description": "6 laws", "status": "active"},
    {"id": "HS-085", "hero_name": "THE FIVE WARDS", "description": "guardrails", "status": "active"},
    {"id": "HS-069", "hero_name": "MERCY MESSAGE", "description": "nd copy", "status": "active"},
    {"id": "HS-032", "hero_name": "COURSE RULES", "description": "course", "status": "active"},
    {"id": "HS-900", "hero_name": "OLD THING", "description": "old", "status": "deprecated"},
]}
LOADOUTS = {
    "_defaults": {"required": ["HS-098", "HS-085"], "optional": ["HS-069"]},
    "agents": {
        "broski-bot": {"required": ["HS-032"], "forbidden": ["HS-069"]},
        "needs-dead": {"required": ["HS-900"]},
    },
}


@pytest.fixture
def files(tmp_path):
    lo = tmp_path / "agent-loadouts.json"
    reg = tmp_path / "skills-registry.json"
    lo.write_text(json.dumps(LOADOUTS), encoding="utf-8")
    reg.write_text(json.dumps(REGISTRY), encoding="utf-8")
    return str(lo), str(reg)


def test_resolves_defaults_plus_agent(files):
    lo, reg = files
    ids = {s["id"] for s in resolve_loadout_skills("broski-bot", lo, reg)}
    assert ids == {"HS-098", "HS-085", "HS-032"}


def test_none_agent_gets_defaults(files):
    lo, reg = files
    ids = {s["id"] for s in resolve_loadout_skills(None, lo, reg)}
    assert ids == {"HS-098", "HS-085", "HS-069"}


def test_forbidden_is_excluded(files):
    lo, reg = files
    ids = {s["id"] for s in resolve_loadout_skills("broski-bot", lo, reg)}
    assert "HS-069" not in ids


def test_dead_status_is_excluded(files):
    lo, reg = files
    ids = {s["id"] for s in resolve_loadout_skills("needs-dead", lo, reg)}
    assert "HS-900" not in ids


def test_fail_open_on_missing_files():
    assert resolve_loadout_skills("broski-bot", "/nope/lo.json", "/nope/reg.json") == []


def test_block_empty_for_no_skills():
    assert loadout_block([]) == ""


def test_block_renders_ids_and_header(files):
    lo, reg = files
    block = loadout_block(resolve_loadout_skills("broski-bot", lo, reg))
    assert "HS-098" in block
    assert "Loadout" in block
