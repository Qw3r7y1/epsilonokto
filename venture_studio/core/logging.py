"""Structured logging setup for the Venture Studio."""

from __future__ import annotations

import logging
import sys

from venture_studio.core.config import get_settings


def setup_logging() -> logging.Logger:
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(fmt)

    root = logging.getLogger("venture_studio")
    root.setLevel(level)
    root.addHandler(handler)
    return root


logger = setup_logging()
