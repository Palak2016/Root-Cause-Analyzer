"""
Structured logging configuration for the Root Cause Analyzer.
Provides JSON and text formatters with context propagation.
"""

import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict, Optional
from contextvars import ContextVar

# Context variables for request tracking
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
service_name_var: ContextVar[str] = ContextVar("service_name", default="rca-analyzer")


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": service_name_var.get(),
        }

        # Add request ID if available
        request_id = request_id_var.get()
        if request_id:
            log_data["request_id"] = request_id

        # Add source location
        log_data["source"] = {
            "file": record.filename,
            "line": record.lineno,
            "function": record.funcName,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "extra"):
            log_data["extra"] = record.extra

        return json.dumps(log_data)


class TextFormatter(logging.Formatter):
    """Human-readable text formatter for development."""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        reset = self.RESET

        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        request_id = request_id_var.get()
        req_str = f"[{request_id[:8]}]" if request_id else ""

        message = f"{timestamp} {color}{record.levelname:8}{reset} {req_str} {record.name}: {record.getMessage()}"

        if record.exc_info:
            message += "\n" + self.formatException(record.exc_info)

        return message


def setup_logging(
    level: str = "INFO",
    format_type: str = "json",
    service_name: str = "rca-analyzer",
) -> None:
    """
    Configure application logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: "json" for structured logging, "text" for human-readable
        service_name: Service name to include in logs
    """
    service_name_var.set(service_name)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create handler
    handler = logging.StreamHandler(sys.stdout)

    # Set formatter
    if format_type.lower() == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(TextFormatter())

    root_logger.addHandler(handler)

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name)


class LoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that includes extra context in all log messages."""

    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        extra = kwargs.get("extra", {})
        extra.update(self.extra)
        kwargs["extra"] = extra
        return msg, kwargs


def get_context_logger(name: str, **context) -> LoggerAdapter:
    """
    Get a logger with additional context fields.

    Args:
        name: Logger name
        **context: Additional context fields to include in all logs

    Returns:
        LoggerAdapter with context
    """
    logger = logging.getLogger(name)
    return LoggerAdapter(logger, context)


def set_request_id(request_id: str) -> None:
    """Set the request ID for the current context."""
    request_id_var.set(request_id)


def get_request_id() -> Optional[str]:
    """Get the current request ID."""
    return request_id_var.get()
