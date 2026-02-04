"""
API routes for data ingestion - logs, metrics, and traces.
"""

from typing import List
from fastapi import APIRouter, HTTPException, status

from app.core.schemas import (
    LogEntryCreate,
    LogBatchCreate,
    MetricDataPointCreate,
    MetricBatchCreate,
    TraceCreate,
    TraceBatchCreate,
    IngestResponse,
    LogEntryResponse,
    MetricDataPointResponse,
)
from app.ingestion.repository import get_telemetry_store
from app.ingestion.validators import (
    validate_log_entry,
    validate_log_batch,
    validate_metric_data_point,
    validate_metric_batch,
    validate_trace,
    validate_trace_batch,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingestion"])


# =============================================================================
# Log Ingestion
# =============================================================================


@router.post(
    "/log",
    response_model=IngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a single log entry",
)
async def ingest_log(log_data: LogEntryCreate) -> IngestResponse:
    """
    Ingest a single log entry.

    The log entry is validated and stored in the telemetry store.
    """
    store = get_telemetry_store()

    log_entry, error = validate_log_entry(log_data)
    if error:
        return IngestResponse(
            success=False,
            ingested_count=0,
            failed_count=1,
            errors=[error],
        )

    store.add_log(log_entry)
    logger.debug(f"Ingested log from {log_data.service_name}")

    return IngestResponse(
        success=True,
        ingested_count=1,
        failed_count=0,
    )


@router.post(
    "/logs",
    response_model=IngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a batch of log entries",
)
async def ingest_logs_batch(batch: LogBatchCreate) -> IngestResponse:
    """
    Ingest multiple log entries in a single request.

    Validation errors for individual entries do not fail the entire batch.
    """
    store = get_telemetry_store()

    result = validate_log_batch(batch.logs)

    # Store valid entries
    if result.valid_items:
        store.add_logs_batch(result.valid_items)

    logger.info(
        f"Batch log ingestion: {result.success_count} succeeded, "
        f"{result.error_count} failed"
    )

    return IngestResponse(
        success=result.success_count > 0,
        ingested_count=result.success_count,
        failed_count=result.error_count,
        errors=result.errors[:10],  # Limit error messages
    )


# =============================================================================
# Metric Ingestion
# =============================================================================


@router.post(
    "/metric",
    response_model=IngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a single metric data point",
)
async def ingest_metric(metric_data: MetricDataPointCreate) -> IngestResponse:
    """
    Ingest a single metric data point.

    The metric is validated and stored in the telemetry store.
    """
    store = get_telemetry_store()

    metric, error = validate_metric_data_point(metric_data)
    if error:
        return IngestResponse(
            success=False,
            ingested_count=0,
            failed_count=1,
            errors=[error],
        )

    store.add_metric(metric)
    logger.debug(
        f"Ingested metric {metric_data.metric_name} from {metric_data.service_name}"
    )

    return IngestResponse(
        success=True,
        ingested_count=1,
        failed_count=0,
    )


@router.post(
    "/metrics",
    response_model=IngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a batch of metric data points",
)
async def ingest_metrics_batch(batch: MetricBatchCreate) -> IngestResponse:
    """
    Ingest multiple metric data points in a single request.

    Validation errors for individual entries do not fail the entire batch.
    """
    store = get_telemetry_store()

    result = validate_metric_batch(batch.metrics)

    # Store valid entries
    if result.valid_items:
        store.add_metrics_batch(result.valid_items)

    logger.info(
        f"Batch metric ingestion: {result.success_count} succeeded, "
        f"{result.error_count} failed"
    )

    return IngestResponse(
        success=result.success_count > 0,
        ingested_count=result.success_count,
        failed_count=result.error_count,
        errors=result.errors[:10],
    )


# =============================================================================
# Trace Ingestion
# =============================================================================


@router.post(
    "/trace",
    response_model=IngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a single distributed trace",
)
async def ingest_trace(trace_data: TraceCreate) -> IngestResponse:
    """
    Ingest a single distributed trace.

    The trace is validated and stored in the telemetry store.
    Service dependencies are extracted from spans.
    """
    store = get_telemetry_store()

    trace, error = validate_trace(trace_data)
    if error:
        return IngestResponse(
            success=False,
            ingested_count=0,
            failed_count=1,
            errors=[error],
        )

    store.add_trace(trace)
    logger.debug(f"Ingested trace {trace_data.trace_id} with {len(trace.spans)} spans")

    return IngestResponse(
        success=True,
        ingested_count=1,
        failed_count=0,
    )


@router.post(
    "/traces",
    response_model=IngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a batch of distributed traces",
)
async def ingest_traces_batch(batch: TraceBatchCreate) -> IngestResponse:
    """
    Ingest multiple distributed traces in a single request.

    Validation errors for individual traces do not fail the entire batch.
    """
    store = get_telemetry_store()

    result = validate_trace_batch(batch.traces)

    # Store valid entries
    if result.valid_items:
        store.add_traces_batch(result.valid_items)

    logger.info(
        f"Batch trace ingestion: {result.success_count} succeeded, "
        f"{result.error_count} failed"
    )

    return IngestResponse(
        success=result.success_count > 0,
        ingested_count=result.success_count,
        failed_count=result.error_count,
        errors=result.errors[:10],
    )


# =============================================================================
# Store Stats
# =============================================================================


@router.get(
    "/stats",
    summary="Get telemetry store statistics",
)
async def get_ingestion_stats():
    """Get statistics about the telemetry store."""
    store = get_telemetry_store()
    return store.get_stats()


@router.get(
    "/services",
    response_model=List[str],
    summary="Get list of all known services",
)
async def get_services():
    """Get list of all services that have sent telemetry."""
    store = get_telemetry_store()
    return store.get_services()
