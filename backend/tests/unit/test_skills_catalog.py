from pathlib import Path

import pytest


def _write_skill(dir_path: Path, name: str, content: str) -> None:
    """Helper: write a fake SKILL.md under dir_path/name/SKILL.md."""
    skill_dir = dir_path / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")


def test_load_catalog_parses_valid_frontmatter(tmp_path):
    """Test load catalog parses valid frontmatter."""
    from app.api.v1.endpoints.skills import _load_catalog_from

    _write_skill(
        tmp_path,
        "cve-trivy-scan",
        "---\nname: cve-trivy-scan\ndescription: Scans containers for CVEs with Trivy.\n---\n\n# Body\n",
    )

    catalog = _load_catalog_from(tmp_path)

    assert catalog == [
        {"name": "cve-trivy-scan", "description": "Scans containers for CVEs with Trivy."}
    ]


def test_load_catalog_skips_missing_description(tmp_path):
    """Test load catalog skips missing description."""
    from app.api.v1.endpoints.skills import _load_catalog_from

    _write_skill(tmp_path, "no-description", "---\nname: no-description\n---\n\n# Body\n")
    _write_skill(
        tmp_path,
        "good-skill",
        "---\nname: good-skill\ndescription: A perfectly fine skill.\n---\n",
    )

    catalog = _load_catalog_from(tmp_path)

    assert catalog == [{"name": "good-skill", "description": "A perfectly fine skill."}]


def test_load_catalog_skips_malformed_yaml(tmp_path):
    """Test load catalog skips malformed yaml."""
    from app.api.v1.endpoints.skills import _load_catalog_from

    _write_skill(
        tmp_path,
        "broken-yaml",
        "---\nname: [this is not valid: yaml\ndescription: broken\n---\n",
    )
    _write_skill(
        tmp_path,
        "good-skill",
        "---\nname: good-skill\ndescription: A perfectly fine skill.\n---\n",
    )

    catalog = _load_catalog_from(tmp_path)

    assert catalog == [{"name": "good-skill", "description": "A perfectly fine skill."}]


def test_load_catalog_skips_missing_frontmatter_delimiters(tmp_path):
    """Test load catalog skips a SKILL.md with no frontmatter block at all."""
    from app.api.v1.endpoints.skills import _load_catalog_from

    _write_skill(tmp_path, "no-frontmatter", "# Just a heading\n\nSome body text.\n")

    catalog = _load_catalog_from(tmp_path)

    assert catalog == []


def test_load_catalog_returns_empty_list_for_missing_directory(tmp_path):
    """Test load catalog returns empty list for a nonexistent directory."""
    from app.api.v1.endpoints.skills import _load_catalog_from

    catalog = _load_catalog_from(tmp_path / "does-not-exist")

    assert catalog == []


def test_load_catalog_parses_the_real_repo_catalog():
    """Sanity check against this repo's actual .claude/skills/ — every real
    SKILL.md should parse. Catches the class of bug where a plain-YAML
    quirk (e.g. an unquoted colon in a description) silently drops a real
    skill from search results without any test noticing."""
    from app.api.v1.endpoints.skills import _load_catalog_from, _REPO_ROOT_FALLBACK

    catalog = _load_catalog_from(_REPO_ROOT_FALLBACK)

    on_disk_count = len(list(_REPO_ROOT_FALLBACK.glob("*/SKILL.md")))
    assert on_disk_count > 0, "expected the real .claude/skills directory to exist with content"
    assert len(catalog) == on_disk_count, (
        f"{on_disk_count - len(catalog)} real SKILL.md file(s) failed to parse — "
        "check the warnings log for which ones and why"
    )


@pytest.fixture
def sample_catalog():
    """Fixture: a small fixed catalog for fallback-matcher tests."""
    return [
        {
            "name": "hypercode-broski-discord-bot",
            "description": "Builds and maintains the BROski Discord bot including moderation commands.",
        },
        {
            "name": "cve-trivy-scan",
            "description": "Scans containers for CVEs with Trivy.",
        },
        {
            "name": "docker-stack-ops",
            "description": "Running, rebuilding, and debugging the HyperCode Docker stack.",
        },
    ]


def test_fallback_match_matches_on_name(sample_catalog):
    """Test fallback match matches on name."""
    from app.api.v1.endpoints.skills import _fallback_match

    matches = _fallback_match("I need to check for CVEs", sample_catalog)

    assert any(m["name"] == "cve-trivy-scan" for m in matches)


def test_fallback_match_matches_on_description(sample_catalog):
    """Test fallback match matches on description."""
    from app.api.v1.endpoints.skills import _fallback_match

    matches = _fallback_match("deploy a discord bot with moderation", sample_catalog)

    assert any(m["name"] == "hypercode-broski-discord-bot" for m in matches)


def test_fallback_match_never_returns_empty(sample_catalog):
    """Test fallback match always returns something, even with no keyword overlap."""
    from app.api.v1.endpoints.skills import _fallback_match

    matches = _fallback_match("something totally unrelated to anything", sample_catalog)

    assert len(matches) > 0


def test_fallback_match_each_result_has_name_and_rationale(sample_catalog):
    """Test fallback match results have the same shape as the LLM-ranked path."""
    from app.api.v1.endpoints.skills import _fallback_match

    matches = _fallback_match("docker rebuild", sample_catalog)

    for m in matches:
        assert "name" in m
        assert "rationale" in m
