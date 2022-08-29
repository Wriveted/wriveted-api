import logging
import logging.config
from typing import List

import structlog
import uvicorn

from app.config import Settings


def init_logging(settings: Settings):
    """

    Ref: https://github.com/simonw/datasette/issues/1175#issuecomment-762488336
    """

    shared_processors: List[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        # Don't need a timestamp as cloudrun already adds one
        # structlog.processors.TimeStamper(fmt='iso'),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    logconfig_dict = {
        "version": 1,
        "formatters": {
            "console": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.dev.ConsoleRenderer(),
                "foreign_pre_chain": shared_processors,
            },
            "json": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.processors.JSONRenderer(),
                "foreign_pre_chain": shared_processors,
            },
            **uvicorn.config.LOGGING_CONFIG["formatters"],
        },
        "handlers": {
            "default": {
                "level": "DEBUG",
                "class": "logging.StreamHandler",
                "formatter": "json" if settings.LOG_AS_JSON else "console",
            },
            "uvicorn.access": {
                "level": "INFO",
                "class": "logging.StreamHandler",
                "formatter": "access",
            },
            "uvicorn.default": {
                "level": "INFO",
                "class": "logging.StreamHandler",
                "formatter": "default",
            },
        },
        "loggers": {
            "": {"handlers": ["default"], "level": "INFO"},
            "app": {"level": settings.LOGGING_LEVEL},
            "app.api.auth": {"level": settings.AUTH_LOGGING_LEVEL},
            "app.services": {"level": "DEBUG"},
            "app.services.recommendations": {"level": "DEBUG"},
            "uvicorn.error": {
                "handlers": ["default"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": [
                    "default" if settings.LOG_UVICORN_ACCESS else "uvicorn.access"
                ],
                "level": "INFO",
                "propagate": False,
            },
        },
    }

    processors = [
        structlog.stdlib.filter_by_level,
        *shared_processors,
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ]

    logging.config.dictConfig(logconfig_dict)

    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
        context_class=dict,
    )
