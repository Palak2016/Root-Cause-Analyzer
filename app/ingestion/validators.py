"""
Payload validation for ingested telemetry data.
"""

from datetime import datetime, timedelta
from typing import List, Tuple, Optional
from pydantic import ValidationError

from app.core.schemas import (
    LogEntryCreate,
    MetricDataPointCreate,
    TraceCreate,
    SpanCreate,
)
from app.core.models import LogEntry, MetricDataPoint, Trace, Span
from app.core.enums import LogLevel, SpanStatus
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ValidationResult:
    """Result of validation containing valid items and errors."""

    def __init__(self):
        self.valid_items: List = []
        self.errors: List[str] = []

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def success_count(self) -> int:
        return len(self.valid_items)

    @property
    def error_count(self) -> int:
        return len(self.errors)


def validate_timestamp(timestamp: datetime) -> Tuple[bool, Optional[str]]:
    """
    Validate that timestamp is reasonable.
    Rejects timestamps too far in the past or future.
    """
    now = datetime.utcnow()
    max_past = now - timedelta(days=7)
    max_future = now + timedelta(minutes=5)

    if timestamp < max_past:
        return False, f"Timestamp {timestamp} is too far in the past (>7 days)"

    if timestamp > max_future:
        return False, f"Timestamp {timestamp} is in the future"

    return True, None


def validate_service_name(service_name: str) -> Tuple[bool, Optional[str]]:
    """Validate service name format."""
    if not service_name:
        return False, "Service name cannot be empty"

    if len(service_name) > 128:
        return False, "Service name too long (max 128 chars)"

    # Basic sanitization - alphanumeric, hyphens, underscores
    import re
    if not re.match(r'^[a-zA-Z0-9_-]+$', service_name):
        return False, "Service name contains invalid characters"

    return True, None


def validate_log_entry(data: LogEntryCreate) -> Tuple[Optional[LogEntry], Optional[str]]:
    """
    Validate and convert a log entry create schema to model.

    Returns:
        Tuple of (LogEntry or None, error message or None)
    """
    # Validate timestamp
    valid, error = validate_timestamp(data.timestamp)
    if not valid:
        return None, error

    # Validate service name
    valid, error = validate_service_name(data.service_name)
    if not valid:
        return None, error

    # Validate message
    if not data.message:
        return None, "Log message cannot be empty"

    if len(data.message) > 65536:
        return None, "Log message too long (max 64KB)"

    # Create model
    try:
        log_entry = LogEntry(
            timestamp=data.timestamp,
            service_name=data.service_name,
            level=data.level,
            message=data.message,
            attributes=data.attributes,
        )
        return log_entry, None
    except Exception as e:
        return None, f"Failed to create log entry: {str(e)}"


def validate_log_batch(logs: List[LogEntryCreate]) -> ValidationResult:
    """Validate a batch of log entries."""
    result = ValidationResult()

    for idx, log_data in enumerate(logs):
        log_entry, error = validate_log_entry(log_data)
        if error:
            result.errors.append(f"Log {idx}: {error}")
        else:
            result.valid_items.append(log_entry)

    return result


def validate_metric_data_point(
    data: MetricDataPointCreate,
) -> Tuple[Optional[MetricDataPoint], Optional[str]]:
    """
    Validate and convert a metric data point create schema to model.
    """
    # Validate timestamp
    valid, error = validate_timestamp(data.timestamp)
    if not valid:
        return None, error

    # Validate service name
    valid, error = validate_service_name(data.service_name)
    if not valid:
        return None, error

    # Validate metric name
    if not data.metric_name:
        return None, "Metric name cannot be empty"

    if len(data.metric_name) > 256:
        return None, "Metric name too long (max 256 chars)"

    # Validate value
    import math
    if math.isnan(data.value) or math.isinf(data.value):
        return None, "Metric value cannot be NaN or Infinity"

    # Create model
    try:
        metric = MetricDataPoint(
            timestamp=data.timestamp,
            service_name=data.service_name,
            metric_name=data.metric_name,
            value=data.value,
            labels=data.labels,
        )
        return metric, None
    except Exception as e:
        return None, f"Failed to create metric: {str(e)}"


def validate_metric_batch(metrics: List[MetricDataPointCreate]) -> ValidationResult:
    """Validate a batch of metric data points."""
    result = ValidationResult()

    for idx, metric_data in enumerate(metrics):
        metric, error = validate_metric_data_point(metric_data)
        if error:
            result.errors.append(f"Metric {idx}: {error}")
        else:
            result.valid_items.append(metric)

    return result


def validate_span(data: SpanCreate) -> Tuple[Optional[Span], Optional[str]]:
    """Validate and convert a span create schema to model."""
    # Validate timestamps
    valid, error = validate_timestamp(data.start_time)
    if not valid:
        return None, f"start_time: {error}"

    valid, error = validate_timestamp(data.end_time)
    if not valid:
        return None, f"end_time: {error}"

    # End time should be after start time
    if data.end_time < data.start_time:
        return None, "end_time cannot be before start_time"

    # Validate service name
    valid, error = validate_service_name(data.service_name)
    if not valid:
        return None, error

    # Validate IDs
    if not data.trace_id:
        return None, "trace_id cannot be empty"

    if not data.span_id:
        return None, "span_id cannot be empty"

    # Create model
    try:
        span = Span(
            trace_id=data.trace_id,
            span_id=data.span_id,
            parent_span_id=data.parent_span_id,
            service_name=data.service_name,
            operation_name=data.operation_name,
            start_time=data.start_time,
            end_time=data.end_time,
            duration_ms=data.duration_ms,
            status=data.status,
            attributes=data.attributes,
            events=data.events,
        )
        return span, None
    except Exception as e:
        return None, f"Failed to create span: {str(e)}"


def validate_trace(data: TraceCreate) -> Tuple[Optional[Trace], Optional[str]]:
    """Validate and convert a trace create schema to model."""
    if not data.trace_id:
        return None, "trace_id cannot be empty"

    if not data.spans:
        return None, "Trace must have at least one span"

    # Validate all spans
    validated_spans = []
    for idx, span_data in enumerate(data.spans):
        span, error = validate_span(span_data)
        if error:
            return None, f"Span {idx}: {error}"
        validated_spans.append(span)

    # Verify all spans have same trace_id
    for span in validated_spans:
        if span.trace_id != data.trace_id:
            return None, f"Span {span.span_id} has mismatched trace_id"

    # Create trace model
    try:
        trace = Trace(
            trace_id=data.trace_id,
            spans=validated_spans,
        )
        return trace, None
    except Exception as e:
        return None, f"Failed to create trace: {str(e)}"


def validate_trace_batch(traces: List[TraceCreate]) -> ValidationResult:
    """Validate a batch of traces."""
    result = ValidationResult()

    for idx, trace_data in enumerate(traces):
        trace, error = validate_trace(trace_data)
        if error:
            result.errors.append(f"Trace {idx}: {error}")
        else:
            result.valid_items.append(trace)

    return result
