"""
Data ingestion module for the Root Cause Analyzer.
Handles receiving and storing logs, metrics, and traces.
"""

from app.ingestion.repository import TelemetryStore, get_telemetry_store
from app.ingestion.routes import router as ingestion_router

__all__ = [
    "TelemetryStore",
    "get_telemetry_store",
    "ingestion_router",
]
