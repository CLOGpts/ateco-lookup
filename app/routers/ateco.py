"""
ATECO Router - API endpoints for ATECO code lookup and search

This module provides modular API endpoints for ATECO code lookup,
extracted from main.py as part of the backend refactoring.

Endpoints:
- GET /ateco/lookup - Search ATECO codes with smart matching
"""

from typing import Dict, Any, Optional, Callable
from fastapi import APIRouter, Query, HTTPException
import logging
import pandas as pd

# Setup logging
logger = logging.getLogger(__name__)

# Create router with prefix
router = APIRouter(
    prefix="/ateco",
    tags=["ateco"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)

# Global dependencies (will be injected from main.py)
_ateco_df: Optional[pd.DataFrame] = None
_search_smart_fn: Optional[Callable] = None
_find_similar_fn: Optional[Callable] = None
_enrich_fn: Optional[Callable] = None
_flatten_fn: Optional[Callable] = None


def set_dependencies(
    ateco_df: pd.DataFrame,
    search_smart_fn: Callable,
    find_similar_fn: Callable,
    enrich_fn: Callable,
    flatten_fn: Callable
):
    """
    Set global dependencies for ATECO router.

    Called from main.py to inject DataFrame and utility functions.

    Args:
        ateco_df: DataFrame with ATECO codes
        search_smart_fn: Function for smart ATECO search
        find_similar_fn: Function to find similar codes
        enrich_fn: Function to enrich with normative/certificazioni
        flatten_fn: Function to flatten DataFrame row
    """
    global _ateco_df, _search_smart_fn, _find_similar_fn, _enrich_fn, _flatten_fn
    _ateco_df = ateco_df
    _search_smart_fn = search_smart_fn
    _find_similar_fn = find_similar_fn
    _enrich_fn = enrich_fn
    _flatten_fn = flatten_fn
    logger.info("ATECO router dependencies set successfully")


@router.get("/lookup")
def lookup_ateco(
    code: str = Query(..., description="Codice ATECO da cercare"),
    prefer: Optional[str] = Query(None, description="Preferenza versione (2025, 2025-camerale, 2022)")
) -> Dict[str, Any]:
    """
    Lookup ATECO code with smart matching.

    Searches for an ATECO code in the database with intelligent matching
    across 2022 and 2025 versions. Returns enriched data with normative
    and certificazioni when available.

    Args:
        code: ATECO code to search (e.g., "64.99.1")
        prefer: Version preference (2025, 2025-camerale, or 2022)

    Returns:
        JSONResponse with:
        - found: Number of results found
        - items: List of matching ATECO codes (enriched)
        - suggestions: Similar codes if no exact match found

    Example:
        GET /ateco/lookup?code=64.99.1&prefer=2025
        Response: {
            "found": 1,
            "items": [{
                "CODICE_ATECO_2022": "64.99.1",
                "TITOLO_ATECO_2022": "...",
                "CODICE_ATECO_2025_RAPPRESENTATIVO": "...",
                "settore": "finance",
                "normative": [...],
                "certificazioni": [...]
            }],
            "suggestions": []
        }
    """
    if not _ateco_df or not _search_smart_fn or not _enrich_fn:
        raise HTTPException(
            status_code=500,
            detail="ATECO router not properly initialized"
        )

    try:
        logger.info(f"🔍 ATECO lookup: code={code}, prefer={prefer}")

        # Search using smart matching
        result_df = _search_smart_fn(_ateco_df, code, prefer=prefer, prefix=False)

        if result_df.empty:
            # No exact match - find similar codes
            logger.info(f"No exact match for {code}, finding suggestions...")
            suggestions = _find_similar_fn(_ateco_df, code, limit=5)

            return {
                "found": 0,
                "items": [],
                "suggestions": suggestions,
                "message": f"Codice {code} non trovato. Vedi suggerimenti."
            }

        # Flatten and enrich results
        items = []
        for _, row in result_df.iterrows():
            item = _flatten_fn(row)
            enriched = _enrich_fn(item)
            items.append(enriched)

        logger.info(f"✅ Found {len(items)} results for code {code}")

        return {
            "found": len(items),
            "items": items,
            "suggestions": []
        }

    except Exception as e:
        logger.error(f"❌ Error in ATECO lookup: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error during ATECO lookup: {str(e)}"
        )
