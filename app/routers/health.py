"""
Health Check Router
===================

Provides health check endpoints for monitoring system status.
Extracted from main.py as part of modular refactoring (Story 2.1).
"""

from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)

# Create router with prefix and tags
router = APIRouter(
    prefix="/health",
    tags=["Health"]
)


@router.get("")
def health_check():
    """
    Basic health check endpoint.

    Returns:
        dict: Status, version, and cache info
    """
    logger.info("Health check requested")
    return {
        "status": "ok",
        "version": "2.0",
        "cache_enabled": True
    }


@router.get("/database")
def health_database():
    """
    Database health check endpoint.

    Tests PostgreSQL connection and returns pool status.

    Returns:
        dict: Database connection status and pool info
    """
    logger.info("Database health check requested")
    try:
        from database.config import check_database_connection, get_pool_status

        # Test connection
        connection_ok = check_database_connection()

        if connection_ok:
            # Get pool status
            pool_status = get_pool_status()
            return {
                "status": "ok",
                "database": "postgresql",
                "pool": pool_status
            }
        else:
            return {
                "status": "error",
                "database": "postgresql",
                "message": "Database connection failed"
            }

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "error",
            "database": "postgresql",
            "message": str(e)
        }
