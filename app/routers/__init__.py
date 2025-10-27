"""
Routers module for SYD Cyber backend.

This module contains FastAPI routers organized by domain.
"""

from app.routers.health import router as health_router
from app.routers.ateco import router as ateco_router

__all__ = ["health_router", "ateco_router"]
