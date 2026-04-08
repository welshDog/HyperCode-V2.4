from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import jsonschema
except Exception as e:  # pragma: no cover
    raise SystemExit("jsonschema is required to run this validator") from e


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_manifest(manifest_path: Path, schema_path: Path) -> list[str]:
    errors: list[str] = []
    schema = _load_json(schema_path)
    manifest = _load_json(manifest_path)
    try:
        jsonschema.validate(instance=manifest, schema=schema)
    except jsonschema.ValidationError as e:
        loc = ".".join([str(p) for p in e.path]) if e.path else "<root>"
        errors.append(f"{manifest_path}: {loc}: {e.message}")
    except jsonschema.SchemaError as e:
        errors.append(f"Schema error: {e.message}")
    return errors


def _iter_manifest_paths(paths: list[str]) -> list[Path]:
    out: list[Path] = []
    for p in paths:
        pp = Path(p)
        if pp.is_file():
            out.append(pp)
            continue
        if pp.is_dir():
            out.extend(sorted(pp.rglob("manifest.json")))
            continue
        if any(ch in p for ch in ["*", "?", "["]):
            out.extend(sorted(Path().glob(p)))
            continue
        out.append(pp)
    uniq: dict[str, Path] = {}
    for p in out:
        uniq[str(p.resolve())] = p
    return list(uniq.values())


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Validate HyperCode ND plugin manifests (manifest.json).")
    parser.add_argument(
        "--schema",
        default=str(Path("config") / "nd_plugin_manifest.schema.json"),
        help="Path to JSON Schema for the manifest.",
    )
    parser.add_argument(
        "--paths",
        nargs="+",
        default=[str(Path("templates") / "mcp-plugin-python" / "manifest.json")],
        help="Files/directories/globs to validate (directories are searched for manifest.json).",
    )
    args = parser.parse_args(argv)

    schema_path = Path(args.schema)
    if not schema_path.exists():
        print(f"Schema not found: {schema_path}", file=sys.stderr)
        return 2

    manifest_paths = _iter_manifest_paths(args.paths)
    if not manifest_paths:
        print("No manifest files found.", file=sys.stderr)
        return 2

    all_errors: list[str] = []
    for mp in manifest_paths:
        if not mp.exists():
            all_errors.append(f"Missing manifest: {mp}")
            continue
        all_errors.extend(validate_manifest(mp, schema_path))

    if all_errors:
        for e in all_errors:
            print(e, file=sys.stderr)
        return 1

    print(f"ok: validated {len(manifest_paths)} manifest(s)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))

