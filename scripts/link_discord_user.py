import argparse
import subprocess


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--email", required=True)
    p.add_argument("--discord-id", required=True)
    p.add_argument("--full-name", default=None)
    return p.parse_args()


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


def main() -> int:
    args = _parse_args()
    email = _q(args.email)
    discord_id = _q(args.discord_id)
    full_name = _q(args.full_name or "")

    placeholder_hash = (
        "$2b$12$7wXZ4o8ABSXoiBJoModlgefy8pp0G1XITe.leZHPL5EXi.Dh1rw0q"
    )

    sql = f"""
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM users WHERE discord_id = '{discord_id}'
    AND email <> '{email}'
  ) THEN
    RAISE EXCEPTION 'discord_id_already_linked';
  END IF;

  IF EXISTS (SELECT 1 FROM users WHERE email = '{email}') THEN
    UPDATE users
    SET discord_id = '{discord_id}'
    WHERE email = '{email}';
  ELSE
    INSERT INTO users (email, hashed_password, full_name, discord_id)
    VALUES ('{email}', '{placeholder_hash}', NULLIF('{full_name}', ''),
            '{discord_id}');
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


if __name__ == "__main__":
    raise SystemExit(main())
