"""
Seismic Zones Router - API endpoints for seismic zone lookups

This module provides modular API endpoints for Italian seismic zones,
migrated from main.py as part of the backend refactoring (Story 2.6).

Endpoints maintain backward compatibility with the old API structure
through dual endpoint support (old + new).
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
import logging

from app.services.seismic_service import SeismicService

# Setup logging
logger = logging.getLogger(__name__)

# Create router with prefix
router = APIRouter(
    prefix="/seismic",
    tags=["seismic"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)


# Dependency injection for SeismicService
def get_seismic_service() -> SeismicService:
    """Dependency injection for SeismicService instance"""
    return SeismicService()


@router.get("/zone")
async def get_seismic_zone(
    comune: str = Query(..., description="Nome del comune (case-insensitive)"),
    provincia: Optional[str] = Query(None, description="Sigla provincia (2 lettere) per disambiguare comuni omonimi"),
    seismic_service: SeismicService = Depends(get_seismic_service)
) -> JSONResponse:
    """
    Get seismic zone data for an Italian comune from JSON database.

    NEW ENDPOINT (Story 2.6) - replaces GET /seismic-zone/{comune}

    Uses multiple search strategies:
    1. Exact match
    2. Fuzzy match (with optional provincia filter)
    3. Provincia-based estimation

    Args:
        comune: Comune name (case-insensitive)
        provincia: Optional provincia code (e.g., 'RM', 'MI') for disambiguation
        seismic_service: Injected SeismicService instance

    Returns:
        JSONResponse with seismic zone data:
        {
            "comune": "ROMA",
            "provincia": "RM",
            "regione": "LAZIO",
            "zona_sismica": 3,
            "accelerazione_ag": 0.15,
            "risk_level": "Media",
            "description": "Zona 3 - Sismicità bassa...",
            "normativa": "OPCM 3519/2006",
            "source": "database_match" | "fuzzy_match" | "provincia_estimation",
            "confidence": 1.0
        }

    Examples:
        GET /seismic/zone?comune=Roma
        GET /seismic/zone?comune=Roma&provincia=RM
        GET /seismic/zone?comune=Milano
    """
    try:
        result = seismic_service.get_zone_by_comune(comune, provincia)
        return JSONResponse(result)

    except FileNotFoundError as e:
        logger.error(f"Seismic database not found: {e}")
        return JSONResponse({
            "error": "database_not_found",
            "message": "Database zone sismiche non disponibile"
        }, status_code=500)

    except ValueError as e:
        error_msg = str(e)

        # Parse error type
        if "comune_provincia_mismatch" in error_msg:
            return JSONResponse({
                "error": "comune_provincia_mismatch",
                "message": error_msg.split(": ", 1)[1] if ": " in error_msg else error_msg
            }, status_code=404)

        elif "no_match_in_provincia" in error_msg:
            # Extract suggestions if available
            suggestions = []
            try:
                # Parse suggestions from error message (basic parsing)
                import re
                match = re.search(r"Suggerimenti: (\[.*?\])", error_msg)
                if match:
                    import ast
                    suggestions = ast.literal_eval(match.group(1))
            except:
                pass

            return JSONResponse({
                "error": "no_match_in_provincia",
                "message": f"Nessun comune simile a '{comune}' trovato in provincia {provincia}",
                "suggestions": suggestions
            }, status_code=404)

        elif "comune_not_found" in error_msg:
            # Get suggestions using service
            suggestions = seismic_service.get_suggestions(comune, limit=5)

            return JSONResponse({
                "error": "comune_not_found",
                "message": f"Comune '{comune}' non trovato nel database",
                "suggestions": suggestions,
                "suggestion_text": "Verifica il nome del comune o fornisci la sigla provincia"
            }, status_code=404)

        else:
            logger.error(f"Unexpected ValueError: {e}")
            return JSONResponse({
                "error": "invalid_input",
                "message": str(e)
            }, status_code=400)

    except Exception as e:
        logger.error(f"Unexpected error in get_seismic_zone: {e}", exc_info=True)
        return JSONResponse({
            "error": "internal_error",
            "message": "Errore interno del server"
        }, status_code=500)


@router.get("/zone-from-db")
async def get_seismic_zone_from_db(
    comune: str = Query(..., description="Nome del comune"),
    provincia: Optional[str] = Query(None, description="Sigla provincia (opzionale)"),
    seismic_service: SeismicService = Depends(get_seismic_service)
) -> JSONResponse:
    """
    Get seismic zone data from PostgreSQL database.

    NEW ENDPOINT (Story 2.6) - replaces GET /db/seismic-zone/{comune}

    Args:
        comune: Comune name
        provincia: Optional provincia code for disambiguation
        seismic_service: Injected SeismicService instance

    Returns:
        JSONResponse with seismic zone data (same format as /zone)

    Examples:
        GET /seismic/zone-from-db?comune=Roma
        GET /seismic/zone-from-db?comune=Roma&provincia=RM
    """
    try:
        from database.config import get_db_session

        with get_db_session() as session:
            result = seismic_service.get_zone_from_db(
                comune=comune,
                provincia=provincia,
                db_session=session
            )
            return JSONResponse(result)

    except ValueError as e:
        error_msg = str(e)

        if "comune_not_found" in error_msg:
            return JSONResponse({
                "error": "comune_not_found",
                "message": f"Comune '{comune}' non trovato nel database zone sismiche",
                "source": "not_found"
            }, status_code=404)

        else:
            logger.error(f"ValueError in zone-from-db: {e}")
            return JSONResponse({
                "error": "invalid_input",
                "message": str(e)
            }, status_code=400)

    except Exception as e:
        logger.error(f"Database error in get_seismic_zone_from_db: {e}", exc_info=True)
        return JSONResponse({
            "error": "database_error",
            "message": "Errore interrogazione database"
        }, status_code=500)


@router.get("/suggestions")
async def get_comune_suggestions(
    comune: str = Query(..., description="Nome comune da cercare"),
    limit: int = Query(5, ge=1, le=20, description="Numero massimo suggerimenti"),
    seismic_service: SeismicService = Depends(get_seismic_service)
) -> JSONResponse:
    """
    Get similar comune name suggestions.

    NEW ENDPOINT (Story 2.6) - utility endpoint for autocomplete

    Args:
        comune: Partial or misspelled comune name
        limit: Maximum number of suggestions (1-20)
        seismic_service: Injected SeismicService instance

    Returns:
        JSONResponse with suggestions list:
        {
            "query": "rom",
            "suggestions": [
                {"comune": "ROMA", "provincia": "RM", "zona_sismica": 3},
                {"comune": "ROMANO", "provincia": "BG", "zona_sismica": 4}
            ],
            "count": 2
        }

    Examples:
        GET /seismic/suggestions?comune=rom
        GET /seismic/suggestions?comune=mila&limit=3
    """
    try:
        suggestions = seismic_service.get_suggestions(comune, limit)

        return JSONResponse({
            "query": comune,
            "suggestions": suggestions,
            "count": len(suggestions)
        })

    except Exception as e:
        logger.error(f"Error getting suggestions: {e}", exc_info=True)
        return JSONResponse({
            "error": "internal_error",
            "message": "Errore recupero suggerimenti",
            "suggestions": []
        }, status_code=500)
