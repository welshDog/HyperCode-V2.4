import argparse
import subprocess
from getpass import getpass
import secrets
from typing import Optional

import bcrypt


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="link_discord_user.py")
    sub = p.add_subparsers(dest="cmd")

    link = sub.add_parser("link", help="Link a Discord ID to a HyperCode user")
    link.add_argument("--email", required=True)
    link.add_argument("--discord-id", required=True)
    link.add_argument("--full-name", default=None)

    reset = sub.add_parser(
        "reset-password",
        help="Reset/lock the hashed_password for a HyperCode user (local postgres container)",
    )
    reset.add_argument("--email", default=None)
    reset.add_argument("--discord-id", default=None)
    reset.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt for a new password (recommended if you need to login). Default is lock-only.",
    )

    args = p.parse_args()
    if args.cmd is None:
        args.cmd = "link"
    return args


def _q(s: str) -> str:
    return s.replace("'", "''")


def _run_psql(sql: str) -> tuple[int, str]:
    cmd = [
        "docker",
        "exec",
        "-i",
        "postgres",
        "psql",
        "-U",
        "postgres",
        "-d",
        "hypercode",
        "-v",
        "ON_ERROR_STOP=1",
        "-c",
        sql,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    out = (res.stdout or "") + (res.stderr or "")
    return res.returncode, out.strip()


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _read_new_password() -> str:
    pw1 = getpass("New password: ")
    pw2 = getpass("Confirm password: ")
    if pw1 != pw2:
        raise ValueError("passwords_do_not_match")
    if len(pw1) < 12:
        raise ValueError("password_too_short")
    return pw1


def _cmd_link(*, email: str, discord_id: str, full_name: Optional[str]) -> int:
    email_q = _q(email)
    discord_id_q = _q(discord_id)
    full_name_q = _q(full_name or "")

    placeholder_hash = "$2b$12$7wXZ4o8ABSXoiBJoModlgefy8pp0G1XITe.leZHPL5EXi.Dh1rw0q"

    sql = f"""
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM users WHERE discord_id = '{discord_id_q}'
    AND email <> '{email_q}'
  ) THEN
    RAISE EXCEPTION 'discord_id_already_linked';
  END IF;

  IF EXISTS (SELECT 1 FROM users WHERE email = '{email_q}') THEN
    UPDATE users
    SET discord_id = '{discord_id_q}', updated_at = NOW()
    WHERE email = '{email_q}';
  ELSE
    INSERT INTO users (email, hashed_password, full_name, discord_id)
    VALUES ('{email_q}', '{placeholder_hash}', NULLIF('{full_name_q}', ''),
            '{discord_id_q}');
  END IF;
END $$;
""".strip()

    code, out = _run_psql(sql)
    if code != 0:
        if "discord_id_already_linked" in out:
            print("error:discord_id_already_linked")
            return 2
        print("error:psql_failed")
        return 1

    print("ok:linked")
    return 0


def _cmd_reset_password(*, email: Optional[str], discord_id: Optional[str], interactive: bool) -> int:
    email_q = _q(email or "")
    discord_id_q = _q(discord_id or "")

    if not email_q and not discord_id_q:
        print("error:email_or_discord_id_required")
        return 2

    if interactive:
        try:
            new_pw = _read_new_password()
        except ValueError as e:
            print(f"error:{e}")
            return 2
        new_hash = _hash_password(new_pw)
    else:
        new_hash = _hash_password(secrets.token_urlsafe(48))

    new_hash_q = _q(new_hash)

    where = []
    if email_q:
        where.append(f"email = '{email_q}'")
    if discord_id_q:
        where.append(f"discord_id = '{discord_id_q}'")
    where_sql = " OR ".join(where)

    sql = f"""
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM users WHERE {where_sql}) THEN
    RAISE EXCEPTION 'user_not_found';
  END IF;

  UPDATE users
  SET hashed_password = '{new_hash_q}', updated_at = NOW()
  WHERE {where_sql};
END $$;
""".strip()

    code, out = _run_psql(sql)
    if code != 0:
        if "user_not_found" in out:
            print("error:user_not_found")
            return 2
        print("error:psql_failed")
        return 1

    print("ok:password_reset")
    return 0


def main() -> int:
    args = _parse_args()
    if args.cmd == "reset-password":
        return _cmd_reset_password(
            email=args.email,
            discord_id=args.discord_id,
            interactive=bool(args.interactive),
        )
    return _cmd_link(email=args.email, discord_id=args.discord_id, full_name=args.full_name)


if __name__ == "__main__":
    raise SystemExit(main())
