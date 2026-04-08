import argparse
import datetime as dt
import pathlib
import shutil
import sqlite3
import sys


def _connect(db_path: pathlib.Path) -> sqlite3.Connection:
    return sqlite3.connect(str(db_path))


def _alert_tables(cur: sqlite3.Cursor) -> list[str]:
    return [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'alert%'").fetchall()]


def _table_exists(cur: sqlite3.Cursor, name: str) -> bool:
    return cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def _count(cur: sqlite3.Cursor, table: str) -> int:
    return int(cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _integrity(cur: sqlite3.Cursor) -> str:
    return str(cur.execute("PRAGMA integrity_check").fetchone()[0])


def _snapshot(cur: sqlite3.Cursor) -> dict[str, int]:
    snap: dict[str, int] = {}
    for t in _alert_tables(cur):
        snap[t] = _count(cur, t)
    return snap


def _health_findings(cur: sqlite3.Cursor) -> dict[str, int]:
    findings: dict[str, int] = {}
    if _table_exists(cur, "alert_rule"):
        findings["alert_rule_blank_guid"] = int(cur.execute("SELECT COUNT(*) FROM alert_rule WHERE guid IS NULL OR guid = ''").fetchone()[0])
    if _table_exists(cur, "alert_rule_version"):
        findings["alert_rule_version_blank_rule_guid"] = int(cur.execute("SELECT COUNT(*) FROM alert_rule_version WHERE rule_guid IS NULL OR rule_guid = ''").fetchone()[0])
    if _table_exists(cur, "alert_rule") and _table_exists(cur, "alert_rule_version"):
        findings["alert_rule_version_orphan_rule_guid"] = int(
            cur.execute(
                "SELECT COUNT(*) FROM alert_rule_version v LEFT JOIN alert_rule r ON r.guid=v.rule_guid WHERE v.rule_guid != '' AND r.guid IS NULL"
            ).fetchone()[0]
        )
        findings["alert_rule_version_orphan_by_uid"] = int(
            cur.execute(
                "SELECT COUNT(*) FROM alert_rule_version v LEFT JOIN alert_rule r ON r.uid=v.rule_uid AND r.org_id=v.rule_org_id WHERE r.uid IS NULL"
            ).fetchone()[0]
        )
    return findings


def backup(db_path: pathlib.Path, backup_dir: pathlib.Path) -> pathlib.Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    dst = backup_dir / f"grafana.db.{ts}.bak"
    shutil.copy2(db_path, dst)
    return dst


def reset_alerting(db_path: pathlib.Path, vacuum: bool) -> None:
    con = _connect(db_path)
    cur = con.cursor()
    cur.execute("PRAGMA foreign_keys=OFF")
    for t in _alert_tables(cur):
        cur.execute(f"DELETE FROM {t}")
    con.commit()
    if vacuum:
        cur.execute("VACUUM")
        con.commit()
    con.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--backup-dir", default=str(pathlib.Path("reports") / "grafana" / "backup"))
    ap.add_argument("--reset-alerting", action="store_true")
    ap.add_argument("--vacuum", action="store_true")
    args = ap.parse_args()

    db_path = pathlib.Path(args.db)
    if not db_path.exists():
        print(f"not found: {db_path}", file=sys.stderr)
        return 2

    backup_path = backup(db_path, pathlib.Path(args.backup_dir))
    print(f"backup: {backup_path}")

    con = _connect(db_path)
    cur = con.cursor()
    print(f"integrity: {_integrity(cur)}")
    snap_before = _snapshot(cur)
    findings_before = _health_findings(cur)
    con.close()

    print("alert_tables_counts_before:")
    for k in sorted(snap_before.keys()):
        print(f"  {k}: {snap_before[k]}")
    print("findings_before:")
    for k in sorted(findings_before.keys()):
        print(f"  {k}: {findings_before[k]}")

    if args.reset_alerting:
        reset_alerting(db_path, vacuum=bool(args.vacuum))
        con = _connect(db_path)
        cur = con.cursor()
        print(f"integrity_after: {_integrity(cur)}")
        snap_after = _snapshot(cur)
        findings_after = _health_findings(cur)
        con.close()
        print("alert_tables_counts_after:")
        for k in sorted(snap_after.keys()):
            print(f"  {k}: {snap_after[k]}")
        print("findings_after:")
        for k in sorted(findings_after.keys()):
            print(f"  {k}: {findings_after[k]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
