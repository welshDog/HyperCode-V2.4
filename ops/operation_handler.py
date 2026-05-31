"""
OperationHandler — Phase 2 core for HyperCode-V2.4 brain ops.

Handles retry logic, circuit breaker, structured logging, and
status output that maps to ops_taxonomy.json error codes.

Usage:
    from ops.operation_handler import OperationHandler
    handler = OperationHandler()
    success, result, error_code, details = handler.execute(
        "github_sync", my_sync_func, repos=my_repos
    )
"""

import json
import logging
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

# ---------------------------------------------------------------------------
# Logging setup — structured log lines that match error_handling.md Rule 4
# ---------------------------------------------------------------------------

LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(step)s] %(error_code)s %(message)s"


class StepLoggerAdapter(logging.LoggerAdapter):
    """Injects step + error_code into every log record."""

    def process(self, msg, kwargs):
        extra = self.extra.copy()
        extra.update(kwargs.pop("extra", {}))
        kwargs["extra"] = extra
        return msg, kwargs


def get_step_logger(step: str, log_path: Optional[Path] = None) -> StepLoggerAdapter:
    logger = logging.getLogger(f"hyper_ops.{step}")
    if not logger.handlers:
        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(step)s] %(error_code)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        # Console handler
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        # File handler if path provided
        if log_path:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            fh = logging.FileHandler(log_path, mode="a", encoding="utf-8")
            fh.setFormatter(formatter)
            logger.addHandler(fh)
        logger.setLevel(logging.DEBUG)
    return StepLoggerAdapter(logger, {"step": step, "error_code": "OPS_000"})


# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------

class CircuitBreaker:
    """
    Opens after `failure_threshold` consecutive failures.
    Auto-recovers after `recovery_timeout` seconds.
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 300):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._failures: dict[str, int] = {}
        self._opened_at: dict[str, float] = {}

    def is_open(self, operation: str) -> bool:
        if operation not in self._opened_at:
            return False
        elapsed = time.time() - self._opened_at[operation]
        if elapsed >= self.recovery_timeout:
            # Auto-recover — reset state
            self._failures.pop(operation, None)
            self._opened_at.pop(operation, None)
            return False
        return True

    def time_until_retry(self, operation: str) -> int:
        if operation not in self._opened_at:
            return 0
        remaining = self.recovery_timeout - (time.time() - self._opened_at[operation])
        return max(0, int(remaining))

    def record_failure(self, operation: str):
        self._failures[operation] = self._failures.get(operation, 0) + 1
        if self._failures[operation] >= self.failure_threshold:
            if operation not in self._opened_at:
                self._opened_at[operation] = time.time()

    def record_success(self, operation: str):
        self._failures.pop(operation, None)
        self._opened_at.pop(operation, None)


# ---------------------------------------------------------------------------
# Error classification — maps exceptions to ops_taxonomy.json error codes
# ---------------------------------------------------------------------------

# Retryable error codes (transient — network, timeout, rate limits)
RETRYABLE_CODES = {
    "NETWORK_ERROR",
    "TIMEOUT",
    "GH_002",   # GitHub rate limit
    "GH_004",   # GitHub network timeout
    "DC_003",   # Discord network timeout
    "HC_003",   # Briefing API timeout
}

# Non-retryable (permanent until human fixes something)
NON_RETRYABLE_CODES = {
    "GH_001",   # Invalid token
    "GH_003",   # No repo access
    "DC_001",   # Invalid webhook URL
    "DC_002",   # Webhook 401/403
    "HC_001",   # Docker daemon down
    "VC_001",   # Git not initialized
    "VC_002",   # Git config missing
    "BR_001",   # Vault path missing
    "BR_003",   # Template missing
    "PERMISSION_DENIED",
}


def classify_exception(e: Exception, step: str = "") -> str:
    """Map an exception to a taxonomy error code."""
    msg = str(e).lower()
    etype = type(e).__name__

    if "rate limit" in msg or "429" in msg:
        return "GH_002" if "github" in step else "RATE_LIMITED"
    if "401" in msg or "403" in msg or "unauthorized" in msg or "forbidden" in msg:
        if "discord" in step or "webhook" in step:
            return "DC_002"
        if "github" in step:
            return "GH_001"
        return "AUTH_ERROR"
    if "404" in msg or "not found" in msg:
        if "github" in step:
            return "GH_003"
        return "NOT_FOUND"
    if "timeout" in msg or "timed out" in msg:
        if "github" in step:
            return "GH_004"
        if "briefing" in step:
            return "HC_003"
        return "TIMEOUT"
    if isinstance(e, (ConnectionError, ConnectionResetError, BrokenPipeError)):
        return "NETWORK_ERROR"
    if isinstance(e, PermissionError):
        return "PERMISSION_DENIED"
    if isinstance(e, FileNotFoundError):
        return "BR_001"
    if "docker" in msg or "daemon" in msg:
        return "HC_001"
    if "port" in msg and "in use" in msg:
        return "HC_004"

    return "UNKNOWN_ERROR"


# ---------------------------------------------------------------------------
# OperationHandler
# ---------------------------------------------------------------------------

class OperationHandler:
    """
    Execute any brain-ops step with:
    - Retry + exponential backoff
    - Circuit breaker
    - Structured logging
    - Taxonomy-mapped error codes
    - Timing stats

    Returns a consistent 4-tuple:
        (success: bool, result: Any, error_code: str | None, details: dict)
    """

    def __init__(
        self,
        max_retries: int = 3,
        retry_delays: list[float] = None,
        circuit_breaker: CircuitBreaker = None,
        log_path: Optional[Path] = None,
    ):
        self.max_retries = max_retries
        self.retry_delays = retry_delays or [1.0, 2.0, 4.0]
        self.circuit_breaker = circuit_breaker or CircuitBreaker(
            failure_threshold=5, recovery_timeout=300
        )
        self.log_path = log_path
        self._loggers: dict[str, StepLoggerAdapter] = {}

    def _logger(self, step: str) -> StepLoggerAdapter:
        if step not in self._loggers:
            self._loggers[step] = get_step_logger(step, self.log_path)
        return self._loggers[step]

    def _log(self, step: str, level: str, error_code: str, message: str):
        log = self._logger(step)
        log.extra["error_code"] = error_code
        getattr(log, level)(message)

    def execute(
        self,
        operation_name: str,
        func: Callable,
        *args,
        **kwargs,
    ) -> tuple[bool, Any, Optional[str], dict]:
        """
        Execute `func` with retry + circuit breaker.

        Returns:
            (success, result, error_code, details)
        """
        start_time = time.monotonic()

        # --- Circuit breaker check ---
        if self.circuit_breaker.is_open(operation_name):
            wait = self.circuit_breaker.time_until_retry(operation_name)
            code = f"{operation_name.upper()[:2]}_CIRCUIT_OPEN"
            self._log(operation_name, "warning", code,
                      f"Circuit breaker OPEN — retry in {wait}s")
            return False, None, code, {
                "reason": "Circuit breaker open (repeated failures)",
                "recovery_in_seconds": wait,
                "duration_seconds": round(time.monotonic() - start_time, 3),
            }

        self._log(operation_name, "info", "OPS_000",
                  f"Starting {operation_name}")

        last_error_code = "UNKNOWN_ERROR"
        last_exception = None

        for attempt in range(1, self.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                self.circuit_breaker.record_success(operation_name)
                duration = round(time.monotonic() - start_time, 3)
                self._log(operation_name, "info", "OPS_000",
                          f"✅ Succeeded on attempt {attempt} ({duration}s)")
                return True, result, None, {
                    "attempt": attempt,
                    "duration_seconds": duration,
                }

            except Exception as e:
                last_exception = e
                last_error_code = classify_exception(e, operation_name)
                self.circuit_breaker.record_failure(operation_name)

                self._log(operation_name, "warning", last_error_code,
                          f"Attempt {attempt}/{self.max_retries} failed: {e}")

                # Non-retryable → fail fast
                if last_error_code in NON_RETRYABLE_CODES:
                    self._log(operation_name, "error", last_error_code,
                              "Non-retryable error — stopping immediately")
                    break

                # Retryable → back off and try again
                if attempt < self.max_retries:
                    delay = self.retry_delays[min(attempt - 1, len(self.retry_delays) - 1)]
                    # Honour Retry-After if available (GitHub rate limits)
                    retry_after = getattr(e, "retry_after", None)
                    if retry_after:
                        delay = float(retry_after)
                    self._log(operation_name, "info", last_error_code,
                              f"Retrying in {delay}s...")
                    time.sleep(delay)

        # All attempts exhausted
        duration = round(time.monotonic() - start_time, 3)
        self._log(operation_name, "error", last_error_code,
                  f"❌ All attempts failed ({duration}s)")
        return False, None, last_error_code, {
            "attempt": attempt,
            "duration_seconds": duration,
            "error": str(last_exception),
            "traceback": traceback.format_exc(),
        }


# ---------------------------------------------------------------------------
# StepResult — structured output that feeds ops_status_template.json
# ---------------------------------------------------------------------------

class StepResult:
    """
    Wraps the OperationHandler 4-tuple into a dict that matches
    the ops_status_template.json step schema.
    """

    STATUS_MAP = {
        # (success, has_partial) → (status_str, icon)
        (True, False):  ("SUCCESS",  "✅"),
        (True, True):   ("PARTIAL",  "⚠️"),
        (False, False): ("FAILED",   "❌"),
    }

    def __init__(
        self,
        step: str,
        success: bool,
        result: Any,
        error_code: Optional[str],
        details: dict,
        partial: bool = False,
        extra: dict = None,
    ):
        self.step = step
        self.success = success
        self.error_code = error_code
        self.details = details
        self.partial = partial
        self.extra = extra or {}
        status_key = (success, partial)
        status_str, icon = self.STATUS_MAP.get(status_key, ("UNKNOWN", "❓"))
        self.status = status_str
        self.icon = icon

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "icon": self.icon,
            "duration_seconds": self.details.get("duration_seconds"),
            "error_code": self.error_code,
            "error_message": self.details.get("error"),
            "details": {**self.details, **self.extra},
        }

    def __bool__(self):
        return self.success

    def __repr__(self):
        return f"StepResult(step={self.step!r}, status={self.status}, error_code={self.error_code!r})"


# ---------------------------------------------------------------------------
# OpsSession — orchestrates the full chain and builds the status object
# ---------------------------------------------------------------------------

class OpsSession:
    """
    Runs the full 5-step ops chain and produces the canonical
    ops-status.json output.

    Steps run in order. Health check failure is the ONLY hard stop
    (per error_handling.md Rule 1).
    """

    CHAIN = [
        "health_check",
        "github_sync",
        "briefing_generation",
        "vault_commit",
        "discord_report",
    ]

    def __init__(self, handler: OperationHandler = None, output_dir: Path = None):
        self.handler = handler or OperationHandler()
        self.output_dir = output_dir or Path("output")
        self.session_id = f"ops_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        self.results: dict[str, StepResult] = {}

    def run_step(
        self,
        step: str,
        func: Callable,
        *args,
        partial_check: Callable = None,
        **kwargs,
    ) -> StepResult:
        """
        Run one step via OperationHandler and wrap in StepResult.
        `partial_check(result)` → True if the result counts as partial.
        """
        success, result, error_code, details = self.handler.execute(
            step, func, *args, **kwargs
        )
        partial = partial_check(result) if (partial_check and success and result) else False
        sr = StepResult(step, success, result, error_code, details, partial=partial)
        self.results[step] = sr
        return sr

    def build_status_object(self) -> dict:
        """Produce the canonical ops-status.json dict."""
        all_ok = all(sr.success for sr in self.results.values())
        any_partial = any(sr.partial for sr in self.results.values())
        any_error = any(not sr.success for sr in self.results.values())

        if all_ok and not any_partial:
            overall_status, overall_icon = "SUCCESS", "✅"
        elif any_error:
            overall_status, overall_icon = "FAILED", "❌"
        else:
            overall_status, overall_icon = "PARTIAL", "⚠️"

        # Collect next_steps from failed/partial steps
        next_steps = []
        for step, sr in self.results.items():
            if sr.error_code:
                next_steps.append(f"[{sr.error_code}] Fix {step}: {sr.details.get('error', 'see logs')}")

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": self.session_id,
            "ops_version": "2.0.0",
            "steps": {step: sr.to_dict() for step, sr in self.results.items()},
            "summary": {
                "overall_status": overall_status,
                "icon": overall_icon,
                "all_ok": all_ok and not any_partial,
                "next_steps": next_steps,
            },
        }

    def save_status(self, status: dict) -> Path:
        """Write ops-status.json to output_dir."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        out_path = self.output_dir / f"{date_str}-ops-status.json"
        out_path.write_text(json.dumps(status, indent=2, ensure_ascii=False))
        return out_path
