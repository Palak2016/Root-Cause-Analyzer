"""
FastAPI application entry point for the AI-Based Incident Root Cause Analyzer.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.utils.logging import setup_logging, get_logger
from app.ingestion.routes import router as ingestion_router
from app.api.health import router as health_router

# Setup logging
setup_logging(
    level=settings.log_level,
    format_type=settings.log_format,
    service_name="rca-analyzer",
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")

    # Initialize telemetry store
    from app.ingestion.repository import get_telemetry_store
    store = get_telemetry_store()
    logger.info("Telemetry store initialized")

    yield

    # Shutdown
    logger.info("Shutting down application")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="""
## AI-Based Incident Root Cause Analyzer

An intelligent system that automatically correlates logs, metrics, and traces
to identify the most probable root cause of production incidents.

### Features

- **Semantic Log Analysis**: Uses NLP embeddings to understand log messages
- **Intelligent Metric Detection**: Identifies behavioral changes in metrics
- **Trace-Based Dependencies**: Builds service dependency graphs
- **Causal Reasoning**: Separates root causes from symptoms
- **Explainable Output**: Generates human-readable explanations

### API Overview

- `/ingest/*` - Data ingestion endpoints for logs, metrics, and traces
- `/incidents/*` - Incident management and analysis
- `/services/*` - Service health and dependencies
- `/health/*` - Health check endpoints
        """,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    # Register routers
    app.include_router(health_router)
    app.include_router(ingestion_router)

    # Root endpoint
    @app.get("/", tags=["root"])
    async def root():
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "health": "/health",
        }

    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        workers=settings.workers if not settings.reload else 1,
    )
