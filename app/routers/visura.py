"""
Visura Router - API endpoints for Visura PDF extraction functionality

This module provides the new modular API endpoints for Visura extraction,
migrated from main.py as part of the backend refactoring (Story 2.4).

Endpoints maintain backward compatibility with the old API structure.
"""

from typing import Dict, Any, Optional, Callable
from fastapi import APIRouter, HTTPException, Depends, File, UploadFile
from fastapi.responses import JSONResponse
from pathlib import Path
import logging
import pandas as pd

from app.services.visura_service import VisuraService

# Setup logging
logger = logging.getLogger(__name__)

# Create router with prefix
router = APIRouter(
    prefix="/visura",
    tags=["visura"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)

# Global dependencies (will be injected from main.py)
_ateco_df: Optional[pd.DataFrame] = None
_search_smart_fn: Optional[Callable] = None
_normalize_code_fn: Optional[Callable] = None


def set_dependencies(
    ateco_df: pd.DataFrame,
    search_smart_fn: Callable,
    normalize_code_fn: Callable
):
    """
    Set global dependencies for Visura router.

    Called from main.py to inject DataFrame and utility functions.

    Args:
        ateco_df: DataFrame with ATECO codes
        search_smart_fn: Function to search ATECO codes
        normalize_code_fn: Function to normalize ATECO codes
    """
    global _ateco_df, _search_smart_fn, _normalize_code_fn
    _ateco_df = ateco_df
    _search_smart_fn = search_smart_fn
    _normalize_code_fn = normalize_code_fn
    logger.info("Visura router dependencies set successfully")


# Dependency injection for VisuraService
def get_visura_service() -> VisuraService:
    """Dependency injection for VisuraService instance"""
    return VisuraService(
        ateco_df=_ateco_df,
        search_smart_fn=_search_smart_fn,
        normalize_code_fn=_normalize_code_fn
    )


@router.get("/test")
def test_visura(
    visura_service: VisuraService = Depends(get_visura_service)
) -> JSONResponse:
    """
    Test endpoint to verify API is working.

    Returns test visura data with all fields populated.

    Args:
        visura_service: Injected VisuraService instance

    Returns:
        JSONResponse with test data

    Example:
        GET /visura/test
        Response: {
            "success": true,
            "message": "API working! VisuraExtractorPower available: True",
            "data": {
                "denominazione": "TEST CELERYA SRL",
                "partita_iva": "12345678901",
                "pec": "test@pec.it",
                "codici_ateco": [...],
                "sede_legale": {...},
                "confidence": 0.99
            }
        }
    """
    try:
        result = visura_service.get_test_data()
        return JSONResponse(result)

    except Exception as e:
        logger.error(f"Error in test_visura: {str(e)}", exc_info=True)
        return JSONResponse({
            "error": "Internal server error",
            "message": str(e)
        }, status_code=500)


@router.post("/extract")
async def extract_visura(
    file: UploadFile = File(...),
    visura_service: VisuraService = Depends(get_visura_service)
) -> JSONResponse:
    """
    Extract data from Visura PDF.

    Extracts ONLY 3 STRICT fields from visura PDF:
    - P.IVA (11 digits)
    - ATECO code (with 2022→2025 conversion)
    - Oggetto Sociale (business description)

    Also extracts optional fields:
    - Sede Legale (comune + provincia)
    - Denominazione (company name)
    - Forma Giuridica (legal form)

    Args:
        file: Uploaded PDF file
        visura_service: Injected VisuraService instance

    Returns:
        JSONResponse with extraction result and confidence score

    Example:
        POST /visura/extract
        Body: multipart/form-data with PDF file
        Response: {
            "success": true,
            "data": {
                "partita_iva": "12345678901",
                "codice_ateco": "64.99.1",
                "oggetto_sociale": "Produzione software...",
                "codici_ateco": [{
                    "codice": "64.99.1",
                    "descrizione": "",
                    "principale": true
                }],
                "sede_legale": {
                    "comune": "Torino",
                    "provincia": "TO"
                },
                "denominazione": "CELERYA SRL",
                "forma_giuridica": "SOCIETA' A RESPONSABILITA' LIMITATA",
                "confidence": {
                    "score": 100,
                    "details": {
                        "partita_iva": "valid",
                        "ateco": "valid",
                        "oggetto_sociale": "valid",
                        "sede_legale": "valid",
                        "denominazione": "valid",
                        "forma_giuridica": "valid"
                    }
                }
            },
            "method": "backend"
        }
    """
    try:
        # Read file content
        content = await file.read()

        if not content:
            logger.warning("Empty file received")
            return JSONResponse({
                'success': True,
                'data': {
                    'partita_iva': None,
                    'codice_ateco': None,
                    'oggetto_sociale': None,
                    'codici_ateco': [],
                    'confidence': {
                        'score': 0,
                        'details': {}
                    }
                },
                'method': 'backend'
            })

        # Extract data using service
        result = visura_service.extract_from_pdf(content, file.filename)
        return JSONResponse(result)

    except Exception as e:
        logger.error(f"Error in extract_visura: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": "Internal server error",
            "message": str(e),
            'data': {
                'partita_iva': None,
                'codice_ateco': None,
                'oggetto_sociale': None,
                'codici_ateco': [],
                'confidence': {
                    'score': 0,
                    'details': {}
                }
            },
            'method': 'backend'
        }, status_code=500)
