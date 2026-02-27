"""Structured logging setup (structlog)."""

import logging
import sys

import structlog


def _build_processors() -> list:
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer() if sys.stderr.isatty() else structlog.processors.JSONRenderer(),
    ]


def configure_logging() -> None:
    from docu_flow.config import settings

    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    structlog.configure(
        processors=_build_processors(),
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


# Apply a safe default config immediately so module-level `log` works
# before the FastAPI lifespan calls configure_logging() with settings.
structlog.configure(
    processors=_build_processors(),
    wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=False,  # re-evaluate after configure_logging()
)

log = structlog.get_logger()
