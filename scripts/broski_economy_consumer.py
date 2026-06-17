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
import subprocess
import sys
import time
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
        import redis  # type: ignore[import]
        self.r = redis.Redis(
            host="127.0.0.1", port=6379, db=_DB,
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
    return xp, source, reason, ts


def _persist(be, xp, source, reason, ts):
    be.write("INCRBY", K_TOTAL, xp)
    be.write("INCR", K_COUNT)
    be.write("HINCRBY", K_BY_SOURCE, source, xp)
    be.write("HINCRBY", K_BY_REASON, reason, xp)
    be.write("SET", K_LAST, ts)
    be.write("XADD", K_LOG, "MAXLEN", "~", _LOG_MAXLEN, "*",
             "xp", xp, "source", source, "reason", reason, "ts", ts)


def _listen(be, seconds):
    deadline = (time.time() + seconds) if seconds else None
    print(C.BOLD + C.CYAN + "  BROSKI$ ECONOMY CONSUMER -- listening on '" + _CHANNEL + "'" + C.RESET)
    print(C.DIM + "  transport=" + be.name + (("  for " + str(seconds) + "s") if seconds else "  (Ctrl-C to stop)") + C.RESET)
    print()
    processed = 0
    try:
        for raw in be.subscribe(_CHANNEL):
            award = _parse_award(raw)
            if award is None:
                continue
            xp, source, reason, ts = award
            _persist(be, xp, source, reason, ts)
            processed += 1
            print("  " + C.GREEN + "+{:>4}".format(xp) + C.RESET
                  + "  " + C.BOLD + "{:<24}".format(source) + C.RESET
                  + C.DIM + reason + C.RESET)
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
