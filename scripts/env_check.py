import argparse
import os
import re
import sys
from collections import Counter
from pathlib import Path


def parse_env(path: Path) -> tuple[dict[str, str], list[str]]:
    entries: list[tuple[str, str]] = []
    if not path.exists():
        return {}, []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("export "):
            s = s[len("export ") :]
        if "=" not in s:
            continue
        k, v = s.split("=", 1)
        entries.append((k.strip(), v.strip()))

    keys = [k for k, _ in entries]
    dup = sorted([k for k, c in Counter(keys).items() if c > 1])
    env_kv: dict[str, str] = {}
    for k, v in entries:
        env_kv[k] = v
    return env_kv, dup


def resolve_root(provided: str | None) -> Path:
    if provided:
        return Path(provided).resolve()
    return Path(__file__).resolve().parents[1]


def resolve_files(args, root_dir: Path) -> list[Path]:
    files: list[str] = []

    if args.files:
        files.extend(args.files)
    else:
        if args.core:
            files.append("docker-compose.yml")
        if args.secrets:
            files.append("docker-compose.secrets.yml")
        if args.brain:
            files.append("docker-compose.brain.yml")
        if args.grafana_cloud:
            files.append("docker-compose.grafana-cloud.yml")

    if not files:
        files = ["docker-compose.yml"]

    out: list[Path] = []
    for f in files:
        p = Path(f)
        out.append(p if p.is_absolute() else root_dir / p)
    return out


def scan_compose_vars(compose_paths: list[Path]) -> tuple[set[str], set[str], list[str]]:
    var_re = re.compile(r"\$\{([A-Z0-9_]+)(?::([?\-])([^}]*))?\}")
    required: set[str] = set()
    optional: set[str] = set()
    errors: list[str] = []

    for cp in compose_paths:
        if not cp.exists():
            errors.append(f"missing_compose_file:{cp}")
            continue
        for line in cp.read_text(encoding="utf-8", errors="ignore").splitlines():
            for (name, mod, _default) in var_re.findall(line):
                if mod == "-":
                    optional.add(name)
                else:
                    required.add(name)

    required_effective = set(required)
    optional_effective = set(optional - required_effective)
    return required_effective, optional_effective, errors


def secrets_enabled(compose_paths: list[Path]) -> bool:
    return any(p.name == "docker-compose.secrets.yml" for p in compose_paths)


def scan_secrets_files(root_dir: Path, secrets_compose: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not secrets_compose.exists():
        errors.append(f"missing_compose_file:{secrets_compose}")
        return errors, warnings

    in_secrets = False
    secret_files: list[Path] = []

    for raw in secrets_compose.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.rstrip("\n")
        stripped = line.lstrip(" ")
        indent = len(line) - len(stripped)

        if indent == 0 and stripped.startswith("secrets:"):
            in_secrets = True
            continue

        if in_secrets and indent == 0 and stripped and not stripped.startswith("secrets:"):
            in_secrets = False

        if not in_secrets:
            continue

        if indent >= 4 and stripped.startswith("file:"):
            _k, _sep, val = stripped.partition(":")
            file_path = val.strip()
            if file_path.startswith("./"):
                file_path = file_path[2:]
            fp = Path(file_path)
            if not fp.is_absolute():
                fp = root_dir / fp
            secret_files.append(fp)

    for fp in secret_files:
        if not fp.exists():
            errors.append(f"missing_secret_file:{fp}")
            continue
        content = fp.read_text(encoding="utf-8", errors="ignore")
        if content.strip() == "":
            errors.append(f"empty_secret_file:{fp}")
            continue
        low = content.lower()
        if any(token in low for token in ["paste_", "your_", "changeme"]):
            warnings.append(f"placeholder_secret_file:{fp}")

    return errors, warnings


def discord_enabled(profiles: list[str]) -> bool:
    return any(p == "discord" for p in profiles)


def parse_env_keys(path: Path) -> set[str]:
    env_kv, _dup = parse_env(path)
    return set(env_kv.keys())


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--help", "-h", action="store_true")
    parser.add_argument("--root")
    parser.add_argument("--files", nargs="+")
    parser.add_argument("--profile", action="append", default=[])
    parser.add_argument("--core", action="store_true")
    parser.add_argument("--secrets", action="store_true")
    parser.add_argument("--brain", action="store_true")
    parser.add_argument("--grafana-cloud", dest="grafana_cloud", action="store_true")
    args, unknown = parser.parse_known_args(argv)

    if unknown:
        print(f"Unknown args: {' '.join(unknown)}")
        return 2

    if args.help:
        print(
            "Usage:\n"
            "  python scripts/env_check.py [--root <path>] [--files <compose...>] [--profile <name>...]\n"
            "  python scripts/env_check.py [--root <path>] [--core] [--secrets] [--brain] [--grafana-cloud] [--profile <name>...]\n"
        )
        return 0

    root_dir = resolve_root(args.root)
    compose_paths = resolve_files(args, root_dir)
    profiles = [p for p in args.profile if p]

    errors: list[str] = []
    warnings: list[str] = []

    env_path = root_dir / ".env"
    env_kv, dup_keys = parse_env(env_path)
    env_key_set = set(env_kv.keys())

    if not env_path.exists():
        errors.append(f"missing_root_env:{env_path}")
    for k in dup_keys:
        warnings.append(f"duplicate_key:{k}")

    req, opt, compose_errors = scan_compose_vars(compose_paths)
    errors.extend(compose_errors)

    for k in sorted(req):
        if k not in env_key_set:
            errors.append(f"missing_required_env_var:{k}")

    for k in sorted(opt):
        if k not in env_key_set:
            warnings.append(f"missing_optional_env_var:{k}")

    if secrets_enabled(compose_paths):
        secrets_compose = next((p for p in compose_paths if p.name == "docker-compose.secrets.yml"), None)
        if secrets_compose:
            e, w = scan_secrets_files(root_dir, secrets_compose)
            errors.extend(e)
            warnings.extend(w)

    if discord_enabled(profiles):
        bot_env = root_dir / "agents" / "broski-bot" / ".env"
        bot_env_example = root_dir / "agents" / "broski-bot" / ".env.example"
        if not bot_env.exists():
            errors.append(f"missing_broski_bot_env:{bot_env}")
        else:
            bot_keys = parse_env_keys(bot_env)
            example_keys = parse_env_keys(bot_env_example)

            docker_mode = secrets_enabled(compose_paths)
            missing = sorted(example_keys - bot_keys)

            if docker_mode:
                skip = {
                    "DISCORD_TOKEN",
                    "POSTGRES_PASSWORD",
                    "DB_HOST",
                    "DB_PORT",
                    "DB_NAME",
                    "DB_USER",
                    "REDIS_URL",
                    "HYPERCODE_CORE_URL",
                    "WORKSPACE_PATH",
                    "DISCORD_COMMAND_PREFIX",
                    "DISCORD_GUILD_ID",
                }
                missing = [k for k in missing if k not in skip]

                if "DISCORD_GUILD_ID" not in bot_keys:
                    warnings.append("missing_broski_bot_env_key:DISCORD_GUILD_ID")
            else:
                if "DISCORD_TOKEN" not in bot_keys:
                    errors.append("missing_broski_bot_env_key:DISCORD_TOKEN")

            for k in missing:
                errors.append(f"missing_broski_bot_env_key:{k}")

    print("Env Check — keys only")
    print(f"Root: {root_dir}")
    print("Files:")
    for cp in compose_paths:
        print(f"- {cp.name}")
    print("Profiles:")
    if profiles:
        for p in profiles:
            print(f"- {p}")
    else:
        print("- (none)")
    print("")

    if errors:
        print("ERRORS:")
        for e in errors:
            print(f"- {e}")
        print("")

    if warnings:
        print("WARNINGS:")
        for w in warnings:
            print(f"- {w}")
        print("")

    print(f"Summary: errors={len(errors)} warnings={len(warnings)}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
