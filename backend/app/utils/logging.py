"""Loguru file logging with rotation (CLAUDE.md §11)."""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

from app.config import settings


def configure_logging(component: str) -> None:
    """Send logs to stderr + /opt/leadkar/logs/<component>.log with rotation.

    component is one of: backend, worker, beat.
    """
    logger.remove()
    logger.add(sys.stderr, level="INFO", enqueue=True)

    log_dir = Path(settings.LOG_DIR)
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        logger.add(
            log_dir / f"{component}.log",
            level="INFO",
            rotation="10 MB",
            retention="14 days",
            compression="gz",
            enqueue=True,
        )
    except OSError as exc:  # don't crash if the log dir isn't writable
        logger.warning("File logging disabled ({}): {}", log_dir, exc)
