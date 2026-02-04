"""
Core domain models for the AI-Based Incident Root Cause Analyzer.
Defines data structures for logs, metrics, traces, incidents, and root cause analysis.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid

from app.core.enums import (
    IncidentStatus,
    Severity,
    LogLevel,
    AnomalyType,
    SpanStatus,
    RootCauseCategory,
    CausalRole,
    ServiceType,
    TimelineEventType,
)


def generate_id() -> str:
    """Generate a unique identifier."""
    return str(uuid.uuid4())


# =============================================================================
# Telemetry Models - Raw observability data
# =============================================================================


class LogEntry(BaseModel):
    """Single log entry from any service."""
    id: str = Field(default_factory=generate_id)
    timestamp: datetime
    service_name: str
    level: LogLevel
    message: str
    attributes: Dict[str, Any] = Field(default_factory=dict)

    # Computed during analysis
    embedding: Optional[List[float]] = None
    cluster_id: Optional[str] = None
    anomaly_score: float = 0.0
    is_anomaly: bool = False

    class Config:
        use_enum_values = True


class MetricDataPoint(BaseModel):
    """Single metric observation."""
    id: str = Field(default_factory=generate_id)
    timestamp: datetime
    service_name: str
    metric_name: str
    value: float
    labels: Dict[str, str] = Field(default_factory=dict)

    # Computed during analysis
    z_score: Optional[float] = None
    is_anomaly: bool = False
    anomaly_type: Optional[AnomalyType] = None

    class Config:
        use_enum_values = True


class Span(BaseModel):
    """Single span from a distributed trace."""
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

    class Config:
        use_enum_values = True


class Trace(BaseModel):
    """Complete distributed trace composed of spans."""
    trace_id: str
    spans: List[Span] = Field(default_factory=list)
    root_service: Optional[str] = None
    total_duration_ms: float = 0.0
    has_error: bool = False

    def model_post_init(self, __context) -> None:
        """Calculate derived fields after initialization."""
        if self.spans:
            # Find root span (no parent)
            for span in self.spans:
                if span.parent_span_id is None:
                    self.root_service = span.service_name
                    break

            # Check for errors
            self.has_error = any(
                span.status == SpanStatus.ERROR for span in self.spans
            )

            # Calculate total duration from root span
            root_spans = [s for s in self.spans if s.parent_span_id is None]
            if root_spans:
                self.total_duration_ms = root_spans[0].duration_ms


# =============================================================================
# Analysis Models - Derived from signal intelligence
# =============================================================================


class LogCluster(BaseModel):
    """Cluster of semantically similar logs."""
    cluster_id: str = Field(default_factory=generate_id)
    representative_message: str
    log_ids: List[str] = Field(default_factory=list)
    centroid_embedding: Optional[List[float]] = None
    severity_distribution: Dict[str, int] = Field(default_factory=dict)
    services_affected: List[str] = Field(default_factory=list)
    first_seen: datetime
    last_seen: datetime
    count: int = 0


class MetricAnomaly(BaseModel):
    """Detected anomaly in metric time series."""
    id: str = Field(default_factory=generate_id)
    service_name: str
    metric_name: str
    detected_at: datetime
    anomaly_type: AnomalyType
    severity: Severity = Severity.MEDIUM
    severity_score: float = 0.5
    baseline_value: float
    anomaly_value: float
    z_score: float
    description: str = ""

    class Config:
        use_enum_values = True


class ChangePoint(BaseModel):
    """Detected change point in metric series."""
    timestamp: datetime
    change_type: AnomalyType
    magnitude: float
    confidence: float
    baseline_mean: float
    new_mean: float


# =============================================================================
# Service & Graph Models
# =============================================================================


class ServiceNode(BaseModel):
    """Node representing a service in the dependency graph."""
    service_name: str
    service_type: ServiceType = ServiceType.UNKNOWN
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class ServiceEdge(BaseModel):
    """Edge representing a service-to-service dependency."""
    caller: str
    callee: str
    operation: str
    avg_latency_ms: float = 0.0
    error_rate: float = 0.0
    call_count: int = 0


class ServiceHealth(BaseModel):
    """Health snapshot for a single service."""
    service_name: str
    timestamp: datetime
    health_score: float = 1.0  # 0.0 (unhealthy) to 1.0 (healthy)
    error_rate: float = 0.0
    avg_latency_ms: float = 0.0
    anomaly_count: int = 0
    error_log_count: int = 0
    active_incidents: int = 0


# =============================================================================
# Incident & Root Cause Models
# =============================================================================


class RootCauseCandidate(BaseModel):
    """Potential root cause with supporting evidence."""
    id: str = Field(default_factory=generate_id)
    service_name: str
    category: RootCauseCategory = RootCauseCategory.UNKNOWN
    hypothesis: str
    confidence_score: float = 0.0

    # Evidence references
    supporting_metrics: List[str] = Field(default_factory=list)
    supporting_logs: List[str] = Field(default_factory=list)
    supporting_traces: List[str] = Field(default_factory=list)

    # Causal analysis
    causal_role: CausalRole = CausalRole.SYMPTOM
    is_upstream: bool = False
    downstream_impact: List[str] = Field(default_factory=list)
    temporal_precedence_score: float = 0.0
    propagation_score: float = 0.0
    evidence_strength_score: float = 0.0
    graph_centrality_score: float = 0.0
    error_specificity_score: float = 0.0

    class Config:
        use_enum_values = True


class TimelineEvent(BaseModel):
    """Event in an incident timeline."""
    id: str = Field(default_factory=generate_id)
    timestamp: datetime
    event_type: TimelineEventType
    service_name: str
    description: str
    severity: Severity = Severity.INFO
    severity_score: float = 0.5
    related_entity_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class Incident(BaseModel):
    """Detected production incident."""
    id: str = Field(default_factory=generate_id)
    title: str
    description: str = ""
    status: IncidentStatus = IncidentStatus.DETECTED
    severity: Severity = Severity.MEDIUM
    detected_at: datetime
    resolved_at: Optional[datetime] = None

    # Affected scope
    services_affected: List[str] = Field(default_factory=list)

    # Associated signals (IDs)
    metric_anomaly_ids: List[str] = Field(default_factory=list)
    log_cluster_ids: List[str] = Field(default_factory=list)
    error_trace_ids: List[str] = Field(default_factory=list)

    # Analysis results
    root_cause_candidates: List[RootCauseCandidate] = Field(default_factory=list)
    timeline: List[TimelineEvent] = Field(default_factory=list)

    # Explanation
    explanation: Optional[str] = None

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True


# =============================================================================
# Correlation Models
# =============================================================================


class CorrelatedSignals(BaseModel):
    """All signals correlated within a time window for a service."""
    service_name: str
    time_window_start: datetime
    time_window_end: datetime

    # Raw signal counts
    log_count: int = 0
    metric_count: int = 0
    trace_count: int = 0

    # Analyzed signals
    log_clusters: List[LogCluster] = Field(default_factory=list)
    metric_anomalies: List[MetricAnomaly] = Field(default_factory=list)
    error_traces: List[str] = Field(default_factory=list)  # trace IDs

    # Summary
    error_count: int = 0
    anomaly_count: int = 0
    health_score: float = 1.0
