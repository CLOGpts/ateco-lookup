"""
DB Admin Router - API endpoints for database administration functionality

This module provides the new modular API endpoints for database admin,
migrated from main.py as part of the backend refactoring (Story 2.5).

Endpoints maintain backward compatibility with the old API structure.
"""

from typing import Dict, Any, Optional, Callable
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pathlib import Path
import logging
import pandas as pd

from app.services.db_admin_service import DBAdminService

# Setup logging
logger = logging.getLogger(__name__)

# Create router with prefix
router = APIRouter(
    prefix="/db-admin",
    tags=["db-admin"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)

# Global dependencies (will be injected from main.py)
_ateco_df: Optional[pd.DataFrame] = None


def set_dependencies(ateco_df: pd.DataFrame):
    """
    Set global dependencies for DB Admin router.

    Called from main.py to inject DataFrame.

    Args:
        ateco_df: DataFrame with ATECO codes
    """
    global _ateco_df
    _ateco_df = ateco_df
    logger.info("DB Admin router dependencies set successfully")


# Dependency injection for DBAdminService
def get_db_admin_service() -> DBAdminService:
    """Dependency injection for DBAdminService instance"""
    return DBAdminService()


@router.get("/setup-database")
async def setup_database(
    db_admin_service: DBAdminService = Depends(get_db_admin_service)
) -> JSONResponse:
    """
    Execute database setup for Syd Agent tracking tables.

    IMPORTANT: Use this endpoint ONLY to initialize database.

    Returns:
        JSONResponse with setup steps and success status

    Example:
        GET /db-admin/setup-database
        Response: {
            "success": true,
            "message": "🎉 Setup completato con successo!",
            "tables_created": ["user_sessions", "session_events"],
            "steps": [...]
        }
    """
    try:
        result = db_admin_service.setup_database()
        return JSONResponse(result)

    except ConnectionError as e:
        logger.error(f"Connection error in setup-database: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": "connection_error",
            "message": "Impossibile connettersi al database",
            "details": str(e)
        }, status_code=500)

    except Exception as e:
        logger.error(f"Error in setup-database endpoint: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": "internal_error",
            "message": "Errore durante setup database",
            "details": str(e)
        }, status_code=500)


@router.get("/check-tables")
async def check_tables_status(
    db_admin_service: DBAdminService = Depends(get_db_admin_service)
) -> JSONResponse:
    """
    Verify which tables exist in the database.

    READ ONLY - does not modify anything.

    Returns:
        JSONResponse with table status information

    Example:
        GET /db-admin/check-tables
        Response: {
            "status": "ok",
            "total_tables": 8,
            "tables": {
                "risk_events": {
                    "exists": true,
                    "row_count": 191,
                    "description": "191 eventi rischio"
                },
                ...
            },
            "missing_tables": []
        }
    """
    try:
        result = db_admin_service.check_tables_status()
        return JSONResponse(result)

    except Exception as e:
        logger.error(f"Error in check-tables endpoint: {str(e)}", exc_info=True)
        return JSONResponse({
            "status": "error",
            "message": "Errore durante verifica tabelle",
            "details": str(e)
        }, status_code=500)


@router.post("/create-tables")
async def create_missing_tables(
    db_admin_service: DBAdminService = Depends(get_db_admin_service)
) -> JSONResponse:
    """
    Create missing tables in PostgreSQL database.

    SECURITY:
    - Does not delete existing tables
    - Does not modify existing data
    - Uses SQLAlchemy create_all (idempotent)

    Tables created:
    1. users (consultants)
    2. companies (client companies)
    3. assessments (risk assessments)
    4. risk_events (191 events)
    5. ateco_codes (25K codes)
    6. seismic_zones (8K municipalities)

    Returns:
        JSONResponse with creation steps and results

    Example:
        POST /db-admin/create-tables
        Response: {
            "success": true,
            "message": "✅ Tabelle create con successo! (6 nuove)",
            "summary": {
                "before": 2,
                "after": 8,
                "created": 6
            },
            "steps": [...]
        }
    """
    try:
        result = db_admin_service.create_missing_tables()
        return JSONResponse(result)

    except Exception as e:
        logger.error(f"Error in create-tables endpoint: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": "internal_error",
            "message": "Errore durante creazione tabelle",
            "details": str(e)
        }, status_code=500)


@router.post("/migrate-risk-events")
async def migrate_risk_events(
    db_admin_service: DBAdminService = Depends(get_db_admin_service)
) -> JSONResponse:
    """
    Migrate 191 risk events from MAPPATURE_EXCEL_PERFETTE.json → PostgreSQL.

    SECURITY:
    - Skip events that already exist (no duplicates)
    - Atomic transaction (rollback on error)
    - Detailed step-by-step report

    Returns:
        JSONResponse with migration results

    Example:
        POST /db-admin/migrate-risk-events
        Response: {
            "success": true,
            "message": "✅ Migrazione completata! (191 inseriti, 0 saltati)",
            "steps": [...]
        }
    """
    try:
        result = db_admin_service.migrate_risk_events()
        return JSONResponse(result)

    except FileNotFoundError as e:
        logger.error(f"File not found in migrate-risk-events: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": "file_not_found",
            "message": "File MAPPATURE_EXCEL_PERFETTE.json non trovato",
            "details": str(e)
        }, status_code=404)

    except Exception as e:
        logger.error(f"Error in migrate-risk-events endpoint: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": "internal_error",
            "message": "Errore durante migrazione eventi rischio",
            "details": str(e)
        }, status_code=500)


@router.post("/migrate-ateco")
async def migrate_ateco_codes(
    db_admin_service: DBAdminService = Depends(get_db_admin_service)
) -> JSONResponse:
    """
    Migrate ATECO codes from DataFrame → PostgreSQL.

    Returns:
        JSONResponse with migration results

    Example:
        POST /db-admin/migrate-ateco
        Response: {
            "success": true,
            "message": "✅ Migrazione ATECO completata! (25123 inseriti, 0 saltati)",
            "steps": [...]
        }
    """
    try:
        if _ateco_df is None:
            raise ValueError("ATECO DataFrame not available")

        result = db_admin_service.migrate_ateco_codes(_ateco_df)
        return JSONResponse(result)

    except ValueError as e:
        logger.error(f"DataFrame not available in migrate-ateco: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": "dataframe_not_available",
            "message": "DataFrame ATECO non disponibile",
            "details": str(e)
        }, status_code=500)

    except Exception as e:
        logger.error(f"Error in migrate-ateco endpoint: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": "internal_error",
            "message": "Errore durante migrazione codici ATECO",
            "details": str(e)
        }, status_code=500)


@router.post("/migrate-seismic-zones")
async def migrate_seismic_zones(
    db_admin_service: DBAdminService = Depends(get_db_admin_service)
) -> JSONResponse:
    """
    Migrate seismic zones from JSON → PostgreSQL.

    Returns:
        JSONResponse with migration results

    Example:
        POST /db-admin/migrate-seismic-zones
        Response: {
            "success": true,
            "message": "✅ Migrazione zone sismiche completata! (8102 inseriti, 0 saltati)",
            "steps": [...]
        }
    """
    try:
        result = db_admin_service.migrate_seismic_zones()
        return JSONResponse(result)

    except FileNotFoundError as e:
        logger.error(f"File not found in migrate-seismic-zones: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": "file_not_found",
            "message": "File zone_sismiche_comuni.json non trovato",
            "details": str(e)
        }, status_code=404)

    except Exception as e:
        logger.error(f"Error in migrate-seismic-zones endpoint: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": "internal_error",
            "message": "Errore durante migrazione zone sismiche",
            "details": str(e)
        }, status_code=500)


@router.post("/create-feedback-table")
async def create_feedback_table(
    db_admin_service: DBAdminService = Depends(get_db_admin_service)
) -> JSONResponse:
    """
    Create user_feedback table in PostgreSQL database.

    SECURITY:
    - This endpoint is protected (admin call only once)
    - Uses IF NOT EXISTS to avoid errors if already exists

    CALL ONCE ONLY:
    POST https://celerya-cyber-ateco-production.up.railway.app/db-admin/create-feedback-table

    Returns:
        JSONResponse with creation results

    Example:
        POST /db-admin/create-feedback-table
        Response: {
            "success": true,
            "message": "Tabella user_feedback creata con successo",
            "steps": ["✅ Tabella user_feedback creata", ...]
        }
    """
    try:
        logger.info("🚀 ADMIN: Richiesta creazione tabella user_feedback")
        result = db_admin_service.create_feedback_table()
        return JSONResponse(result)

    except Exception as e:
        logger.error(f"❌ Errore creazione tabella user_feedback: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": "table_creation_failed",
            "message": "Errore durante creazione tabella",
            "details": str(e)
        }, status_code=500)
