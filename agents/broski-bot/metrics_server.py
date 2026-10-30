"""Prometheus metrics endpoint for the cog bot (python -m cogs.bot).

src/bot.py starts its own metrics server, but the container runs cogs.bot, so
until now nothing listened on :8000 and the `broski-bot` scrape target stayed
down. Fail-open: a missing library or a busy port never stops the bot.
"""
import logging
import os

log = logging.getLogger(__name__)

DEFAULT_PORT = 8000
_OFF = ("0", "false", "no", "off")

try:
    from prometheus_client import Gauge, start_http_server
    _READY = Gauge("broski_bot_ready", "1 once the Discord session is ready")
    _GUILDS = Gauge("broski_bot_guilds", "Guilds the bot is in")
except ImportError:  # library not installed
    Gauge = start_http_server = _READY = _GUILDS = None


def start_metrics_server(port: int | None = None) -> bool:
    """Start the /metrics listener. Returns True only if it is now serving."""
    if os.getenv("PROMETHEUS_ENABLED", "true").lower() in _OFF:
        return False
    if start_http_server is None:
        log.warning("prometheus_client not installed; metrics disabled")
        return False
    port = int(port if port is not None else os.getenv("PROMETHEUS_PORT", DEFAULT_PORT))
    try:
        start_http_server(port)
    except OSError as exc:
        log.warning("metrics server not started on :%s (%s)", port, exc)
        return False
    log.info("metrics server listening on :%s", port)
    return True


def set_ready(guild_count: int) -> None:
    if _READY is not None:
        _READY.set(1)
        _GUILDS.set(guild_count)
