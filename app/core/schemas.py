"""
Pydantic schemas for API request and response validation.
Separates API contracts from internal domain models.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.enums import (
    IncidentStatus,
    Severity,
    LogLevel,
    AnomalyType,
    SpanStatus,
    RootCauseCategory,
    CausalRole,
    TimelineEventType,
)


# =============================================================================
# Ingestion Request Schemas
# =============================================================================


class LogEntryCreate(BaseModel):
    """Request schema for ingesting a log entry."""
    timestamp: datetime
    service_name: str
    level: LogLevel
    message: str
    attributes: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2024-01-15T10:30:00Z",
                "service_name": "order-service",
                "level": "ERROR",
                "message": "Failed to connect to database: connection timeout",
                "attributes": {
                    "trace_id": "abc123",
                    "user_id": "user-456"
                }
            }
        }


class LogBatchCreate(BaseModel):
    """Request schema for batch log ingestion."""
    logs: List[LogEntryCreate]


class MetricDataPointCreate(BaseModel):
    """Request schema for ingesting a metric data point."""
    timestamp: datetime
    service_name: str
    metric_name: str
    value: float
    labels: Dict[str, str] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2024-01-15T10:30:00Z",
                "service_name": "order-service",
                "metric_name": "http_request_duration_ms",
                "value": 1250.5,
                "labels": {
                    "endpoint": "/api/orders",
                    "method": "POST",
                    "status_code": "500"
                }
            }
        }


class MetricBatchCreate(BaseModel):
    """Request schema for batch metric ingestion."""
    metrics: List[MetricDataPointCreate]


class SpanCreate(BaseModel):
    """Request schema for a trace span."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    service_name: str
    operation_name: str
    start_time: datetime
    end_time: datetime
    duration_ms: float
    status: SpanStatus = SpanStatus.OK
    attributes: Dict[str, Any] = Field(default_factory=dict)
    events: List[Dict[str, Any]] = Field(default_factory=list)


class TraceCreate(BaseModel):
    """Request schema for ingesting a distributed trace."""
    trace_id: str
    spans: List[SpanCreate]

    class Config:
        json_schema_extra = {
            "example": {
                "trace_id": "trace-abc123",
                "spans": [
                    {
                        "trace_id": "trace-abc123",
                        "span_id": "span-001",
                        "parent_span_id": None,
                        "service_name": "api-gateway",
                        "operation_name": "POST /orders",
                        "start_time": "2024-01-15T10:30:00Z",
                        "end_time": "2024-01-15T10:30:02Z",
                        "duration_ms": 2000,
                        "status": "OK",
                        "attributes": {}
                    }
                ]
            }
        }


class TraceBatchCreate(BaseModel):
    """Request schema for batch trace ingestion."""
    traces: List[TraceCreate]


# =============================================================================
# Incident Request Schemas
# =============================================================================


class IncidentCreate(BaseModel):
    """Request schema for creating an incident."""
    title: str
    description: str = ""
    severity: Severity = Severity.MEDIUM
    services_affected: List[str] = Field(default_factory=list)
    detected_at: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "title": "High latency in order processing",
                "description": "Multiple users reporting slow checkout",
                "severity": "high",
                "services_affected": ["order-service", "payment-service"]
            }
        }


class IncidentUpdate(BaseModel):
    """Request schema for updating an incident."""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[IncidentStatus] = None
    severity: Optional[Severity] = None
    services_affected: Optional[List[str]] = None
    resolved_at: Optional[datetime] = None


# =============================================================================
# Response Schemas
# =============================================================================


class LogEntryResponse(BaseModel):
    """Response schema for a log entry."""
    id: str
    timestamp: datetime
    service_name: str
    level: str
    message: str
    attributes: Dict[str, Any]
    anomaly_score: float
    is_anomaly: bool
    cluster_id: Optional[str]


class MetricDataPointResponse(BaseModel):
    """Response schema for a metric data point."""
    id: str
    timestamp: datetime
    service_name: str
    metric_name: str
    value: float
    labels: Dict[str, str]
    z_score: Optional[float]
    is_anomaly: bool


class MetricAnomalyResponse(BaseModel):
    """Response schema for a detected metric anomaly."""
    id: str
    service_name: str
    metric_name: str
    detected_at: datetime
    anomaly_type: str
    severity: str
    severity_score: float
    baseline_value: float
    anomaly_value: float
    z_score: float
    description: str


class LogClusterResponse(BaseModel):
    """Response schema for a log cluster."""
    cluster_id: str
    representative_message: str
    count: int
    services_affected: List[str]
    severity_distribution: Dict[str, int]
    first_seen: datetime
    last_seen: datetime


class RootCauseCandidateResponse(BaseModel):
    """Response schema for a root cause candidate."""
    id: str
    service_name: str
    category: str
    hypothesis: str
    confidence_score: float
    causal_role: str
    is_upstream: bool
    downstream_impact: List[str]
    supporting_metrics_count: int
    supporting_logs_count: int
    supporting_traces_count: int


class TimelineEventResponse(BaseModel):
    """Response schema for a timeline event."""
    id: str
    timestamp: datetime
    event_type: str
    service_name: str
    description: str
    severity: str


class IncidentResponse(BaseModel):
    """Response schema for an incident."""
    id: str
    title: str
    description: str
    status: str
    severity: str
    detected_at: datetime
    resolved_at: Optional[datetime]
    services_affected: List[str]
    created_at: datetime
    updated_at: datetime


class IncidentDetailResponse(BaseModel):
    """Detailed response schema for an incident with analysis."""
    id: str
    title: str
    description: str
    status: str
    severity: str
    detected_at: datetime
    resolved_at: Optional[datetime]
    services_affected: List[str]
    root_cause_candidates: List[RootCauseCandidateResponse]
    timeline: List[TimelineEventResponse]
    explanation: Optional[str]
    created_at: datetime
    updated_at: datetime


class IncidentAnalysisResponse(BaseModel):
    """Response schema for incident analysis results."""
    incident_id: str
    status: str
    root_cause: Optional[RootCauseCandidateResponse]
    all_candidates: List[RootCauseCandidateResponse]
    timeline: List[TimelineEventResponse]
    explanation: str
    confidence: float
    analysis_duration_ms: float


# =============================================================================
# Service Schemas
# =============================================================================


class ServiceHealthResponse(BaseModel):
    """Response schema for service health."""
    service_name: str
    timestamp: datetime
    health_score: float
    error_rate: float
    avg_latency_ms: float
    anomaly_count: int
    error_log_count: int


class ServiceDependencyResponse(BaseModel):
    """Response schema for service dependencies."""
    service_name: str
    upstream: List[str]
    downstream: List[str]
    edges: List[Dict[str, Any]]


# =============================================================================
# Common Response Schemas
# =============================================================================


class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = True
    message: str = "Operation completed successfully"


class ErrorResponse(BaseModel):
    """Generic error response."""
    success: bool = False
    error: str
    detail: Optional[str] = None


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


class IngestResponse(BaseModel):
    """Response schema for ingestion operations."""
    success: bool = True
    ingested_count: int
    failed_count: int = 0
    errors: List[str] = Field(default_factory=list)
