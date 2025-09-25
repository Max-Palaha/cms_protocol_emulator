# utils/logger.py
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Optional
from logging.handlers import RotatingFileHandler


class SafeFormatter(logging.Formatter):
    """Formatter that tolerates missing `protocol` and `client_ip` extras."""
    def format(self, record: logging.LogRecord) -> str:
        proto = getattr(record, "protocol", "")
        ip = getattr(record, "client_ip", "")
        record.proto = f"({proto}) " if proto else ""
        record.ip = f"({ip}) " if ip else ""
        return super().format(record)


def _env_log_level(default: int = logging.INFO) -> int:
    """Read log level from env var CMS_LOG_LEVEL / LOG_LEVEL if provided."""
    name = os.getenv("CMS_LOG_LEVEL") or os.getenv("LOG_LEVEL")
    if not name:
        return default
    return getattr(logging, name.upper(), default)


def _discover_project_root() -> Path:
    """
    Try to find the repo root regardless of where the script is run from
    (works for 'Current File' in PyCharm).
    """
    here = Path(__file__).resolve()
    candidates = [here.parent, *here.parents]
    markers = {"pyproject.toml", "requirements.txt", ".git"}
    for p in candidates:
        if any((p / m).exists() for m in markers):
            return p
    return here.parent.parent


def _logs_dir(explicit_dir: Optional[Path] = None) -> Path:
    base = explicit_dir if explicit_dir else _discover_project_root() / "logs"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _build_formatter(with_ms: bool = False) -> logging.Formatter:
    fmt = "%(levelname)-8s %(asctime)s %(proto)s%(ip)s%(message)s"
    if with_ms:
        class MillisecondFormatter(SafeFormatter):
            def formatTime(self, record, datefmt=None):
                s = super().formatTime(record, "%y-%m-%d %H:%M:%S.%f")
                return s[:-3] if "." in s else s
        return MillisecondFormatter(fmt)
    return SafeFormatter(fmt, datefmt="%y-%m-%d %H:%M:%S")


def setup_logger(
    name: str = "cms_protocol",
    level: int = _env_log_level(),
    log_file_name: str = "cms_protocol.log",
    log_dir: Optional[Path] = None,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 2,
    with_milliseconds: bool = False,
) -> logging.Logger:
    """
    Create (or return existing) application logger.

    - Writes to <repo_root>/logs/<log_file_name> by default.
    - Ensures the logs directory exists.
    - Safe to import multiple times (no duplicate handlers).
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    formatter = _build_formatter(with_ms=with_milliseconds)
    log_path = _logs_dir(Path(log_dir) if log_dir else None) / log_file_name

    # Console handler (stdout)
    if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler)
               for h in logger.handlers):
        ch = logging.StreamHandler(stream=sys.stdout)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    # Rotating file handler
    if not any(isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", "") == str(log_path)
               for h in logger.handlers):
        fh = RotatingFileHandler(str(log_path), maxBytes=max_bytes,
                                 backupCount=backup_count, encoding="utf-8")
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger


logger = setup_logger()
