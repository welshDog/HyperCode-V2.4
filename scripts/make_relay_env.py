#!/usr/bin/env python3
"""Build the MINIMAL env file for the evolve-relay container (least privilege). Never prints a value.

Why: docker-compose.bropets.yml used to hand evolve-relay the Pets repo's WHOLE .env (~50 variables incl. the CDP
secret, GitHub token, Supabase service key, Anthropic key). The relay's code (evolve_relay.py, agent.py, metadata.py,
scripts/evolve_token.py, scripts/mint_all_eeps.py - the only files its Dockerfile copies) reads just these:

  required (scripts/evolve_token.py `_require_env`): SEPOLIA_RPC, CONTRACT_ADDRESS, DEPLOYER_KEY, PINATA_JWT
  optional, used by the evolve flow, all have code defaults: REDIS_HOST, REDIS_PORT, REDIS_PASSWORD (bridge XP/happiness),
                                                              IPFS_GATEWAY, IMAGES_ROOT_CID
  not copied: GROQ/LLM_* (chat code the relay never runs), AGENT_API_KEY (compose always sets HYPERCODE_API_KEY, which wins).

This copies ONLY those lines, byte for byte (so the compose dotenv parser reads them exactly as before), from the Pets
repo's .env into secrets/evolve_relay.env (gitignored). Run from HyperCode-V2.4/:

    MSYS_NO_PATHCONV=1 python scripts/make_relay_env.py            # dry run: names only, writes nothing
    MSYS_NO_PATHCONV=1 python scripts/make_relay_env.py --write

Output: variable NAMES and counts only. Exit 2 if a required variable is missing (nothing is written).
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

REQUIRED = ("SEPOLIA_RPC", "CONTRACT_ADDRESS", "DEPLOYER_KEY", "PINATA_JWT")
OPTIONAL = ("REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD", "IPFS_GATEWAY", "IMAGES_ROOT_CID")
ALLOWED = REQUIRED + OPTIONAL
_KEY_LINE = re.compile(r"^[ \t]*(?:export[ \t]+)?([A-Za-z_][A-Za-z0-9_]*)[ \t]*=")


def pick_lines(text: str, allowed=ALLOWED) -> tuple[list[str], list[str], int]:
    """(kept raw lines, names kept, number of variable lines dropped). The LAST assignment of a name wins, like dotenv."""
    last: dict[str, str] = {}
    total = 0
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        m = _KEY_LINE.match(raw)
        if not m:
            continue
        total += 1
        if m.group(1) in allowed:
            last[m.group(1)] = raw.rstrip("\r\n")
    kept = [last[k] for k in allowed if k in last]
    return kept, [k for k in allowed if k in last], total - len(last)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    root = Path.cwd()
    pets = (root / (os.environ.get("BROSKIPETS_DIR") or "../../BROskiPets-LLM-dNFT")).resolve()
    src, dst = pets / ".env", root / "secrets" / "evolve_relay.env"
    if not src.is_file():
        print(f"missing source env file: {src}")
        return 2
    kept, names, dropped = pick_lines(src.read_text(encoding="utf-8"))
    missing_req = [k for k in REQUIRED if k not in names]
    print(f"source: {src}")
    print(f"keeping {len(names)}: {', '.join(names)}")
    print(f"optional not present (code defaults apply): {[k for k in OPTIONAL if k not in names]}")
    print(f"NOT passed to the relay: {dropped} other variable(s)")
    if missing_req:
        print(f"REQUIRED variable(s) missing: {missing_req} - nothing written")
        return 2
    if not args.write:
        print("dry run - nothing written (re-run with --write)")
        return 0
    dst.parent.mkdir(exist_ok=True)
    dst.write_text("\n".join(kept) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {dst} ({len(kept)} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
