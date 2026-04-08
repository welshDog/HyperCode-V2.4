import argparse
import pathlib
import re
import sys


UID_RE = re.compile(r'^\s*-\s*uid:\s*(?P<uid>"[^"]+"|[^#\s]+)\s*(#.*)?$')


def _strip_quotes(v: str) -> str:
    v = v.strip()
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        return v[1:-1]
    return v


def _load_lines(path: pathlib.Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines(keepends=False)


def _write_lines(path: pathlib.Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _collect_rule_uids(alert_rules_path: pathlib.Path) -> tuple[list[tuple[int, str]], list[str]]:
    lines = _load_lines(alert_rules_path)
    found: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        m = UID_RE.match(line)
        if not m:
            continue
        uid = _strip_quotes(m.group("uid"))
        found.append((i, uid))
    return found, lines


def _make_unique(uids: list[str], base: str) -> str:
    if base not in uids:
        return base
    n = 2
    while True:
        candidate = f"{base}_{n}"
        if candidate not in uids:
            return candidate
        n += 1


def validate_and_optionally_fix(alert_rules_path: pathlib.Path, fix: bool) -> int:
    found, lines = _collect_rule_uids(alert_rules_path)
    if not found:
        print(f"{alert_rules_path}: no rule uids found")
        return 0

    seen: dict[str, int] = {}
    duplicates: list[tuple[int, str]] = []
    empties: list[int] = []

    for line_idx, uid in found:
        if uid == "":
            empties.append(line_idx)
            continue
        if uid in seen:
            duplicates.append((line_idx, uid))
        else:
            seen[uid] = line_idx

    if not duplicates and not empties:
        print(f"{alert_rules_path}: ok ({len(found)} rules, uids unique)")
        return 0

    if not fix:
        if empties:
            print(f"{alert_rules_path}: empty uid on lines: {', '.join(str(i+1) for i in empties)}")
        if duplicates:
            print(f"{alert_rules_path}: duplicate uids:")
            for i, uid in duplicates:
                print(f"  line {i+1}: {uid}")
        return 1

    uid_list = [uid for _, uid in found if uid != ""]
    for line_idx, uid in duplicates:
        new_uid = _make_unique(uid_list, uid)
        uid_list.append(new_uid)
        lines[line_idx] = re.sub(r'(\buid:\s*)(?P<v>"[^"]+"|[^#\s]+)', lambda m: m.group(1) + new_uid, lines[line_idx], count=1)

    for line_idx in empties:
        new_uid = _make_unique(uid_list, "rule")
        uid_list.append(new_uid)
        lines[line_idx] = re.sub(r'(\buid:\s*)(?P<v>"[^"]+"|[^#\s]*)', lambda m: m.group(1) + new_uid, lines[line_idx], count=1)

    _write_lines(alert_rules_path, lines)
    print(f"{alert_rules_path}: fixed (updated uids to be unique)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--alert-rules",
        default=str(pathlib.Path("monitoring") / "grafana" / "provisioning" / "alerting" / "alert-rules.yaml"),
    )
    ap.add_argument("--fix", action="store_true")
    args = ap.parse_args()

    path = pathlib.Path(args.alert_rules)
    if not path.exists():
        print(f"not found: {path}", file=sys.stderr)
        return 2

    return validate_and_optionally_fix(path, fix=bool(args.fix))


if __name__ == "__main__":
    raise SystemExit(main())
