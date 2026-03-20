"""
logger.py — Centralized logging for Tikkocampus.

Provides a configured logger with console + file output.
Handles --windowed mode (null stdout) gracefully.
"""
import os
import sys
import logging
from logging.handlers import RotatingFileHandler


def get_logger(name="tikkocampus"):
    """
    Returns a configured logger instance.
    - Console handler (if stdout is available)
    - File handler (rotating, max 2MB, 3 backups)
    """
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers on repeated calls
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler (only if stdout is available)
    if sys.stdout is not None:
        try:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        except Exception:
            pass  # Skip console in windowed mode

    # File handler (always active)
    try:
        from config import LOG_FILE
        file_handler = RotatingFileHandler(
            LOG_FILE, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        # Last resort: if even file logging fails, at least don't crash the app
        if sys.stderr is not None:
            sys.stderr.write(f"Failed to initialize file logger: {e}\n")

    return logger
