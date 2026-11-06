# backend/discovery/discovery_logger.py
"""Structured logger for discovery operations with credential redaction."""

import logging
import re

logger = logging.getLogger("discovery")
logger.setLevel(logging.INFO)

if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    ch.setFormatter(formatter)
    logger.addHandler(ch)

_KEY_REDACT_REGEX = re.compile(r"(key|token|auth|secret)=([a-zA-Z0-9_\-\.]{6,})", re.IGNORECASE)


def redact_sensitive(text: str) -> str:
    """Mask potential secret tokens and API keys in log strings."""
    if not text:
        return text
    return _KEY_REDACT_REGEX.sub(r"\1=***", text)


def get_logger(name: str = "discovery") -> logging.Logger:
    """Returns a logger instance prefixed with discovery namespace."""
    sub_logger = logging.getLogger(f"discovery.{name}" if not name.startswith("discovery") else name)
    sub_logger.setLevel(logging.INFO)
    return sub_logger


def log_discovery_event(level: str, msg: str, **kwargs):
    """Log discovery lifecycle events with redacted metadata."""
    clean_msg = redact_sensitive(msg)
    if kwargs:
        clean_kwargs = {k: redact_sensitive(str(v)) for k, v in kwargs.items()}
        clean_msg = f"{clean_msg} | {clean_kwargs}"

    if level.lower() == "error":
        logger.error(clean_msg)
    elif level.lower() == "warning":
        logger.warning(clean_msg)
    elif level.lower() == "debug":
        logger.debug(clean_msg)
    else:
        logger.info(clean_msg)
