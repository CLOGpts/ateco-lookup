"""
Unit tests for Risk Router

Tests cover the API endpoints for risk assessment:
- GET /risk/events/{category}
- GET /risk/description/{event_code}
- GET /risk/assessment-fields
- POST /risk/save-assessment
- POST /risk/calculate-assessment
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.routers import risk as risk_router


# ==================== Fixtures ====================

@pytest.fixture
def app():
    """Create a test FastAPI app with risk router"""
    app = FastAPI()
    app.include_router(risk_router.router)
    return app


@pytest.fixture
def client(app):
    """Create a test client"""
    return TestClient(app)


@pytest.fixture
def mock_risk_service():
    """Mock RiskService for testing"""
    mock = MagicMock()
    return mock


# ==================== Test: GET /risk/events/{category} ====================

def test_get_events_success(client, mock_risk_service):
    """Test successful retrieval of events for a category"""
    with patch('app.routers.risk.get_risk_service', return_value=mock_risk_service):
        mock_risk_service.get_events_for_category.return_value = {
            "category": "Damage_Danni",
            "original_request": "damage",
            "events": [
                {"code": "101", "name": "Incendio", "severity": "medium"},
                {"code": "102", "name": "Allagamento", "severity": "medium"}
            ],
            "total": 2
        }

        response = client.get("/risk/events/damage")

        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "Damage_Danni"
        assert len(data["events"]) == 2
        assert data["total"] == 2


def test_get_events_category_not_found(client, mock_risk_service):
    """Test error when category doesn't exist"""
    with patch('app.routers.risk.get_risk_service', return_value=mock_risk_service):
        mock_risk_service.get_events_for_category.return_value = {
            "error": "Category 'invalid' not found",
            "available_categories": ["Damage_Danni", "Business_disruption"]
        }

        response = client.get("/risk/events/invalid")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data


def test_get_events_with_mapping(client, mock_risk_service):
    """Test category alias mapping works"""
    with patch('app.routers.risk.get_risk_service', return_value=mock_risk_service):
        mock_risk_service.get_events_for_category.return_value = {
            "category": "Execution_delivery_Problemi_di_produzione_o_consegna",
            "original_request": "operational",
            "events": [{"code": "301", "name": "Errore operativo", "severity": "low"}],
            "total": 1
        }

        response = client.get("/risk/events/operational")

        assert response.status_code == 200
        data = response.json()
        assert data["original_request"] == "operational"


def test_get_events_service_error(client, mock_risk_service):
    """Test handling of service errors"""
    with patch('app.routers.risk.get_risk_service', return_value=mock_risk_service):
        mock_risk_service.get_events_for_category.side_effect = Exception("Database error")

        response = client.get("/risk/events/damage")

        assert response.status_code == 500
        data = response.json()
        assert "error" in data


# ==================== Test: GET /risk/description/{event_code} ====================

def test_get_description_success(client, mock_risk_service):
    """Test successful retrieval of event description"""
    with patch('app.routers.risk.get_risk_service', return_value=mock_risk_service):
        mock_risk_service.get_event_description.return_value = {
            "code": "101",
            "name": "Incendio strutture",
            "description": "Danno da incendio...",
            "category": "Damage_Danni",
            "impact": "high",
            "probability": "medium",
            "controls": ["Sistema antincendio", "Assicurazione"],
            "source": "Excel Risk Mapping",
            "has_vlookup": True
        }

        response = client.get("/risk/description/101")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "101"
        assert data["name"] == "Incendio strutture"
        assert data["has_vlookup"] is True


def test_get_description_not_found(client, mock_risk_service):
    """Test description for non-existent event code"""
    with patch('app.routers.risk.get_risk_service', return_value=mock_risk_service):
        mock_risk_service.get_event_description.return_value = {
            "code": "999",
            "name": "Evento non mappato",
            "description": "Evento 999 non presente nel mapping Excel",
            "source": "Generic"
        }

        response = client.get("/risk/description/999")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "999"
        assert data["source"] == "Generic"


def test_get_description_invalid_format(client, mock_risk_service):
    """Test description with malformed event code"""
    with patch('app.routers.risk.get_risk_service', return_value=mock_risk_service):
        mock_risk_service.get_event_description.return_value = {
            "error": "Invalid event code format",
            "received": "[object Object]"
        }

        response = client.get("/risk/description/[object Object]")

        assert response.status_code == 400
        data = response.json()
        assert "error" in data


def test_get_description_service_error(client, mock_risk_service):
    """Test handling of service errors in description"""
    with patch('app.routers.risk.get_risk_service', return_value=mock_risk_service):
        mock_risk_service.get_event_description.side_effect = Exception("Service error")

        response = client.get("/risk/description/101")

        assert response.status_code == 500
        data = response.json()
        assert "error" in data


# ==================== Test: GET /risk/assessment-fields ====================

def test_get_assessment_fields_success(client):
    """Test successful retrieval of assessment field structure"""
    response = client.get("/risk/assessment-fields")

    assert response.status_code == 200
    data = response.json()
    assert "fields" in data
    assert len(data["fields"]) == 8  # 8 fields defined

    # Check first field structure
    first_field = data["fields"][0]
    assert "id" in first_field
    assert "column" in first_field
    assert "question" in first_field
    assert "type" in first_field
    assert "options" in first_field


def test_get_assessment_fields_structure(client):
    """Test assessment fields have correct structure"""
    response = client.get("/risk/assessment-fields")
    data = response.json()

    field_ids = [f["id"] for f in data["fields"]]
    expected_ids = [
        "impatto_finanziario",
        "perdita_economica",
        "impatto_immagine",
        "impatto_regolamentare",
        "impatto_criminale",
        "perdita_non_economica",
        "controllo",
        "descrizione_controllo"
    ]

    assert set(field_ids) == set(expected_ids)


def test_get_assessment_fields_financial_options(client):
    """Test financial impact field has correct options"""
    response = client.get("/risk/assessment-fields")
    data = response.json()

    financial_field = next(f for f in data["fields"] if f["id"] == "impatto_finanziario")

    assert "N/A" in financial_field["options"]
    assert "3 - 5M€" in financial_field["options"]
    assert len(financial_field["options"]) == 9


def test_get_assessment_fields_control_vlookup(client):
    """Test control description field has VLOOKUP structure"""
    response = client.get("/risk/assessment-fields")
    data = response.json()

    control_desc_field = next(f for f in data["fields"] if f["id"] == "descrizione_controllo")

    assert control_desc_field["autoPopulated"] is True
    assert "vlookupMap" in control_desc_field
    assert "++" in control_desc_field["vlookupMap"]


# ==================== Test: POST /risk/save-assessment ====================

def test_save_assessment_success(client, mock_risk_service):
    """Test successful risk score calculation"""
    with patch('app.routers.risk.get_risk_service', return_value=mock_risk_service):
        mock_risk_service.calculate_risk_score.return_value = {
            "status": "success",
            "risk_score": 45,
            "risk_level": "Medium",
            "financial_score": 15,
            "economic_score": 0,
            "non_economic_score": 30,
            "control_multiplier": 0.9,
            "final_score": 40.5
        }

        payload = {
            "financial_impact": "10 - 50K€",
            "image_impact": True,
            "regulatory_impact": True,
            "criminal_impact": True,
            "control_level": "+"
        }

        response = client.post("/risk/save-assessment", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["risk_level"] == "Medium"


def test_save_assessment_high_risk(client, mock_risk_service):
    """Test high-risk assessment calculation"""
    with patch('app.routers.risk.get_risk_service', return_value=mock_risk_service):
        mock_risk_service.calculate_risk_score.return_value = {
            "status": "success",
            "risk_score": 85,
            "risk_level": "High",
            "financial_score": 40,
            "non_economic_score": 30,
            "control_multiplier": 1.2,
            "final_score": 84
        }

        payload = {
            "financial_impact": "3 - 5M€",
            "image_impact": True,
            "regulatory_impact": True,
            "criminal_impact": True,
            "control_level": "--"
        }

        response = client.post("/risk/save-assessment", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["risk_level"] == "High"


def test_save_assessment_service_error(client, mock_risk_service):
    """Test error handling in save assessment"""
    with patch('app.routers.risk.get_risk_service', return_value=mock_risk_service):
        mock_risk_service.calculate_risk_score.side_effect = Exception("Calculation error")

        payload = {"financial_impact": "10 - 50K€"}

        response = client.post("/risk/save-assessment", json=payload)

        assert response.status_code == 500
        data = response.json()
        assert data["status"] == "error"


# ==================== Test: POST /risk/calculate-assessment ====================

def test_calculate_assessment_success(client, mock_risk_service):
    """Test successful risk matrix calculation"""
    with patch('app.routers.risk.get_risk_service', return_value=mock_risk_service):
        mock_risk_service.calculate_risk_matrix.return_value = {
            "status": "success",
            "matrix_position": "B3",
            "risk_level": "Medium",
            "risk_color": "yellow",
            "risk_value": 0,
            "inherent_risk": {"value": 3, "label": "Medium"},
            "control_effectiveness": {"value": 3, "label": "+", "description": "Sostanzialmente adeguato"},
            "calculation_details": {},
            "recommendations": ["Monitorare regolarmente", "Valutare miglioramenti"]
        }

        payload = {
            "economic_loss": "Y",
            "non_economic_loss": "O",
            "control_level": "+"
        }

        response = client.post("/risk/calculate-assessment", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["matrix_position"] == "B3"
        assert data["risk_level"] == "Medium"


def test_calculate_assessment_critical_risk(client, mock_risk_service):
    """Test critical risk matrix position"""
    with patch('app.routers.risk.get_risk_service', return_value=mock_risk_service):
        mock_risk_service.calculate_risk_matrix.return_value = {
            "status": "success",
            "matrix_position": "D1",
            "risk_level": "Critical",
            "risk_color": "red",
            "risk_value": 1,
            "inherent_risk": {"value": 1, "label": "Critical"},
            "control_effectiveness": {"value": 1, "label": "--", "description": "Non adeguato"},
            "recommendations": ["Azione immediata richiesta", "Escalation management"]
        }

        payload = {
            "economic_loss": "R",
            "non_economic_loss": "R",
            "control_level": "--"
        }

        response = client.post("/risk/calculate-assessment", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["risk_level"] == "Critical"
        assert data["matrix_position"] == "D1"


def test_calculate_assessment_low_risk(client, mock_risk_service):
    """Test low risk matrix position"""
    with patch('app.routers.risk.get_risk_service', return_value=mock_risk_service):
        mock_risk_service.calculate_risk_matrix.return_value = {
            "status": "success",
            "matrix_position": "A4",
            "risk_level": "Low",
            "risk_color": "green",
            "risk_value": 0,
            "recommendations": ["Rischio accettabile", "Mantenere controlli attuali"]
        }

        payload = {
            "economic_loss": "G",
            "non_economic_loss": "G",
            "control_level": "++"
        }

        response = client.post("/risk/calculate-assessment", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["risk_level"] == "Low"


def test_calculate_assessment_service_error(client, mock_risk_service):
    """Test error handling in matrix calculation"""
    with patch('app.routers.risk.get_risk_service', return_value=mock_risk_service):
        mock_risk_service.calculate_risk_matrix.side_effect = Exception("Matrix calculation failed")

        payload = {
            "economic_loss": "Y",
            "non_economic_loss": "Y",
            "control_level": "+"
        }

        response = client.post("/risk/calculate-assessment", json=payload)

        assert response.status_code == 500
        data = response.json()
        assert data["status"] == "error"


# ==================== Test: Response Structure ====================

def test_events_response_structure(client, mock_risk_service):
    """Test events response has required fields"""
    with patch('app.routers.risk.get_risk_service', return_value=mock_risk_service):
        mock_risk_service.get_events_for_category.return_value = {
            "category": "Test",
            "original_request": "test",
            "events": [],
            "total": 0
        }

        response = client.get("/risk/events/test")
        data = response.json()

        required_fields = ["category", "original_request", "events", "total"]
        assert all(field in data for field in required_fields)


def test_description_response_structure(client, mock_risk_service):
    """Test description response has required fields"""
    with patch('app.routers.risk.get_risk_service', return_value=mock_risk_service):
        mock_risk_service.get_event_description.return_value = {
            "code": "101",
            "name": "Test",
            "description": "Test desc",
            "category": "Test",
            "impact": "medium",
            "probability": "low",
            "controls": []
        }

        response = client.get("/risk/description/101")
        data = response.json()

        required_fields = ["code", "name", "description", "impact", "probability", "controls"]
        assert all(field in data for field in required_fields)
