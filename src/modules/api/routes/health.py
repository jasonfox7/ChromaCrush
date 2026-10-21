"""Health check endpoints.

Three endpoints for monitoring:

- ``GET /api/v1/health`` -- basic liveness (always 200).
- ``GET /api/v1/health/ready`` -- readiness: checks that database and
  Redis connections are available. Returns 200 if all healthy, 503 if any
  check fails.
- ``GET /api/v1/health/live`` -- simple liveness probe for container
  orchestrators.

No authentication is required for any health endpoint.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/v1/health", tags=["health"])


@router.get("")
async def health_check(request: Request) -> dict[str, Any]:
    """Basic health check.

    Returns:
        JSON with status "ok" and server timestamp.
    """
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": getattr(request.app.state, "app_version", "0.1.0"),
    }


@router.get("/ready")
async def readiness_check(request: Request) -> dict[str, Any]:
    """Readiness check verifying downstream dependencies.

    Checks database and Redis connectivity via the data context
    stored on app state. Returns 503 if any dependency is unavailable.

    Returns:
        JSON with per-dependency health status.
    """
    checks: dict[str, str] = {}

    # Database check
    data_ctx = getattr(request.app.state, "data_context", None)
    if data_ctx is not None:
        try:
            # If data_ctx exposes a health check, use it
            health_fn = getattr(data_ctx, "health_check", None)
            if health_fn is not None:
                await health_fn()
            checks["database"] = "ok"
        except Exception:
            checks["database"] = "unavailable"
    else:
        checks["database"] = "not_configured"

    # Redis check
    redis_ctx = getattr(request.app.state, "redis_context", None)
    if redis_ctx is not None:
        try:
            health_fn = getattr(redis_ctx, "health_check", None)
            if health_fn is not None:
                await health_fn()
            checks["redis"] = "ok"
        except Exception:
            checks["redis"] = "unavailable"
    else:
        checks["redis"] = "not_configured"

    all_ok = all(v == "ok" or v == "not_configured" for v in checks.values())

    from starlette.responses import JSONResponse

    status_code = 200 if all_ok else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if all_ok else "not_ready",
            "checks": checks,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@router.get("/live")
async def liveness_check() -> dict[str, str]:
    """Liveness probe for container orchestrators.

    Always returns 200 to indicate the process is alive and responsive.

    Returns:
        JSON with status "alive".
    """
    return {"status": "alive"}
