"""Logging configuration.

Provides standard Python logging with structured key=value formatting.
"""

import logging
import logging.config
from contextvars import ContextVar

# Context variable for task ID tracking
task_id_var: ContextVar[str | None] = ContextVar("task_id", default=None)


class TaskContextFilter(logging.Filter):
    """Filter that adds task_id to log records from context."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.task_id = task_id_var.get() or "-"
        return True


LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "task_context": {
            "()": TaskContextFilter,
        },
    },
    "formatters": {
        "standard": {
            "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "detailed": {
            "format": "%(asctime)s | %(levelname)-8s | %(name)s | task=%(task_id)s | %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "standard",
            "filters": ["task_context"],
            "stream": "ext://sys.stderr",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"],
    },
    "loggers": {
        "compliance": {
            "level": "DEBUG",
            "handlers": ["console"],
            "propagate": False,
        },
        "httpx": {
            "level": "WARNING",
        },
        "httpcore": {
            "level": "WARNING",
        },
        "openai": {
            "level": "WARNING",
        },
    },
}

_configured = False


def configure_logging() -> None:
    """Configure logging using the LOG_CONFIG dictionary."""
    global _configured
    if not _configured:
        logging.config.dictConfig(LOG_CONFIG)
        _configured = True


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name.

    Args:
        name: The name for the logger, typically __name__.

    Returns:
        A configured logging.Logger instance.
    """
    configure_logging()
    return logging.getLogger(name)
