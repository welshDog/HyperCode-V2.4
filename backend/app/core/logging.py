import logging
import sys

try:
    from pythonjsonlogger import jsonlogger as _jsonlogger
    _HAS_JSON_LOGGER = True
except ImportError:
    _HAS_JSON_LOGGER = False


def setup_logging(log_level: str = "INFO") -> None:
    """Configure structured JSON logging for all services.
    Falls back to plain text if python-json-logger is not installed."""
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)
    if _HAS_JSON_LOGGER:
        formatter = _jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    handler.setFormatter(formatter)

    # Remove default handlers, add ours
    logger.handlers.clear()
    logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Get a named structured logger."""
    return logging.getLogger(name)
