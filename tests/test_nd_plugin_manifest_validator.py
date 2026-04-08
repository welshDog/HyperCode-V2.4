from __future__ import annotations

import json
from pathlib import Path


from scripts.validate_nd_plugin_manifest import validate_manifest


def test_template_manifest_validates_against_schema() -> None:
    repo = Path(__file__).resolve().parents[1]
    schema = repo / "config" / "nd_plugin_manifest.schema.json"
    manifest = repo / "templates" / "mcp-plugin-python" / "manifest.json"
    errors = validate_manifest(manifest, schema)
    assert errors == []


def test_validator_reports_missing_required_field(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    schema = repo / "config" / "nd_plugin_manifest.schema.json"

    bad = {
        "name": "x",
        "version": "0.0.1",
        "author": "y",
        "tools": [
            {
                "name": "t",
                "description": "d",
                "parameters": {"type": "object", "properties": {}, "required": []},
            }
        ],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(bad), encoding="utf-8")
    errors = validate_manifest(p, schema)
    assert errors
    assert "nd_metadata" in errors[0]

