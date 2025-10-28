"""
Risk Assessment Router - API endpoints for risk assessment functionality

This module provides the new modular API endpoints for risk assessment,
migrated from main.py as part of the backend refactoring (Story 2.3).

Endpoints maintain backward compatibility with the old API structure.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pathlib import Path
import logging

from app.services.risk_service import RiskService

# Setup logging
logger = logging.getLogger(__name__)

# Create router with prefix
router = APIRouter(
    prefix="/risk",
    tags=["risk"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)

# Dependency injection for RiskService
def get_risk_service() -> RiskService:
    """Dependency injection for RiskService instance"""
    return RiskService()


@router.get("/events/{category}")
def get_events_for_category(
    category: str,
    risk_service: RiskService = Depends(get_risk_service)
) -> JSONResponse:
    """
    Get risk events for a specific category

    Args:
        category: Category name (e.g., 'operational', 'cyber', 'Damage_Danni', etc.)
        risk_service: Injected RiskService instance

    Returns:
        JSONResponse with events list including code, name, severity

    Example:
        GET /risk/events/operational
        Response: {
            "category": "Execution_delivery_Problemi_di_produzione_o_consegna",
            "original_request": "operational",
            "events": [
                {"code": "101", "name": "Evento X", "severity": "medium"},
                ...
            ],
            "total": 15
        }
    """
    try:
        result = risk_service.get_events_for_category(category)

        # Check if error occurred in service
        if "error" in result:
            return JSONResponse(result, status_code=404)

        return JSONResponse(result)

    except Exception as e:
        logger.error(f"Error in get_events_for_category: {str(e)}", exc_info=True)
        return JSONResponse({
            "error": "Internal server error",
            "message": str(e)
        }, status_code=500)


@router.get("/description/{event_code}")
def get_event_description(
    event_code: str,
    risk_service: RiskService = Depends(get_risk_service)
) -> JSONResponse:
    """
    Get detailed description for a specific risk event

    Args:
        event_code: Event code (e.g., '101', '201', etc.)
        risk_service: Injected RiskService instance

    Returns:
        JSONResponse with event details including:
        - code, name, description
        - category, impact, probability
        - controls, source

    Example:
        GET /risk/description/101
        Response: {
            "code": "101",
            "name": "Nome Evento",
            "description": "Descrizione dettagliata...",
            "category": "Damage_Danni",
            "impact": "high",
            "probability": "medium",
            "controls": ["Controllo 1", "Controllo 2"],
            "source": "Excel Risk Mapping",
            "has_vlookup": true
        }
    """
    try:
        result = risk_service.get_event_description(event_code)

        # Check if error occurred in service
        if "error" in result:
            status_code = 400 if "Invalid event code" in result.get("error", "") else 404
            return JSONResponse(result, status_code=status_code)

        return JSONResponse(result)

    except Exception as e:
        logger.error(f"Error in get_event_description: {str(e)}", exc_info=True)
        return JSONResponse({
            "error": "Internal server error",
            "message": str(e)
        }, status_code=500)


@router.get("/assessment-fields")
def get_risk_assessment_fields() -> Dict[str, Any]:
    """
    Get the structure of risk assessment form fields

    Returns:
        Dictionary with field definitions for the risk assessment form.
        Includes 7 fields: financial impact, economic loss, image impact,
        regulatory impact, criminal impact, non-economic loss, control level

    Example:
        GET /risk/assessment-fields
        Response: {
            "fields": [
                {
                    "id": "impatto_finanziario",
                    "column": "H",
                    "question": "Qual è l'impatto finanziario stimato?",
                    "type": "select",
                    "options": ["N/A", "0 - 1K€", ...],
                    "required": true
                },
                ...
            ]
        }
    """
    return {
        "fields": [
            {
                "id": "impatto_finanziario",
                "column": "H",
                "question": "Qual è l'impatto finanziario stimato?",
                "type": "select",
                "options": [
                    "N/A",
                    "0 - 1K€",
                    "1 - 10K€",
                    "10 - 50K€",
                    "50 - 100K€",
                    "100 - 500K€",
                    "500K€ - 1M€",
                    "1 - 3M€",
                    "3 - 5M€"
                ],
                "required": True
            },
            {
                "id": "perdita_economica",
                "column": "I",
                "question": "Qual è il livello di perdita economica attesa?",
                "type": "select_color",
                "options": [
                    {"value": "G", "label": "Bassa/Nulla", "color": "green", "emoji": "🟢"},
                    {"value": "Y", "label": "Media", "color": "yellow", "emoji": "🟡"},
                    {"value": "O", "label": "Importante", "color": "orange", "emoji": "🟠"},
                    {"value": "R", "label": "Grave", "color": "red", "emoji": "🔴"}
                ],
                "required": True
            },
            {
                "id": "impatto_immagine",
                "column": "J",
                "question": "L'evento ha impatto sull'immagine aziendale?",
                "type": "boolean",
                "options": ["Si", "No"],
                "required": True
            },
            {
                "id": "impatto_regolamentare",
                "column": "L",
                "question": "Ci sono possibili conseguenze regolamentari o legali civili?",
                "type": "boolean",
                "options": ["Si", "No"],
                "description": "Multe, sanzioni amministrative, cause civili",
                "required": True
            },
            {
                "id": "impatto_criminale",
                "column": "M",
                "question": "Ci sono possibili conseguenze penali?",
                "type": "boolean",
                "options": ["Si", "No"],
                "description": "Denunce penali, procedimenti criminali",
                "required": True
            },
            {
                "id": "perdita_non_economica",
                "column": "V",
                "question": "Qual è il livello di perdita non economica non attesa ma accadibile?",
                "type": "select_color",
                "options": [
                    {"value": "G", "label": "Bassa/Nulla - Impatto minimo o trascurabile", "color": "green", "emoji": "🟢"},
                    {"value": "Y", "label": "Media - Impatto moderato gestibile", "color": "yellow", "emoji": "🟡"},
                    {"value": "O", "label": "Importante - Impatto significativo che richiede attenzione", "color": "orange", "emoji": "🟠"},
                    {"value": "R", "label": "Grave - Impatto critico che richiede azione immediata", "color": "red", "emoji": "🔴"}
                ],
                "required": False
            },
            {
                "id": "controllo",
                "column": "W",
                "question": "Qual è il livello di controllo?",
                "type": "select",
                "options": [
                    {"value": "++", "label": "++ Adeguato"},
                    {"value": "+", "label": "+ Sostanzialmente adeguato"},
                    {"value": "-", "label": "- Parzialmente Adeguato"},
                    {"value": "--", "label": "-- Non adeguato / assente"}
                ],
                "required": False,
                "triggers": "descrizione_controllo"
            },
            {
                "id": "descrizione_controllo",
                "column": "X",
                "question": "Descrizione del controllo",
                "type": "readonly",
                "autoPopulated": True,
                "vlookupSource": "W",
                "vlookupMap": {
                    "++": {
                        "titolo": "Adeguato",
                        "descrizione": "Il sistema di controllo interno è efficace ed adeguato (controlli 1 e 2 sono attivi e consolidati)"
                    },
                    "+": {
                        "titolo": "Sostanzialmente adeguato",
                        "descrizione": "Alcune correzioni potrebbero rendere soddisfacente il sistema di controllo interno (controlli 1 e 2 presenti ma parzialmente strutturati)"
                    },
                    "-": {
                        "titolo": "Parzialmente Adeguato",
                        "descrizione": "Il sistema di controllo interno deve essere migliorato e il processo dovrebbe essere più strettamente controllato (controlli 1 e 2 NON formalizzati)"
                    },
                    "--": {
                        "titolo": "Non adeguato / assente",
                        "descrizione": "Il sistema di controllo interno dei processi deve essere riorganizzato immediatamente (livelli di controllo 1 e 2 NON attivi)"
                    }
                }
            }
        ]
    }


@router.post("/save-assessment")
def save_risk_assessment(
    data: dict,
    risk_service: RiskService = Depends(get_risk_service)
) -> JSONResponse:
    """
    Save risk assessment and calculate risk score

    Args:
        data: Risk assessment data including:
            - financial_impact: Financial impact level
            - image_impact: Boolean for image impact
            - regulatory_impact: Boolean for regulatory consequences
            - criminal_impact: Boolean for criminal consequences
            - control_level: Control effectiveness level

    Returns:
        JSONResponse with calculated risk score and analysis

    Example:
        POST /risk/save-assessment
        Body: {
            "financial_impact": "10 - 50K€",
            "image_impact": true,
            "regulatory_impact": false,
            "criminal_impact": false,
            "control_level": "+"
        }
        Response: {
            "status": "success",
            "risk_score": 45,
            "risk_level": "Medium",
            "financial_score": 15,
            "economic_score": 0,
            "non_economic_score": 30,
            "control_multiplier": 0.9,
            "final_score": 40.5,
            "analysis": {...}
        }
    """
    try:
        result = risk_service.calculate_risk_score(data)
        return JSONResponse(result)

    except Exception as e:
        logger.error(f"Error in save_risk_assessment: {str(e)}", exc_info=True)
        return JSONResponse({
            "status": "error",
            "message": f"Errore nel calcolo del rischio: {str(e)}",
            "error_details": str(e)
        }, status_code=500)


@router.post("/calculate-assessment")
def calculate_risk_assessment(
    data: dict,
    risk_service: RiskService = Depends(get_risk_service)
) -> JSONResponse:
    """
    Calculate risk matrix position based on economic/non-economic loss and control level

    This endpoint implements the risk matrix calculation that maps:
    - Economic & non-economic loss (colors G/Y/O/R) to inherent risk
    - Control level (++/+/-/--) to control effectiveness
    - Final matrix position (A1-D4) with risk level and recommendations

    Args:
        data: Assessment data including:
            - economic_loss: Color code (G/Y/O/R)
            - non_economic_loss: Color code (G/Y/O/R)
            - control_level: Control effectiveness (++/+/-/--)

    Returns:
        JSONResponse with matrix position, risk level, and recommendations

    Example:
        POST /risk/calculate-assessment
        Body: {
            "economic_loss": "Y",
            "non_economic_loss": "O",
            "control_level": "+"
        }
        Response: {
            "status": "success",
            "matrix_position": "B3",
            "risk_level": "Medium",
            "risk_color": "yellow",
            "risk_value": 0,
            "inherent_risk": {"value": 3, "label": "Medium"},
            "control_effectiveness": {"value": 3, "label": "+", "description": "..."},
            "calculation_details": {...},
            "recommendations": [...]
        }
    """
    try:
        result = risk_service.calculate_risk_matrix(data)
        return JSONResponse(result)

    except Exception as e:
        logger.error(f"Error in calculate_risk_assessment: {str(e)}", exc_info=True)
        return JSONResponse({
            "status": "error",
            "message": f"Errore nel calcolo del rischio: {str(e)}",
            "error_details": str(e)
        }, status_code=500)
