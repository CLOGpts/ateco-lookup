"""
ATECO Router
============

Provides ATECO code lookup endpoints.
Extracted from main.py as part of modular refactoring (Story 2.2).

Endpoints:
- GET /ateco/lookup - Single code lookup
- GET /ateco/autocomplete - Autocomplete suggestions
- POST /ateco/batch - Batch lookup
- GET /db/ateco/lookup - Database-based lookup (legacy compatibility)
"""

import logging
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services.ateco_service import ATECOService

logger = logging.getLogger(__name__)

# Create router with prefix and tags
router = APIRouter(prefix="/ateco", tags=["ATECO"])

# Initialize ATECO service (dependency injection would be better, but keeping it simple for now)
# In production, this should be injected via Depends()
DATASET_PATH = Path("tabella_ATECO.xlsx")
ateco_service = None  # Will be initialized on first request


def get_ateco_service() -> ATECOService:
    """
    Get or create ATECO service instance.

    Returns:
        ATECOService: Initialized service
    """
    global ateco_service
    if ateco_service is None:
        ateco_service = ATECOService(dataset_path=DATASET_PATH)
        logger.info("ATECO service initialized")
    return ateco_service


# ----------------------- Pydantic Models -----------------------


class BatchRequest(BaseModel):
    """Request model for batch ATECO lookup."""

    codes: List[str]
    prefer: Optional[str] = None
    prefix: bool = False


class ATECOLookupResponse(BaseModel):
    """Response model for ATECO lookup."""

    found: int
    items: List[dict]


class ATECOSuggestion(BaseModel):
    """Model for autocomplete suggestion."""

    code: str
    title: str
    version: str


class AutocompleteResponse(BaseModel):
    """Response model for autocomplete."""

    partial: str
    suggestions: List[ATECOSuggestion]
    count: int


# ----------------------- Endpoints -----------------------


@router.get("/lookup")
def lookup_ateco(
    code: str = Query(..., description="Codice ATECO (e.g., 62.01)", min_length=2),
    prefer: Optional[str] = Query(
        None, description="Priorità versione: 2022 | 2025 | 2025-camerale"
    ),
    prefix: bool = Query(False, description="Ricerca per prefisso"),
    limit: int = Query(50, description="Limite risultati (max 50)", le=50),
):
    """
    Single ATECO code lookup with optional 2022/2025 preference.

    Args:
        code: ATECO code to search (min 2 characters)
        prefer: Preferred ATECO version (2022, 2025, 2025-camerale)
        prefix: Enable prefix matching
        limit: Maximum number of results

    Returns:
        JSON with found count and items list

    Examples:
        GET /ateco/lookup?code=62.01
        GET /ateco/lookup?code=62&prefix=true&limit=10
        GET /ateco/lookup?code=62.01&prefer=2025
    """
    logger.info(
        f"ATECO lookup: code={code}, prefer={prefer}, prefix={prefix}, limit={limit}"
    )

    # Validation
    if not code or len(code) < 2:
        logger.warning(f"Invalid code provided: {code}")
        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_CODE",
                "message": "Codice troppo corto (minimo 2 caratteri)",
            },
        )

    # Validate prefer parameter
    if prefer and prefer not in ["2022", "2025", "2025-camerale"]:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_PREFER",
                "message": "prefer deve essere: 2022, 2025, o 2025-camerale",
            },
        )

    try:
        service = get_ateco_service()
        result = service.search_smart(code, prefer=prefer, prefix=prefix)

        if result.empty:
            logger.info(f"No results found for code: {code}")
            # Suggest alternatives
            suggestions = service.find_similar_codes(code, limit=5)
            return JSONResponse(
                {
                    "found": 0,
                    "items": [],
                    "suggestions": suggestions,
                    "message": f"Nessun risultato per '{code}'. Prova con uno dei suggerimenti.",
                }
            )

        # Limit results if prefix search
        if prefix:
            result = result.head(limit)

        # Convert to JSON
        items = [service.enrich(service.flatten(row)) for _, row in result.iterrows()]
        logger.info(f"Found {len(items)} results for code: {code}")

        return JSONResponse({"found": len(items), "items": items})

    except FileNotFoundError as e:
        logger.error(f"Dataset file not found: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "DATASET_NOT_FOUND",
                "message": "Dataset ATECO non disponibile",
            },
        )
    except Exception as e:
        logger.error(f"Error in lookup_ateco: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "INTERNAL_ERROR", "message": "Errore interno del server"},
        )


@router.get("/autocomplete")
def autocomplete_ateco(
    partial: str = Query(..., min_length=2, description="Codice parziale (e.g., 62)"),
    limit: int = Query(5, le=20, description="Numero suggerimenti (max 20)"),
):
    """
    Autocomplete suggestions for partial ATECO code.

    Returns suggestions from both ATECO 2022 and 2025 versions.

    Args:
        partial: Partial ATECO code (min 2 characters)
        limit: Maximum number of suggestions (max 20)

    Returns:
        JSON with suggestions list

    Examples:
        GET /ateco/autocomplete?partial=62
        GET /ateco/autocomplete?partial=62.0&limit=10
    """
    logger.info(f"ATECO autocomplete: partial={partial}, limit={limit}")

    try:
        service = get_ateco_service()
        df = service.load_dataset()

        from app.services.ateco_service import normalize_code

        partial_norm = normalize_code(partial)
        suggestions = []
        seen = set()

        # Search in ATECO 2022 codes first
        for _, row in df.iterrows():
            code = normalize_code(row.get("CODICE_ATECO_2022", ""))
            if code and code.startswith(partial_norm) and code not in seen:
                seen.add(code)
                suggestions.append(
                    {
                        "code": row.get("CODICE_ATECO_2022", ""),
                        "title": row.get("TITOLO_ATECO_2022", ""),
                        "version": "2022",
                    }
                )
                if len(suggestions) >= limit:
                    break

        # If not enough results, search in ATECO 2025 codes
        if len(suggestions) < limit:
            for _, row in df.iterrows():
                code = normalize_code(row.get("CODICE_ATECO_2025_RAPPRESENTATIVO", ""))
                if code and code.startswith(partial_norm) and code not in seen:
                    seen.add(code)
                    suggestions.append(
                        {
                            "code": row.get("CODICE_ATECO_2025_RAPPRESENTATIVO", ""),
                            "title": row.get("TITOLO_ATECO_2025_RAPPRESENTATIVO", ""),
                            "version": "2025",
                        }
                    )
                    if len(suggestions) >= limit:
                        break

        logger.info(f"Autocomplete found {len(suggestions)} suggestions")

        return JSONResponse(
            {
                "partial": partial,
                "suggestions": suggestions[:limit],
                "count": len(suggestions[:limit]),
            }
        )

    except Exception as e:
        logger.error(f"Error in autocomplete_ateco: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "INTERNAL_ERROR", "message": "Errore interno del server"},
        )


@router.post("/batch")
def batch_lookup_ateco(request: BatchRequest):
    """
    Batch lookup for multiple ATECO codes.

    Args:
        request: BatchRequest with codes list

    Returns:
        JSON with total_codes and results list

    Examples:
        POST /ateco/batch
        {
            "codes": ["62.01", "62.02", "62.09"],
            "prefer": "2022",
            "prefix": false
        }
    """
    logger.info(f"ATECO batch lookup: {len(request.codes)} codes")

    # Validation
    if len(request.codes) > 50:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "TOO_MANY_CODES",
                "message": "Massimo 50 codici per richiesta batch",
            },
        )

    if not request.codes:
        raise HTTPException(
            status_code=400,
            detail={"error": "EMPTY_CODES", "message": "Lista codici vuota"},
        )

    try:
        service = get_ateco_service()
        results = []

        for code in request.codes:
            result = service.search_smart(
                code, prefer=request.prefer, prefix=request.prefix
            )

            if result.empty:
                results.append({"code": code, "found": 0, "items": []})
            else:
                # Only return first match for batch (not all prefix matches)
                items = [
                    service.enrich(service.flatten(row))
                    for _, row in result.head(1).iterrows()
                ]
                results.append({"code": code, "found": len(items), "items": items})

        logger.info(f"Batch lookup completed: {len(results)} results")

        return JSONResponse({"total_codes": len(request.codes), "results": results})

    except Exception as e:
        logger.error(f"Error in batch_lookup_ateco: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "INTERNAL_ERROR", "message": "Errore interno del server"},
        )


@router.get("/db/lookup")
def db_lookup_ateco(
    code: str = Query(..., description="Codice ATECO", min_length=2),
    prefer: Optional[str] = Query(None, description="Priorità versione"),
    prefix: bool = Query(False, description="Ricerca per prefisso"),
):
    """
    Database-based ATECO lookup (legacy compatibility).

    Accessible at /ateco/db/lookup for backward compatibility.

    Args:
        code: ATECO code to search
        prefer: Preferred ATECO version
        prefix: Enable prefix matching

    Returns:
        Same as /ateco/lookup
    """
    logger.info(f"DB ATECO lookup (legacy): code={code}")
    # Delegate to main lookup endpoint
    return lookup_ateco(code=code, prefer=prefer, prefix=prefix, limit=50)
