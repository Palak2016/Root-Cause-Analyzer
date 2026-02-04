"""
API module for the Root Cause Analyzer.
Contains FastAPI routers for external endpoints.
"""

from app.api.health import router as health_router

__all__ = ["health_router"]
