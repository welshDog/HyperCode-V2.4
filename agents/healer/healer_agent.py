# agents/healer/healer_agent.py
# HYPER-SILLs Stack: HS-003 → HS-006 → HS-103
# Self-Healing Docker Agent — circuit-breaker + fallback chain + lifecycle
# Uses docker-ce-cli via /var/run/docker.sock (NEVER docker.io)

import subprocess
import time
import logging
from enum import Enum

logging.basicConfig(level=logging.INFO, format="%(asctime)s [HEALER] %(message)s")
log = logging.getLogger(__name__)


# ── HS-003: Agent Lifecycle States ──────────────────────────────────────────
class AgentState(Enum):
    BOOT     = "BOOT"
    IDLE     = "IDLE"
    ACTIVE   = "ACTIVE"
    ERROR    = "ERROR"
    HEALING  = "HEALING"
    RETIRED  = "RETIRED"


# ── HS-103: Circuit Breaker States ──────────────────────────────────────────
class CircuitState(Enum):
    CLOSED    = "CLOSED"     # normal — watching
    OPEN      = "OPEN"       # tripped — blocking restarts
    HALF_OPEN = "HALF_OPEN"  # testing if recovery worked


# ── Config ───────────────────────────────────────────────────────────────────
FAILURE_THRESHOLD = 3        # open circuit after N consecutive failures
COOLDOWN_SECONDS  = 30       # wait before moving to HALF_OPEN
POLL_INTERVAL     = 10       # seconds between health checks
WATCH_CONTAINERS  = [        # HyperCode-V2.4 containers to monitor
    "hypercode-api",
    "hypercode-redis",
    "hypercode-postgres",
    "broski-bot",
]


class HealerAgent:
    def __init__(self):
        self.state          = AgentState.BOOT
        self.circuit        = CircuitState.CLOSED
        self.fail_counts    = {c: 0 for c in WATCH_CONTAINERS}
        self.last_open_time = {}
        self.transition(AgentState.IDLE)

    # ── HS-003: State machine transitions ───────────────────────────────────
    def transition(self, new_state: AgentState):
        log.info(f"STATE: {self.state.value} → {new_state.value}")
        self.state = new_state

    # ── Docker via docker-ce-cli ─────────────────────────────────────────────
    def is_running(self, container: str) -> bool:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Running}}", container],
            capture_output=True, text=True
        )
        return result.stdout.strip() == "true"

    def restart_container(self, container: str) -> bool:
        log.info(f"Restarting {container}...")
        result = subprocess.run(
            ["docker", "restart", container],
            capture_output=True, text=True
        )
        return result.returncode == 0

    # ── HS-006: 3-level fallback chain ──────────────────────────────────────
    def fallback_chain(self, container: str) -> bool:
        # Level 1 — retry after short pause
        log.warning(f"FALLBACK L1 — retrying {container}")
        time.sleep(2)
        if self.is_running(container):
            return True

        # Level 2 — degraded restart
        log.warning(f"FALLBACK L2 — degraded restart {container}")
        if self.restart_container(container):
            time.sleep(5)
            if self.is_running(container):
                return True

        # Level 3 — safe-mode, give up this cycle
        log.error(f"FALLBACK L3 — safe-mode: {container} unrecoverable this cycle")
        return False

    # ── HS-103: Circuit breaker ──────────────────────────────────────────────
    def check_circuit(self, container: str) -> bool:
        cstate = self.circuit

        # OPEN — check cooldown before allowing retry
        if cstate == CircuitState.OPEN:
            elapsed = time.time() - self.last_open_time.get(container, 0)
            if elapsed >= COOLDOWN_SECONDS:
                log.info(f"CIRCUIT HALF-OPEN — testing {container}")
                self.circuit = CircuitState.HALF_OPEN
            else:
                remaining = int(COOLDOWN_SECONDS - elapsed)
                log.info(f"CIRCUIT OPEN — skipping {container} ({remaining}s left)")
                return False

        if not self.is_running(container):
            self.fail_counts[container] += 1
            log.warning(f"{container} DOWN — failures: {self.fail_counts[container]}")
            self.transition(AgentState.ERROR)

            recovered = self.fallback_chain(container)

            if recovered:
                log.info(f"✅ {container} RECOVERED — circuit CLOSED")
                self.fail_counts[container] = 0
                self.circuit = CircuitState.CLOSED
                self.transition(AgentState.IDLE)
            else:
                if self.fail_counts[container] >= FAILURE_THRESHOLD:
                    log.error(f"🔴 CIRCUIT OPEN — {container} hit {FAILURE_THRESHOLD} failures")
                    self.circuit = CircuitState.OPEN
                    self.last_open_time[container] = time.time()
                self.transition(AgentState.HEALING)
            return recovered

        # HALF_OPEN — container healthy again, close the circuit
        if cstate == CircuitState.HALF_OPEN:
            log.info(f"✅ {container} healthy — circuit CLOSED")
            self.circuit = CircuitState.CLOSED
            self.fail_counts[container] = 0

        return True

    # ── Main watch loop ──────────────────────────────────────────────────────
    def run(self):
        self.transition(AgentState.ACTIVE)
        log.info(f"👁  Watching: {WATCH_CONTAINERS}")
        while self.state != AgentState.RETIRED:
            for container in WATCH_CONTAINERS:
                self.check_circuit(container)
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    HealerAgent().run()
