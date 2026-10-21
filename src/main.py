"""FastAPI application entry point.

Uses the ``create_app`` factory from the API module to build a fully-wired
FastAPI application with all services, middleware, and routers.

Run with:
    uvicorn src.main:app --reload
"""

from src.modules.api.factory import create_app

app = create_app()
