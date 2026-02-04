"""
Health check API endpoints.
"""

from datetime import datetime
from fastapi import APIRouter

from app.config import settings
from app.ingestion.repository import get_telemetry_store

router = APIRouter(tags=["health"])


@router.get("/health", summary="Basic health check")
async def health_check():
    """
    Basic health check endpoint.
    Returns service status and version.
    """
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@router.get("/health/ready", summary="Readiness check")
async def readiness_check():
    """
    Readiness check for Kubernetes/container orchestration.
    Checks if the service is ready to accept traffic.
    """
    # Check telemetry store is initialized
    try:
        store = get_telemetry_store()
        stats = store.get_stats()
        store_ready = True
    except Exception:
        store_ready = False
        stats = {}

    ready = store_ready

    return {
        "ready": ready,
        "checks": {
            "telemetry_store": store_ready,
        },
        "stats": stats,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@router.get("/health/live", summary="Liveness check")
async def liveness_check():
    """
    Liveness check for Kubernetes/container orchestration.
    Returns OK if the service is running.
    """
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
