"""
Unit tests for RiskService

Tests cover the core risk assessment business logic including:
- Event category retrieval
- Event description lookup
- Risk score calculation
- Risk matrix calculation
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import json

from app.services.risk_service import RiskService


# ==================== Fixtures ====================

@pytest.fixture
def mock_risk_data():
    """Mock risk data structure matching MAPPATURE_EXCEL_PERFETTE.json"""
    return {
        "mappature_categoria_eventi": {
            "Damage_Danni": [
                "101 - Incendio strutture",
                "102 - Danni da acqua",
                "103 - Danni elettrici"
            ],
            "Business_disruption": [
                "201 - Interruzione sistemi IT",
                "202 - Blackout energetico"
            ],
            "Execution_delivery_Problemi_di_produzione_o_consegna": [
                "301 - Ritardo produzione",
                "302 - Errore qualità"
            ],
            "Employment_practices_Dipendenti": [
                "401 - Infortunio lavorativo"
            ],
            "Clients_product_Clienti": [
                "501 - Reclamo cliente"
            ],
            "Internal_Fraud_Frodi_interne": [
                "601 - Furto interno"
            ],
            "External_fraud_Frodi_esterne": [
                "701 - Attacco hacker"
            ]
        },
        "vlookup_map": {
            "101": "Danno da incendio a strutture aziendali con possibile interruzione operativa",
            "201": "Interruzione dei sistemi informatici critici per l'operatività"
        }
    }


@pytest.fixture
def risk_service_with_mock_data(mock_risk_data, tmp_path):
    """RiskService instance with mocked data file"""
    # Create a temporary JSON file with mock data
    data_file = tmp_path / "mock_risk_data.json"
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(mock_risk_data, f)

    return RiskService(data_path=data_file)


# ==================== Test: Initialization ====================

def test_risk_service_initialization():
    """Test RiskService can be initialized"""
    service = RiskService()
    assert service is not None
    assert hasattr(service, 'EXCEL_CATEGORIES')
    assert hasattr(service, 'EXCEL_DESCRIPTIONS')


def test_risk_service_with_custom_path(tmp_path):
    """Test RiskService initialization with custom data path"""
    data_file = tmp_path / "custom_risk.json"
    mock_data = {
        "mappature_categoria_eventi": {"Test": ["101 - Test event"]},
        "vlookup_map": {}
    }
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(mock_data, f)

    service = RiskService(data_path=data_file)
    assert service is not None
    assert "Test" in service.EXCEL_CATEGORIES


def test_risk_service_missing_file():
    """Test RiskService handles missing data file gracefully"""
    service = RiskService(data_path=Path("/nonexistent/file.json"))
    # Should initialize with fallback data (7 default categories)
    assert len(service.EXCEL_CATEGORIES) == 7
    assert "Damage_Danni" in service.EXCEL_CATEGORIES
    assert service.EXCEL_DESCRIPTIONS == {}


# ==================== Test: get_events_for_category ====================

def test_get_events_for_category_valid(risk_service_with_mock_data):
    """Test getting events for a valid category"""
    result = risk_service_with_mock_data.get_events_for_category("Damage_Danni")

    assert "category" in result
    assert "events" in result
    assert "total" in result
    assert result["category"] == "Damage_Danni"
    assert len(result["events"]) == 3
    assert result["total"] == 3

    # Check first event structure
    first_event = result["events"][0]
    assert first_event["code"] == "101"
    assert first_event["name"] == "Incendio strutture"
    assert "severity" in first_event


def test_get_events_for_category_with_mapping(risk_service_with_mock_data):
    """Test getting events with category mapping (alias)"""
    result = risk_service_with_mock_data.get_events_for_category("operational")

    # Should map 'operational' to 'Execution_delivery_Problemi_di_produzione_o_consegna'
    assert "events" in result
    assert result["original_request"] == "operational"


def test_get_events_for_category_invalid(risk_service_with_mock_data):
    """Test getting events for an invalid category"""
    result = risk_service_with_mock_data.get_events_for_category("InvalidCategory")

    assert "error" in result
    assert "available_categories" in result


def test_get_events_severity_calculation(risk_service_with_mock_data):
    """Test severity calculation based on event codes"""
    result = risk_service_with_mock_data.get_events_for_category("Damage_Danni")
    events = result["events"]

    # Code starting with '1' should be 'medium'
    assert all(e["severity"] == "medium" for e in events if e["code"].startswith("1"))

    # Test different code ranges
    result2 = risk_service_with_mock_data.get_events_for_category("Business_disruption")
    events2 = result2["events"]
    # Code starting with '2' should be 'high'
    assert all(e["severity"] == "high" for e in events2 if e["code"].startswith("2"))


# ==================== Test: get_event_description ====================

def test_get_event_description_valid(risk_service_with_mock_data):
    """Test getting description for a valid event code"""
    result = risk_service_with_mock_data.get_event_description("101")

    assert "code" in result
    assert "name" in result
    assert "description" in result
    assert "category" in result
    assert "impact" in result
    assert "probability" in result
    assert "controls" in result

    assert result["code"] == "101"
    assert result["name"] == "Incendio strutture"
    assert result["category"] == "Damage_Danni"


def test_get_event_description_with_vlookup(risk_service_with_mock_data):
    """Test description includes VLOOKUP data when available"""
    result = risk_service_with_mock_data.get_event_description("101")

    assert "has_vlookup" in result
    assert result["has_vlookup"] is True
    # Should contain the VLOOKUP description
    assert "incendio" in result["description"].lower()


def test_get_event_description_without_vlookup(risk_service_with_mock_data):
    """Test description without VLOOKUP data"""
    result = risk_service_with_mock_data.get_event_description("102")

    assert "has_vlookup" in result
    # 102 doesn't have VLOOKUP in mock data
    assert result["has_vlookup"] is False


def test_get_event_description_invalid_code(risk_service_with_mock_data):
    """Test description for invalid event code"""
    result = risk_service_with_mock_data.get_event_description("999")

    assert result["code"] == "999"
    assert result["name"] == "Evento non mappato"
    assert result["source"] == "Generic"


def test_get_event_description_malformed_code(risk_service_with_mock_data):
    """Test description handles malformed codes"""
    result = risk_service_with_mock_data.get_event_description("[object Object]")

    assert "error" in result
    assert "Invalid event code" in result["error"]


# ==================== Test: calculate_risk_score ====================

def test_calculate_risk_score_basic(risk_service_with_mock_data):
    """Test basic risk score calculation"""
    data = {
        "financial_impact": "10 - 50K€",
        "image_impact": False,
        "regulatory_impact": False,
        "criminal_impact": False,
        "control_level": "+"
    }

    result = risk_service_with_mock_data.calculate_risk_score(data)

    assert "status" in result
    assert result["status"] == "success"
    assert "risk_score" in result
    assert "risk_level" in result
    assert "financial_score" in result


def test_calculate_risk_score_high_impact(risk_service_with_mock_data):
    """Test risk score with high impact values"""
    data = {
        "impatto_finanziario": "3 - 5M€",
        "impatto_immagine": "Si",
        "impatto_regolamentare": "Si",
        "impatto_criminale": "Si",
        "controllo": "--"
    }

    result = risk_service_with_mock_data.calculate_risk_score(data)

    # Should have high financial score (40 pts)
    assert result["financial_score"] == 40
    # Should have high non-economic score (30 pts: 10+10+10)
    assert result["non_economic_score"] == 30
    # Poor controls should increase risk
    assert result["risk_level"] in ["High", "Critical"]


def test_calculate_risk_score_control_multiplier(risk_service_with_mock_data):
    """Test control level affects final score"""
    base_data = {
        "impatto_finanziario": "50 - 100K€",
        "impatto_immagine": "Si",
        "impatto_regolamentare": "No",
        "impatto_criminale": "No"
    }

    # Good controls (0.5x multiplier)
    data_good_control = {**base_data, "controllo": "++"}
    result_good = risk_service_with_mock_data.calculate_risk_score(data_good_control)

    # Poor controls (1.5x multiplier)
    data_poor_control = {**base_data, "controllo": "--"}
    result_poor = risk_service_with_mock_data.calculate_risk_score(data_poor_control)

    # Poor controls should result in higher final score
    assert result_poor["final_score"] > result_good["final_score"]


# ==================== Test: calculate_risk_matrix ====================

def test_calculate_risk_matrix_basic(risk_service_with_mock_data):
    """Test basic risk matrix calculation"""
    data = {
        "economic_loss": "Y",  # Yellow = 3
        "non_economic_loss": "G",  # Green = 4
        "control_level": "+"  # Row 3
    }

    result = risk_service_with_mock_data.calculate_risk_matrix(data)

    assert "status" in result
    assert result["status"] == "success"
    assert "matrix_position" in result
    assert "risk_level" in result
    assert "risk_color" in result
    assert "inherent_risk" in result
    assert "control_effectiveness" in result
    assert "recommendations" in result


def test_calculate_risk_matrix_positions(risk_service_with_mock_data):
    """Test various matrix positions are calculated correctly"""
    # Low risk: Green economic, Green non-economic, good controls
    data_low = {
        "economic_loss": "G",
        "non_economic_loss": "G",
        "control_level": "++"
    }
    result_low = risk_service_with_mock_data.calculate_risk_matrix(data_low)
    assert result_low["risk_level"] == "Low"
    assert result_low["matrix_position"] == "A4"

    # Critical risk: Red economic, Red non-economic, poor controls
    data_critical = {
        "economic_loss": "R",
        "non_economic_loss": "R",
        "control_level": "--"
    }
    result_critical = risk_service_with_mock_data.calculate_risk_matrix(data_critical)
    assert result_critical["risk_level"] == "Critical"
    assert result_critical["matrix_position"] == "D1"


def test_calculate_risk_matrix_inherent_risk(risk_service_with_mock_data):
    """Test inherent risk is minimum of economic and non-economic"""
    data = {
        "economic_loss": "O",  # Orange = 2
        "non_economic_loss": "Y",  # Yellow = 3
        "control_level": "+"
    }

    result = risk_service_with_mock_data.calculate_risk_matrix(data)

    # Inherent risk should be min(2, 3) = 2
    assert result["inherent_risk"]["value"] == 2
    assert result["inherent_risk"]["label"] == "High"


def test_calculate_risk_matrix_recommendations(risk_service_with_mock_data):
    """Test recommendations are provided based on risk level"""
    data_critical = {
        "economic_loss": "R",
        "non_economic_loss": "R",
        "control_level": "--"
    }

    result = risk_service_with_mock_data.calculate_risk_matrix(data_critical)

    assert len(result["recommendations"]) > 0
    # Critical risk should have urgent recommendations
    assert any("immediata" in rec.lower() or "urgente" in rec.lower()
              for rec in result["recommendations"])


# ==================== Test: Helper Methods ====================

def test_calculate_severity(risk_service_with_mock_data):
    """Test severity calculation for different event codes"""
    assert risk_service_with_mock_data._calculate_severity("101") == "medium"
    assert risk_service_with_mock_data._calculate_severity("201") == "high"
    assert risk_service_with_mock_data._calculate_severity("301") == "low"
    assert risk_service_with_mock_data._calculate_severity("601") == "critical"
    assert risk_service_with_mock_data._calculate_severity("701") == "critical"


def test_get_impact_for_code(risk_service_with_mock_data):
    """Test impact description for event codes"""
    # Code 1xx should return damage description
    assert risk_service_with_mock_data._get_impact_for_code("101") == "Danni fisici e materiali"

    # Code 2xx should return business disruption description
    assert risk_service_with_mock_data._get_impact_for_code("201") == "Interruzione operativa e perdita dati"


def test_get_probability_for_code(risk_service_with_mock_data):
    """Test probability calculation for event codes"""
    prob = risk_service_with_mock_data._get_probability_for_code("101")
    assert prob in ["low", "medium", "high"]


def test_get_controls_for_code(risk_service_with_mock_data):
    """Test controls are suggested for event codes"""
    controls = risk_service_with_mock_data._get_controls_for_code("101")
    assert isinstance(controls, list)
    assert len(controls) > 0


def test_get_recommendations(risk_service_with_mock_data):
    """Test recommendations for different risk levels"""
    recs_critical = risk_service_with_mock_data._get_recommendations("Critical")
    recs_low = risk_service_with_mock_data._get_recommendations("Low")

    assert len(recs_critical) > 0
    assert len(recs_low) > 0

    # Critical should have more urgent language
    assert any("immediata" in rec.lower() for rec in recs_critical)
    assert any("accettabile" in rec.lower() for rec in recs_low)


# ==================== Test: Edge Cases ====================

def test_empty_data_handling(risk_service_with_mock_data):
    """Test service handles empty/missing data gracefully"""
    result = risk_service_with_mock_data.calculate_risk_score({})

    # Should not crash, should return some result
    assert "status" in result


def test_malformed_financial_impact(risk_service_with_mock_data):
    """Test service handles malformed financial impact values"""
    data = {
        "financial_impact": "Invalid Value",
        "control_level": "+"
    }

    result = risk_service_with_mock_data.calculate_risk_score(data)

    # Should handle gracefully and default to 0
    assert result["financial_score"] == 0


def test_malformed_color_codes(risk_service_with_mock_data):
    """Test service handles invalid color codes in matrix calculation"""
    data = {
        "economic_loss": "InvalidColor",
        "non_economic_loss": "G",
        "control_level": "+"
    }

    result = risk_service_with_mock_data.calculate_risk_matrix(data)

    # Should default to safe value (green = 4)
    assert result["status"] == "success"
