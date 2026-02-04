"""
Application configuration using pydantic-settings.
Loads settings from environment variables and .env file.
"""

from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "AI Incident Root Cause Analyzer"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"

    # API Server
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    workers: int = 1

    # CORS
    cors_origins: List[str] = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]

    # Telemetry Store
    telemetry_retention_hours: int = 24
    max_logs_per_service: int = 100000
    max_metrics_per_service: int = 100000
    max_traces: int = 50000

    # Log Intelligence
    log_embedding_model: str = "all-MiniLM-L6-v2"
    log_embedding_batch_size: int = 32
    log_cluster_similarity_threshold: float = 0.85
    log_cluster_min_size: int = 3

    # Metric Intelligence
    metric_zscore_threshold: float = 3.0
    metric_baseline_window_minutes: int = 60
    metric_min_data_points: int = 10
    cusum_threshold: float = 5.0
    cusum_drift: float = 0.5

    # Trace Intelligence
    trace_error_threshold: float = 0.1  # 10% error rate threshold
    graph_max_depth: int = 5

    # Incident Detection
    incident_time_window_minutes: int = 30
    incident_min_anomalies: int = 2
    incident_auto_detection: bool = True

    # Root Cause Analysis
    rca_temporal_weight: float = 0.25
    rca_propagation_weight: float = 0.25
    rca_evidence_weight: float = 0.20
    rca_centrality_weight: float = 0.15
    rca_specificity_weight: float = 0.15
    rca_root_cause_threshold: float = 0.7
    rca_contributing_threshold: float = 0.4

    # Correlation
    correlation_window_seconds: int = 30
    correlation_min_services: int = 2

    # External Services (optional - for future use)
    database_url: Optional[str] = None
    redis_url: Optional[str] = None

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience accessor
settings = get_settings()
