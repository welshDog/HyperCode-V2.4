#!/usr/bin/env python3
"""HyperFocus Z0ne - BROski$ Economy Consumer.

The consumer side of the hook XP loop. Subscribes to Redis channel
'broski_economy' (DB 1) and PERSISTS every xp_award into durable redis keys,
so XP totals survive and become queryable. Publishers are each repo's
broski_xp_reward.py (14 repos -- see hfz_ecosystem.py for the roster).

Redis lives on an internal Docker network (6379 not published to host -- Sacred
Rule: data-net internal), so this talks to it the same way the publishers do:
direct host TCP if available, else `docker exec <redis> redis-cli`.

Accepts BOTH publisher payload shapes:
  {"event": "xp_award", "xp": N, "reason": "...", "source": "...", "timestamp": "..."}
  {"type":  "xp_award", "xp": N, "reason": "...", "source": "...", "timestamp": "..."}

Persisted keys (DB 1):
  broski:xp:total       (string)  grand total XP banked
  broski:xp:count       (string)  number of awards processed
  broski:xp:by_source   (hash)    XP per source (repo hook)
  broski:xp:by_reason   (hash)    XP per reason
  broski:xp:last        (string)  ISO timestamp of the most recent award
  broski:xp:log         (stream)  capped history (MAXLEN ~2000)

Usage:
  python scripts/broski_economy_consumer.py            # listen + persist (Ctrl-C to stop)
  python scripts/broski_economy_consumer.py --seconds 15   # listen for N seconds then exit
  python scripts/broski_economy_consumer.py --stats    # print the leaderboard and exit
  python scripts/broski_economy_consumer.py --no-color
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime

_CHANNEL = "broski_economy"
_DB = 1  # Sacred Rule: DB 1 = cache
_CONTAINERS = ("redis", "hypercode-redis")  # internal redis -- 6379 not published to host
_LOG_MAXLEN = 2000

K_TOTAL = "broski:xp:total"
K_COUNT = "broski:xp:count"
K_BY_SOURCE = "broski:xp:by_source"
K_BY_REASON = "broski:xp:by_reason"
K_LAST = "broski:xp:last"
K_LOG = "broski:xp:log"
K_SEEN = "broski:xp:seen:"   # + source_id -> idempotency marker (dedup rebase replays)
_SEEN_TTL = 7776000         # 90d -- bound growth; old commits past this could re-award

# Durable postgres sink -- POST each award to hypercode-core, which routes it
# through broski_service.award_xp into broski_wallets/broski_transactions (the
# system of record). Redis stays the fast always-on path; postgres is the
# survives-anything ledger. Opt-in: fires only when BOTH are set, so an
# unconfigured deploy behaves exactly as before (redis-only).
def _read_secret(name, default=""):
    """`<name>_FILE` (a Compose/Docker secret file) wins; else the `<name>` env var; else default.

    Inlined on purpose: this script ships alone in a tiny image (see Dockerfile.broski-economy).
    """
    path = os.environ.get(name + "_FILE", "").strip()
    if path:
        try:
            with open(path, encoding="utf-8") as fh:
                value = fh.read().strip()
        except OSError:
            value = ""
        if value:
            return value
    return os.environ.get(name, default)


def _key_source(name):
    """Where the key comes from - 'file' | 'env' | 'none'. For the startup banner; never the value."""
    path = os.environ.get(name + "_FILE", "").strip()
    if path:
        try:
            with open(path, encoding="utf-8") as fh:
                if fh.read().strip():
                    return "file"
        except OSError:
            pass
    return "env" if os.environ.get(name) else "none"


_CORE_URL = os.environ.get("HYPERCODE_API_URL", "http://hypercode-core:8000").rstrip("/")
_CORE_API_KEY = _read_secret("HYPERCODE_API_KEY")
_DEV_XP_DISCORD_ID = os.environ.get("DEV_XP_DISCORD_ID", "")
_CORE_TIMEOUT = 3


class C:
    GREEN = "\033[32m"
    CYAN = "\033[36m"
    YELLOW = "\033[33m"
    DIM = "\033[2m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    @classmethod
    def off(cls):
        for k in ("GREEN", "CYAN", "YELLOW", "DIM", "BOLD", "RESET"):
            setattr(cls, k, "")


# --------------------------------------------------------------------------- #
# Redis transport -- TCP if reachable, else docker exec. Same as publishers.
# --------------------------------------------------------------------------- #

class TcpBackend:
    name = "tcp"

    def __init__(self):
        import os
        import redis  # type: ignore[import]
        host = os.environ.get("REDIS_HOST", "127.0.0.1")  # 'redis' inside the data-net container
        port = int(os.environ.get("REDIS_PORT", "6379"))
        self.r = redis.Redis(
            host=host, port=port, db=_DB,
            socket_connect_timeout=2, decode_responses=True,
        )
        self.r.ping()

    def write(self, *args):
        return self.r.execute_command(*args)

    def get(self, key):
        return self.r.get(key)

    def hgetall(self, key):
        return self.r.hgetall(key) or {}

    def subscribe(self, channel):
        pubsub = self.r.pubsub()
        pubsub.subscribe(channel)
        for msg in pubsub.listen():
            if msg.get("type") == "message":
                yield msg["data"]


class DockerBackend:
    name = "docker"

    def __init__(self, container):
        self.container = container

    def _exec(self, args, timeout=8):
        out = subprocess.run(
            ["docker", "exec", self.container, "redis-cli", "-n", str(_DB)] + [str(a) for a in args],
            capture_output=True, text=True, timeout=timeout,
        )
        return out.returncode, out.stdout

    def ping(self):
        rc, out = self._exec(["PING"])
        return rc == 0 and out.strip() == "PONG"

    def write(self, *args):
        rc, out = self._exec(list(args))
        return out.strip()

    def get(self, key):
        rc, out = self._exec(["GET", key])
        val = out.strip()
        return val if val else None

    def hgetall(self, key):
        rc, out = self._exec(["HGETALL", key])
        lines = [ln for ln in out.splitlines() if ln != ""]
        return {lines[i]: lines[i + 1] for i in range(0, len(lines) - 1, 2)}

    def subscribe(self, channel):
        proc = subprocess.Popen(
            ["docker", "exec", self.container, "redis-cli", "-n", str(_DB), "SUBSCRIBE", channel],
            stdout=subprocess.PIPE, text=True, bufsize=1,
        )
        # redis-cli prints each reply element on its own line; a message push is
        # the three consecutive lines:  message / <channel> / <payload>
        state = None
        try:
            for raw in proc.stdout:
                line = raw.rstrip("\n")
                if line == "message":
                    state = "channel"
                elif state == "channel":
                    state = "payload"
                elif state == "payload":
                    state = None
                    yield line
        finally:
            proc.terminate()


def _make_backend():
    try:
        return TcpBackend()
    except Exception:
        pass
    for container in _CONTAINERS:
        try:
            b = DockerBackend(container)
            if b.ping():
                return b
        except Exception:
            continue
    return None


# --------------------------------------------------------------------------- #
# Core
# --------------------------------------------------------------------------- #

def _parse_award(raw):
    """Return (xp:int, source:str, reason:str, ts:str) or None if not an xp_award."""
    try:
        d = json.loads(raw)
    except (ValueError, TypeError):
        return None
    kind = d.get("event") or d.get("type")
    if kind != "xp_award":
        return None
    try:
        xp = int(d.get("xp", 0))
    except (ValueError, TypeError):
        return None
    source = str(d.get("source", "unknown"))
    reason = str(d.get("reason", "unspecified"))
    ts = str(d.get("timestamp", datetime.now().isoformat()))
    source_id = d.get("source_id")
    source_id = str(source_id) if source_id else None
    return xp, source, reason, ts, source_id


def _persist(be, xp, source, reason, ts):
    be.write("INCRBY", K_TOTAL, xp)
    be.write("INCR", K_COUNT)
    be.write("HINCRBY", K_BY_SOURCE, source, xp)
    be.write("HINCRBY", K_BY_REASON, reason, xp)
    be.write("SET", K_LAST, ts)
    be.write("XADD", K_LOG, "MAXLEN", "~", _LOG_MAXLEN, "*",
             "xp", xp, "source", source, "reason", reason, "ts", ts)


def _post_to_core(xp, source, reason, source_id=None):
    """Best-effort durable sink. Returns True (banked), an Exception (failed),
    or None (sink not configured). Never raises -- redis stays the buffer."""
    if not (_CORE_API_KEY and _DEV_XP_DISCORD_ID):
        return None
    body = json.dumps({
        "discord_id": _DEV_XP_DISCORD_ID,
        "xp": xp,
        "source": source,
        "reason": reason,
        "source_id": source_id,
    }).encode()
    req = urllib.request.Request(
        _CORE_URL + "/api/v1/economy/award-dev-xp",
        data=body,
        headers={"Content-Type": "application/json", "X-API-Key": _CORE_API_KEY},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=_CORE_TIMEOUT) as resp:
            return resp.status == 200
    except Exception as e:  # noqa: BLE001 -- durability is best-effort by design
        return e


def _describe_failure(err):
    """'HTTP 401' for an HTTP error (the status is what tells a stale key from an outage), else the class name."""
    code = getattr(err, "code", None)
    return ("HTTP %s" % code) if code is not None else type(err).__name__


def _auth_alert(err, consecutive):
    """A loud message for the 1st, then every 10th, consecutive 401/403 from core - else None.

    Why: a stale key used to make EVERY award skip postgres with only a quiet '->pg FAILED (HTTPError)'.
    """
    if getattr(err, "code", None) not in (401, 403):
        return None
    if consecutive != 1 and consecutive % 10 != 0:
        return None
    return ("ERROR: hypercode-core rejected the economy sink (%s) x%d - the API key is stale or wrong. "
            "Awards are still banked in redis but are NOT reaching postgres. "
            "Check API_KEY_FILE / secrets/api_key.txt." % (_describe_failure(err), consecutive))


def _listen(be, seconds):
    deadline = (time.time() + seconds) if seconds else None
    print(C.BOLD + C.CYAN + "  BROSKI$ ECONOMY CONSUMER -- listening on '" + _CHANNEL + "'" + C.RESET)
    print(C.DIM + "  transport=" + be.name + (("  for " + str(seconds) + "s") if seconds else "  (Ctrl-C to stop)") + C.RESET)
    if _CORE_API_KEY and _DEV_XP_DISCORD_ID:
        print(C.DIM + "  postgres sink: ENABLED (key from " + _key_source("HYPERCODE_API_KEY") + ")" + C.RESET)
    else:
        print(C.YELLOW + "  postgres sink: DISABLED (needs HYPERCODE_API_KEY[_FILE] and DEV_XP_DISCORD_ID) -- redis only" + C.RESET)
    print()
    processed = 0
    auth_fails = 0   # consecutive 401/403 from core
    try:
        for raw in be.subscribe(_CHANNEL):
            award = _parse_award(raw)
            if award is None:
                continue
            xp, source, reason, ts, source_id = award
            # Idempotency gate: a stable source_id (git:<repo>:<patch-id>) means a
            # rebase replay / re-run is the SAME award -- skip it so neither the
            # redis tally nor the pg wallet double-counts.
            if source_id and be.write("SETNX", K_SEEN + source_id, "1") in (0, "0"):
                print("  " + C.DIM + "dup    skipped  " + source_id + C.RESET)
                continue
            if source_id:
                be.write("EXPIRE", K_SEEN + source_id, _SEEN_TTL)
            _persist(be, xp, source, reason, ts)
            sink = _post_to_core(xp, source, reason, source_id)
            if sink is True:
                tag = C.CYAN + "  ->pg" + C.RESET
            elif sink is None:
                tag = ""
            else:
                tag = C.YELLOW + "  ->pg FAILED (" + _describe_failure(sink) + ")" + C.RESET
            if sink is True or sink is None:
                auth_fails = 0
            else:
                auth_fails = auth_fails + 1 if getattr(sink, "code", None) in (401, 403) else 0
                alert = _auth_alert(sink, auth_fails)
                if alert:
                    print(alert, file=sys.stderr, flush=True)
            processed += 1
            print("  " + C.GREEN + "+{:>4}".format(xp) + C.RESET
                  + "  " + C.BOLD + "{:<24}".format(source) + C.RESET
                  + C.DIM + reason + C.RESET + tag)
            if deadline and time.time() >= deadline:
                break
    except KeyboardInterrupt:
        pass
    print()
    print(C.DIM + "  processed " + str(processed) + " award(s) this run" + C.RESET)
    return 0


def _stats(be):
    total = be.get(K_TOTAL) or "0"
    count = be.get(K_COUNT) or "0"
    last = be.get(K_LAST) or "never"
    by_source = be.hgetall(K_BY_SOURCE)
    by_reason = be.hgetall(K_BY_REASON)

    print()
    print(C.BOLD + C.CYAN + "  BROSKI$ ECONOMY -- XP LEADERBOARD" + C.RESET)
    print(C.DIM + "  transport=" + be.name + "  last award: " + last + C.RESET)
    print()
    print("  " + C.BOLD + "GRAND TOTAL  " + C.GREEN + str(total) + " XP" + C.RESET
          + C.DIM + "   across " + str(count) + " award(s)" + C.RESET)
    print()

    def _table(title, data):
        print("  " + C.BOLD + title + C.RESET)
        if not data:
            print(C.DIM + "    (none yet -- run the consumer while XP is published)" + C.RESET)
            return
        rows = sorted(data.items(), key=lambda kv: int(kv[1]), reverse=True)
        for name, xp in rows:
            bar = "#" * min(40, int(int(xp) / max(1, int(total)) * 40)) if int(total) else ""
            print("    {:<26} {:>7} XP  ".format(name[:26], xp) + C.GREEN + bar + C.RESET)
        print()

    _table("BY SOURCE (repo)", by_source)
    _table("BY REASON", by_reason)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="BROski$ economy consumer -- persists XP from broski_economy")
    parser.add_argument("--stats", action="store_true", help="print the persisted leaderboard and exit")
    parser.add_argument("--seconds", type=int, default=0, help="listen for N seconds then exit (0 = forever)")
    parser.add_argument("--no-color", action="store_true", help="plain text output")
    args = parser.parse_args()

    if args.no_color:
        C.off()

    be = _make_backend()
    if be is None:
        print(C.YELLOW + "  Redis unreachable (no host TCP + no redis container). Is the stack up?" + C.RESET)
        return 1

    if args.stats:
        return _stats(be)
    return _listen(be, args.seconds)


if __name__ == "__main__":
    sys.exit(main())
