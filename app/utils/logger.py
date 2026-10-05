"""Logging configuration utility for the student data pipeline."""
import logging
from pathlib import Path
from typing import Optional


def setup_logger(
    log_file: Optional[Path] = None,
    level: int = logging.INFO
) -> logging.Logger:
    """
    Configures and returns the central pipeline logger.
    Writes formatted logs to both file and console.
    """
    if log_file is None:
        log_file = Path("logs/pipeline.log")

    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("student_pipeline")
    logger.setLevel(level)

    # Avoid adding duplicate handlers if logger was already initialized
    if not logger.handlers:
        # File handler matching required format
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Stream handler for console feedback
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger
