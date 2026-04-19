"""
Unified logging for the entire project.

Every module should use::

    from logger import log
    log.info("Mode started")
    log.debug("Frame data: %s", data)
    log.error("Something failed", exc_info=True)

The log level and file path are read from config.yaml → logging section.
"""

import logging
import os
import sys

from config_loader import get

_LOG_NAME = "proton"

def _setup() -> logging.Logger:
    logger = logging.getLogger(_LOG_NAME)
    # Prevent duplicate handlers on reload
    if logger.handlers:
        return logger

    level_str = get("logging.level", "INFO").upper()
    level = getattr(logging, level_str, logging.INFO)
    logger.setLevel(level)

    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(name)s.%(funcName)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    if get("logging.console", True):
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(level)
        ch.setFormatter(fmt)
        logger.addHandler(ch)

    # File handler
    log_file = get("logging.log_file")
    if log_file:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_path = os.path.join(project_root, log_file)
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setLevel(level)
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    return logger


log: logging.Logger = _setup()
