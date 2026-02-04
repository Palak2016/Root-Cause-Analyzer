"""
Core enumerations for the AI-Based Incident Root Cause Analyzer.
Defines status codes, severity levels, and signal types used across the system.
"""

from enum import Enum


class IncidentStatus(str, Enum):
    """Status of an incident through its lifecycle."""
    DETECTED = "detected"
    ANALYZING = "analyzing"
    ROOT_CAUSE_FOUND = "root_cause_found"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Severity(str, Enum):
    """Severity levels for incidents and anomalies."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class LogLevel(str, Enum):
    """Standard log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    WARNING = "WARNING"
    ERROR = "ERROR"
    FATAL = "FATAL"
    CRITICAL = "CRITICAL"


class SignalType(str, Enum):
    """Types of observability signals."""
    LOG = "log"
    METRIC = "metric"
    TRACE = "trace"


class AnomalyType(str, Enum):
    """Types of detected anomalies in metrics."""
    SPIKE = "spike"
    DROP = "drop"
    LEVEL_SHIFT = "level_shift"
    TREND_CHANGE = "trend_change"
    OUTLIER = "outlier"


class SpanStatus(str, Enum):
    """Status of a trace span."""
    OK = "OK"
    ERROR = "ERROR"
    UNSET = "UNSET"


class RootCauseCategory(str, Enum):
    """Categories of root causes."""
    INFRASTRUCTURE = "infrastructure"
    CODE_ERROR = "code_error"
    DEPENDENCY = "dependency"
    CONFIGURATION = "configuration"
    CAPACITY = "capacity"
    NETWORK = "network"
    DATABASE = "database"
    EXTERNAL = "external"
    UNKNOWN = "unknown"


class CausalRole(str, Enum):
    """Role of a service in an incident's causal chain."""
    ROOT_CAUSE = "root_cause"
    CONTRIBUTING = "contributing"
    SYMPTOM = "symptom"
    UNRELATED = "unrelated"


class ServiceType(str, Enum):
    """Types of services in the architecture."""
    API = "api"
    WEB = "web"
    WORKER = "worker"
    DATABASE = "database"
    CACHE = "cache"
    QUEUE = "queue"
    GATEWAY = "gateway"
    EXTERNAL = "external"
    UNKNOWN = "unknown"


class TimelineEventType(str, Enum):
    """Types of events in incident timeline."""
    METRIC_ANOMALY = "metric_anomaly"
    ERROR_LOG = "error_log"
    TRACE_ERROR = "trace_error"
    STATUS_CHANGE = "status_change"
    DEPLOYMENT = "deployment"
    CONFIG_CHANGE = "config_change"
    ALERT_FIRED = "alert_fired"
