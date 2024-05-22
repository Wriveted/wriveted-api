import logging
import logging.config
from typing import List

import structlog
import uvicorn
from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.cloud_trace_propagator import CloudTraceFormatPropagator
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from app.config import Settings


def init_tracing(app, settings: Settings):
    trace.set_tracer_provider(TracerProvider())

    if settings.ENABLE_OTEL_GOOGLE_EXPORTER:
        cloud_trace_exporter = CloudTraceSpanExporter(
            project_id=settings.GCP_PROJECT_ID,
        )
        trace.get_tracer_provider().add_span_processor(
            SimpleSpanProcessor(cloud_trace_exporter)
        )
        # Set the X-Cloud-Trace-Context header
        set_global_textmap(CloudTraceFormatPropagator())

    HTTPXClientInstrumentor().instrument()
    FastAPIInstrumentor().instrument_app(app)

    Psycopg2Instrumentor().instrument()
    AsyncPGInstrumentor().instrument()


def add_open_telemetry_spans(_, __, event_dict):
    span = trace.get_current_span()
    if not span.is_recording():
        event_dict["span"] = None
        return event_dict
    event_dict["trace_sampled"] = span.is_recording()

    ctx = span.get_span_context()
    parent = getattr(span, "parent", None)

    event_dict["span"] = {
        "span_id": hex(ctx.span_id),
        "trace_id": hex(ctx.trace_id),
        "parent_span_id": None if not parent else hex(parent.span_id),
    }

    return event_dict


def init_logging(settings: Settings):
    """

    Ref: https://github.com/simonw/datasette/issues/1175#issuecomment-762488336
    """

    shared_processors: List[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        # add_open_telemetry_spans,
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
            "sqlalchemy": {"level": settings.SQLALCHEMY_LOGGING_LEVEL},
            "app": {"level": settings.LOGGING_LEVEL},
            "app.api.auth": {"level": settings.AUTH_LOGGING_LEVEL},
            "app.api.works": {"level": "DEBUG"},
            "app.crud.collection": {"level": "DEBUG"},
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
