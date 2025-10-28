"""
Routers package - API endpoint modules

This package contains FastAPI router modules that define API endpoints.
Each router encapsulates endpoints for a specific domain area.
"""

from app.routers import risk

__all__ = ["risk"]
