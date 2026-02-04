"""
In-memory telemetry store for logs, metrics, and traces.
Provides time-window queries and efficient lookups.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from collections import defaultdict
import threading

from app.core.models import LogEntry, MetricDataPoint, Trace, Span
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class TelemetryStore:
    """
    Thread-safe in-memory store for telemetry data.
    Supports time-based windowing and service-based queries.
    """

    def __init__(
        self,
        retention_hours: int = None,
        max_logs_per_service: int = None,
        max_metrics_per_service: int = None,
        max_traces: int = None,
    ):
        self._lock = threading.RLock()
        self._retention = timedelta(
            hours=retention_hours or settings.telemetry_retention_hours
        )
        self._max_logs = max_logs_per_service or settings.max_logs_per_service
        self._max_metrics = max_metrics_per_service or settings.max_metrics_per_service
        self._max_traces = max_traces or settings.max_traces

        # Primary storage - keyed by service name
        self._logs: Dict[str, List[LogEntry]] = defaultdict(list)
        self._metrics: Dict[str, List[MetricDataPoint]] = defaultdict(list)
        self._traces: Dict[str, Trace] = {}  # trace_id -> Trace

        # Indexes
        self._logs_by_id: Dict[str, LogEntry] = {}
        self._metrics_by_id: Dict[str, MetricDataPoint] = {}
        self._services: Set[str] = set()

        # Stats
        self._stats = {
            "logs_ingested": 0,
            "metrics_ingested": 0,
            "traces_ingested": 0,
        }

    # =========================================================================
    # Log Operations
    # =========================================================================

    def add_log(self, log: LogEntry) -> str:
        """Add a log entry to the store."""
        with self._lock:
            self._logs[log.service_name].append(log)
            self._logs_by_id[log.id] = log
            self._services.add(log.service_name)
            self._stats["logs_ingested"] += 1

            # Enforce max limit
            if len(self._logs[log.service_name]) > self._max_logs:
                removed = self._logs[log.service_name].pop(0)
                del self._logs_by_id[removed.id]

            return log.id

    def add_logs_batch(self, logs: List[LogEntry]) -> List[str]:
        """Add multiple log entries."""
        return [self.add_log(log) for log in logs]

    def get_log_by_id(self, log_id: str) -> Optional[LogEntry]:
        """Get a specific log by ID."""
        with self._lock:
            return self._logs_by_id.get(log_id)

    def get_logs_in_window(
        self,
        start: datetime,
        end: datetime,
        services: Optional[List[str]] = None,
        levels: Optional[List[str]] = None,
    ) -> List[LogEntry]:
        """
        Get logs within a time window.

        Args:
            start: Window start time
            end: Window end time
            services: Filter by service names (None = all)
            levels: Filter by log levels (None = all)
        """
        with self._lock:
            results = []
            target_services = services or list(self._logs.keys())

            for service in target_services:
                for log in self._logs.get(service, []):
                    if not (start <= log.timestamp <= end):
                        continue
                    if levels and log.level not in levels:
                        continue
                    results.append(log)

            return sorted(results, key=lambda x: x.timestamp)

    def get_error_logs_in_window(
        self,
        start: datetime,
        end: datetime,
        services: Optional[List[str]] = None,
    ) -> List[LogEntry]:
        """Get only error and fatal logs within a time window."""
        error_levels = ["ERROR", "FATAL", "CRITICAL"]
        return self.get_logs_in_window(start, end, services, error_levels)

    # =========================================================================
    # Metric Operations
    # =========================================================================

    def add_metric(self, metric: MetricDataPoint) -> str:
        """Add a metric data point to the store."""
        with self._lock:
            self._metrics[metric.service_name].append(metric)
            self._metrics_by_id[metric.id] = metric
            self._services.add(metric.service_name)
            self._stats["metrics_ingested"] += 1

            # Enforce max limit
            if len(self._metrics[metric.service_name]) > self._max_metrics:
                removed = self._metrics[metric.service_name].pop(0)
                del self._metrics_by_id[removed.id]

            return metric.id

    def add_metrics_batch(self, metrics: List[MetricDataPoint]) -> List[str]:
        """Add multiple metric data points."""
        return [self.add_metric(metric) for metric in metrics]

    def get_metric_by_id(self, metric_id: str) -> Optional[MetricDataPoint]:
        """Get a specific metric by ID."""
        with self._lock:
            return self._metrics_by_id.get(metric_id)

    def get_metric_series(
        self,
        service_name: str,
        metric_name: str,
        start: datetime,
        end: datetime,
    ) -> List[MetricDataPoint]:
        """
        Get metric time series for analysis.

        Args:
            service_name: Service to query
            metric_name: Metric name to filter
            start: Window start time
            end: Window end time
        """
        with self._lock:
            series = []
            for metric in self._metrics.get(service_name, []):
                if metric.metric_name != metric_name:
                    continue
                if start <= metric.timestamp <= end:
                    series.append(metric)

            return sorted(series, key=lambda x: x.timestamp)

    def get_metric_names_for_service(self, service_name: str) -> List[str]:
        """Get list of unique metric names for a service."""
        with self._lock:
            names = set()
            for metric in self._metrics.get(service_name, []):
                names.add(metric.metric_name)
            return list(names)

    def get_metrics_in_window(
        self,
        start: datetime,
        end: datetime,
        services: Optional[List[str]] = None,
        metric_names: Optional[List[str]] = None,
    ) -> List[MetricDataPoint]:
        """Get all metrics within a time window."""
        with self._lock:
            results = []
            target_services = services or list(self._metrics.keys())

            for service in target_services:
                for metric in self._metrics.get(service, []):
                    if not (start <= metric.timestamp <= end):
                        continue
                    if metric_names and metric.metric_name not in metric_names:
                        continue
                    results.append(metric)

            return sorted(results, key=lambda x: x.timestamp)

    # =========================================================================
    # Trace Operations
    # =========================================================================

    def add_trace(self, trace: Trace) -> str:
        """Add a trace to the store."""
        with self._lock:
            self._traces[trace.trace_id] = trace
            self._stats["traces_ingested"] += 1

            # Track services from spans
            for span in trace.spans:
                self._services.add(span.service_name)

            # Enforce max limit
            if len(self._traces) > self._max_traces:
                # Remove oldest trace
                oldest_id = next(iter(self._traces))
                del self._traces[oldest_id]

            return trace.trace_id

    def add_traces_batch(self, traces: List[Trace]) -> List[str]:
        """Add multiple traces."""
        return [self.add_trace(trace) for trace in traces]

    def get_trace_by_id(self, trace_id: str) -> Optional[Trace]:
        """Get a specific trace by ID."""
        with self._lock:
            return self._traces.get(trace_id)

    def get_traces_for_service(
        self,
        service_name: str,
        start: datetime,
        end: datetime,
    ) -> List[Trace]:
        """Get traces that include a specific service."""
        with self._lock:
            results = []
            for trace in self._traces.values():
                for span in trace.spans:
                    if span.service_name == service_name:
                        if start <= span.start_time <= end:
                            results.append(trace)
                            break
            return results

    def get_error_traces_in_window(
        self,
        start: datetime,
        end: datetime,
        services: Optional[List[str]] = None,
    ) -> List[Trace]:
        """Get traces with errors within a time window."""
        with self._lock:
            results = []
            for trace in self._traces.values():
                if not trace.has_error:
                    continue

                # Check if any span falls in window
                for span in trace.spans:
                    if services and span.service_name not in services:
                        continue
                    if start <= span.start_time <= end:
                        results.append(trace)
                        break

            return results

    # =========================================================================
    # Service Operations
    # =========================================================================

    def get_services(self) -> List[str]:
        """Get list of all known services."""
        with self._lock:
            return list(self._services)

    # =========================================================================
    # Maintenance Operations
    # =========================================================================

    def cleanup_old_data(self) -> Dict[str, int]:
        """Remove data older than retention period."""
        cutoff = datetime.utcnow() - self._retention
        removed = {"logs": 0, "metrics": 0, "traces": 0}

        with self._lock:
            # Clean logs
            for service in list(self._logs.keys()):
                original = len(self._logs[service])
                self._logs[service] = [
                    log for log in self._logs[service] if log.timestamp > cutoff
                ]
                removed["logs"] += original - len(self._logs[service])

            # Clean metrics
            for service in list(self._metrics.keys()):
                original = len(self._metrics[service])
                self._metrics[service] = [
                    m for m in self._metrics[service] if m.timestamp > cutoff
                ]
                removed["metrics"] += original - len(self._metrics[service])

            # Clean traces
            traces_to_remove = []
            for trace_id, trace in self._traces.items():
                if trace.spans:
                    latest_span = max(trace.spans, key=lambda s: s.end_time)
                    if latest_span.end_time < cutoff:
                        traces_to_remove.append(trace_id)

            for trace_id in traces_to_remove:
                del self._traces[trace_id]
            removed["traces"] = len(traces_to_remove)

        logger.info(
            f"Cleanup completed: removed {removed['logs']} logs, "
            f"{removed['metrics']} metrics, {removed['traces']} traces"
        )

        return removed

    def get_stats(self) -> Dict:
        """Get store statistics."""
        with self._lock:
            return {
                **self._stats,
                "services_count": len(self._services),
                "logs_stored": sum(len(logs) for logs in self._logs.values()),
                "metrics_stored": sum(len(m) for m in self._metrics.values()),
                "traces_stored": len(self._traces),
            }

    def clear(self) -> None:
        """Clear all data from the store."""
        with self._lock:
            self._logs.clear()
            self._metrics.clear()
            self._traces.clear()
            self._logs_by_id.clear()
            self._metrics_by_id.clear()
            self._services.clear()
            logger.info("Telemetry store cleared")


# Singleton instance
_telemetry_store: Optional[TelemetryStore] = None


def get_telemetry_store() -> TelemetryStore:
    """Get the singleton telemetry store instance."""
    global _telemetry_store
    if _telemetry_store is None:
        _telemetry_store = TelemetryStore()
    return _telemetry_store
