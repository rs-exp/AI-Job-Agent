import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


APP_LOGGER_NAME = "ai_job_agent"


def _configure_application_logger() -> logging.Logger:
    """
    Configure one shared logger for the entire application.

    All module loggers propagate their messages to this logger,
    preventing multiple file handlers from opening the same file.
    """

    application_logger = logging.getLogger(APP_LOGGER_NAME)

    if application_logger.handlers:
        return application_logger

    application_logger.setLevel(logging.INFO)

    project_root = Path(__file__).resolve().parent.parent
    log_directory = project_root / "logs"
    log_directory.mkdir(parents=True, exist_ok=True)

    log_file = log_directory / "ai_job_agent.log"

    log_format = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Use stdout so PowerShell does not mark normal log lines
    # as NativeCommandError.
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)

    file_handler = TimedRotatingFileHandler(
        filename=log_file,
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8",
        delay=True,
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(log_format)

    application_logger.addHandler(console_handler)
    application_logger.addHandler(file_handler)

    application_logger.propagate = False

    return application_logger


def get_logger(name: str) -> logging.Logger:
    """
    Return a child logger that uses the application's shared handlers.
    """

    _configure_application_logger()

    logger_name = f"{APP_LOGGER_NAME}.{name}"
    logger = logging.getLogger(logger_name)

    logger.setLevel(logging.INFO)

    # Do not attach handlers directly to child loggers.
    # Messages will use the application logger's handlers.
    logger.propagate = True

    return logger
