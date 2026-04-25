from __future__ import annotations

import json
from pathlib import Path

import pytest


def _import_writer():
    import sys

    here = Path(__file__).resolve()
    sys.path.insert(0, str(here.parents[1]))
    import snapshot_writer  # type: ignore

    return snapshot_writer


def test_get_suggested_next_action_parses_next_up(tmp_path: Path) -> None:
    writer = _import_writer()

    (tmp_path / "WHATS_DONE.md").write_text(
        "\n".join(
            [
                "# WHATS_DONE",
                "",
                "## 🚀 NEXT UP (in order)",
                "",
                "1. First thing",
                "2. Second thing",
                "",
                "## Other",
                "- Not this",
            ]
        ),
        encoding="utf-8",
    )

    assert writer.get_suggested_next_action(tmp_path) == "First thing"


def test_get_last_test_result_reads_lastfailed(tmp_path: Path) -> None:
    writer = _import_writer()

    lastfailed = tmp_path / "backend" / ".pytest_cache" / "v" / "cache" / "lastfailed"
    lastfailed.parent.mkdir(parents=True, exist_ok=True)
    lastfailed.write_text(json.dumps({"tests/test_a.py::test_a": True}), encoding="utf-8")

    result = writer.get_last_test_result(tmp_path)
    assert result is not None
    assert "Failing tests detected" in result


def test_write_session_md_writes_expected_sections(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    writer = _import_writer()

    (tmp_path / "WHATS_DONE.md").write_text(
        "\n".join(
            [
                "## 🚀 NEXT UP (in order)",
                "- Do the next thing",
            ]
        ),
        encoding="utf-8",
    )

    def fake_run(cmd: list[str], cwd: Path):
        if cmd[:3] == ["git", "status", "--short"]:
            return 0, " M backend/app/main.py\n?? new_file.txt"
        if cmd[:3] == ["git", "log", "--oneline"]:
            return 0, "abc123 fix: something"
        return 1, "error"

    monkeypatch.setattr(writer, "_run", fake_run)

    out = writer.write_session_md(tmp_path, tmp_path / "SESSION.md")
    content = out.read_text(encoding="utf-8")

    assert "Welcome Back — Session Snapshot" in content
    assert "abc123 fix: something" in content
    assert "M backend/app/main.py" in content
    assert "?? new_file.txt" in content
    assert "Do the next thing" in content
