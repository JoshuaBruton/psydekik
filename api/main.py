from datetime import datetime, timezone

from fastapi import FastAPI

from services.models import SystemStatus
from services.system_service import SystemService


app = FastAPI(
    title="Psydekik API",
    description="Local API and event system for Chappie and Psydekik.",
    version="0.1.0",
)

system_service = SystemService()


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    """Confirm that the Psydekik API is running."""

    return {
        "status": "healthy",
        "service": "psydekik-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get(
    "/api/system/status",
    response_model=SystemStatus,
    tags=["System"],
)
def get_system_status() -> SystemStatus:
    """Return current health information for the Raspberry Pi."""

    return system_service.get_status()
