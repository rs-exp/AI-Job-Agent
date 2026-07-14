import logging
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler


def get_logger(name: str) -> logging.Logger:
    """
    Create and return a reusable application logger.

    Logs are written to:
    1. The VS Code terminal
    2. logs/ai_job_agent.log
    """

    logger = logging.getLogger(name)

    # Prevent duplicate handlers if get_logger() is called multiple times.
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    project_root = Path(__file__).resolve().parent.parent
    log_directory = project_root / "logs"
    log_directory.mkdir(parents=True, exist_ok=True)

    log_file = log_directory / "ai_job_agent.log"

    log_format = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)

    file_handler = TimedRotatingFileHandler(
        filename=log_file,
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(log_format)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    logger.propagate = False

    return logger