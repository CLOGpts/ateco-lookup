"""
Unit tests for Seismic Router

Tests cover the API endpoints for seismic zones:
- GET /seismic/zone
- GET /seismic/zone-from-db
- GET /seismic/suggestions

Story 2.6: Extract Seismic Zones Service
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.routers import seismic as seismic_router


# ==================== Fixtures ====================

@pytest.fixture
def mock_seismic_service():
    """Mock SeismicService for testing"""
    mock = MagicMock()
    return mock


@pytest.fixture
def app(mock_seismic_service):
    """Create a test FastAPI app with seismic router and mocked service"""
    app = FastAPI()
    app.include_router(seismic_router.router)
    # Override dependency to use mock
    app.dependency_overrides[seismic_router.get_seismic_service] = lambda: mock_seismic_service
    return app


@pytest.fixture
def client(app):
    """Create a test client"""
    return TestClient(app)


# ==================== Test: GET /seismic/zone ====================

def test_get_zone_success_exact_match(client, mock_seismic_service):
    """Test successful zone retrieval with exact match"""
    mock_seismic_service.get_zone_by_comune.return_value = {
        "comune": "ROMA",
        "provincia": "RM",
        "regione": "LAZIO",
        "zona_sismica": 3,
        "accelerazione_ag": 0.15,
        "risk_level": "Media",
        "description": "Zona 3 - Sismicità bassa",
        "normativa": "OPCM 3519/2006",
        "source": "database_match",
        "confidence": 1.0
    }

    response = client.get("/seismic/zone?comune=Roma")

    assert response.status_code == 200
    data = response.json()
    assert data["comune"] == "ROMA"
    assert data["provincia"] == "RM"
    assert data["zona_sismica"] == 3
    assert data["confidence"] == 1.0
    assert data["source"] == "database_match"


def test_get_zone_success_with_provincia(client, mock_seismic_service):
    """Test zone retrieval with provincia parameter"""
    mock_seismic_service.get_zone_by_comune.return_value = {
        "comune": "ROMA",
        "provincia": "RM",
        "regione": "LAZIO",
        "zona_sismica": 3,
        "accelerazione_ag": 0.15,
        "risk_level": "Media",
        "description": "Zona 3 - Sismicità bassa",
        "normativa": "OPCM 3519/2006",
        "source": "database_match",
        "confidence": 1.0
    }

    response = client.get("/seismic/zone?comune=Roma&provincia=RM")

    assert response.status_code == 200
    data = response.json()
    assert data["comune"] == "ROMA"
    assert data["provincia"] == "RM"


def test_get_zone_fuzzy_match(client, mock_seismic_service):
    """Test zone retrieval with fuzzy matching"""
    mock_seismic_service.get_zone_by_comune.return_value = {
        "comune": "ROMA",
        "input_comune": "RОМА",
        "provincia": "RM",
        "regione": "LAZIO",
        "zona_sismica": 3,
        "accelerazione_ag": 0.15,
        "risk_level": "Media",
        "description": "Zona 3 - Sismicità bassa",
        "normativa": "OPCM 3519/2006",
        "source": "fuzzy_match",
        "confidence": 0.85,
        "note": "Match approssimato: 'RОМА' -> 'ROMA'"
    }

    response = client.get("/seismic/zone?comune=Rома")

    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "fuzzy_match"
    assert data["confidence"] < 1.0
    assert "note" in data


def test_get_zone_database_not_found(client, mock_seismic_service):
    """Test error when database file not found"""
    mock_seismic_service.get_zone_by_comune.side_effect = FileNotFoundError(
        "Database not found"
    )

    response = client.get("/seismic/zone?comune=Roma")

    assert response.status_code == 500
    data = response.json()
    assert data["error"] == "database_not_found"
    assert "disponibile" in data["message"]


def test_get_zone_comune_not_found(client, mock_seismic_service):
    """Test error when comune not found"""
    mock_seismic_service.get_zone_by_comune.side_effect = ValueError(
        "comune_not_found: Comune 'XYZ' non trovato"
    )
    mock_seismic_service.get_suggestions.return_value = [
        {"comune": "ROMA", "provincia": "RM", "zona_sismica": 3}
    ]

    response = client.get("/seismic/zone?comune=XYZ")

    assert response.status_code == 404
    data = response.json()
    assert data["error"] == "comune_not_found"
    assert "suggestions" in data
    assert "suggestion_text" in data


def test_get_zone_comune_provincia_mismatch(client, mock_seismic_service):
    """Test error when comune doesn't match specified provincia"""
    mock_seismic_service.get_zone_by_comune.side_effect = ValueError(
        "comune_provincia_mismatch: Roma non trovato in provincia MI"
    )

    response = client.get("/seismic/zone?comune=Roma&provincia=MI")

    assert response.status_code == 404
    data = response.json()
    assert data["error"] == "comune_provincia_mismatch"


def test_get_zone_no_match_in_provincia(client, mock_seismic_service):
    """Test error when no matches found in specified provincia"""
    mock_seismic_service.get_zone_by_comune.side_effect = ValueError(
        "no_match_in_provincia: Nessun comune simile trovato. Suggerimenti: []"
    )

    response = client.get("/seismic/zone?comune=XYZ&provincia=RM")

    assert response.status_code == 404
    data = response.json()
    assert data["error"] == "no_match_in_provincia"


def test_get_zone_missing_comune_parameter(client, mock_seismic_service):
    """Test validation error when comune parameter is missing"""
    response = client.get("/seismic/zone")

    assert response.status_code == 422  # Validation error


def test_get_zone_internal_error(client, mock_seismic_service):
    """Test handling of unexpected internal errors"""
    mock_seismic_service.get_zone_by_comune.side_effect = Exception("Unexpected error")

    response = client.get("/seismic/zone?comune=Roma")

    assert response.status_code == 500
    data = response.json()
    assert data["error"] == "internal_error"


# ==================== Test: GET /seismic/zone-from-db ====================

def test_get_zone_from_db_success(client, mock_seismic_service):
    """Test successful zone retrieval from database"""
    mock_seismic_service.get_zone_from_db.return_value = {
        "comune": "ROMA",
        "provincia": "RM",
        "regione": "LAZIO",
        "zona_sismica": 3,
        "accelerazione_ag": 0.15,
        "risk_level": "Media",
        "description": "Zona 3 - Sismicità bassa",
        "normativa": "OPCM 3519/2006",
        "source": "database_match",
        "confidence": 1.0
    }

    with patch('database.config.get_db_session') as mock_db_session:
        mock_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_session

        response = client.get("/seismic/zone-from-db?comune=Roma")

        assert response.status_code == 200
        data = response.json()
        assert data["comune"] == "ROMA"
        assert data["zona_sismica"] == 3
        assert data["source"] == "database_match"


def test_get_zone_from_db_with_provincia(client, mock_seismic_service):
    """Test database query with provincia filter"""
    mock_seismic_service.get_zone_from_db.return_value = {
        "comune": "ROMA",
        "provincia": "RM",
        "regione": "LAZIO",
        "zona_sismica": 3,
        "accelerazione_ag": 0.15,
        "risk_level": "Media",
        "description": "Zona 3 - Sismicità bassa",
        "normativa": "OPCM 3519/2006",
        "source": "database_match",
        "confidence": 1.0
    }

    with patch('database.config.get_db_session') as mock_db_session:
        mock_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_session

        response = client.get("/seismic/zone-from-db?comune=Roma&provincia=RM")

        assert response.status_code == 200
        data = response.json()
        assert data["provincia"] == "RM"


def test_get_zone_from_db_not_found(client, mock_seismic_service):
    """Test error when comune not found in database"""
    mock_seismic_service.get_zone_from_db.side_effect = ValueError(
        "comune_not_found: Comune not found"
    )

    with patch('database.config.get_db_session') as mock_db_session:
        mock_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_session

        response = client.get("/seismic/zone-from-db?comune=XYZ")

        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "comune_not_found"


def test_get_zone_from_db_database_error(client, mock_seismic_service):
    """Test handling of database errors"""
    mock_seismic_service.get_zone_from_db.side_effect = Exception("DB connection error")

    with patch('database.config.get_db_session') as mock_db_session:
        mock_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_session

        response = client.get("/seismic/zone-from-db?comune=Roma")

        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "database_error"


def test_get_zone_from_db_missing_comune(client, mock_seismic_service):
    """Test validation error when comune parameter is missing"""
    response = client.get("/seismic/zone-from-db")

    assert response.status_code == 422  # Validation error


# ==================== Test: GET /seismic/suggestions ====================

def test_get_suggestions_success(client, mock_seismic_service):
    """Test successful retrieval of comune suggestions"""
    mock_seismic_service.get_suggestions.return_value = [
        {"comune": "ROMA", "provincia": "RM", "zona_sismica": 3},
        {"comune": "ROMANO", "provincia": "BG", "zona_sismica": 4}
    ]

    response = client.get("/seismic/suggestions?comune=rom")

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "rom"
    assert len(data["suggestions"]) == 2
    assert data["count"] == 2
    assert data["suggestions"][0]["comune"] == "ROMA"


def test_get_suggestions_with_limit(client, mock_seismic_service):
    """Test suggestions with custom limit"""
    mock_seismic_service.get_suggestions.return_value = [
        {"comune": "ROMA", "provincia": "RM", "zona_sismica": 3}
    ]

    response = client.get("/seismic/suggestions?comune=rom&limit=1")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1


def test_get_suggestions_empty_results(client, mock_seismic_service):
    """Test suggestions when no matches found"""
    mock_seismic_service.get_suggestions.return_value = []

    response = client.get("/seismic/suggestions?comune=xyz999")

    assert response.status_code == 200
    data = response.json()
    assert data["suggestions"] == []
    assert data["count"] == 0


def test_get_suggestions_invalid_limit(client, mock_seismic_service):
    """Test validation error for invalid limit value"""
    response = client.get("/seismic/suggestions?comune=roma&limit=0")

    assert response.status_code == 422  # Validation error


def test_get_suggestions_limit_too_high(client, mock_seismic_service):
    """Test validation error for limit exceeding maximum"""
    response = client.get("/seismic/suggestions?comune=roma&limit=100")

    assert response.status_code == 422  # Validation error


def test_get_suggestions_missing_comune(client, mock_seismic_service):
    """Test validation error when comune parameter is missing"""
    response = client.get("/seismic/suggestions")

    assert response.status_code == 422  # Validation error


def test_get_suggestions_internal_error(client, mock_seismic_service):
    """Test handling of unexpected errors in suggestions endpoint"""
    mock_seismic_service.get_suggestions.side_effect = Exception("Unexpected error")

    response = client.get("/seismic/suggestions?comune=roma")

    assert response.status_code == 500
    data = response.json()
    assert data["error"] == "internal_error"
    assert data["suggestions"] == []


# ==================== Test: Edge Cases ====================

def test_comune_with_special_characters(client, mock_seismic_service):
    """Test handling of comuni with special characters"""
    mock_seismic_service.get_zone_by_comune.return_value = {
        "comune": "L'AQUILA",
        "provincia": "AQ",
        "regione": "ABRUZZO",
        "zona_sismica": 1,
        "accelerazione_ag": 0.35,
        "risk_level": "Molto Alta",
        "description": "Zona 1 - Sismicità alta",
        "normativa": "OPCM 3519/2006",
        "source": "database_match",
        "confidence": 1.0
    }

    response = client.get("/seismic/zone?comune=L'Aquila")

    assert response.status_code == 200
    data = response.json()
    assert data["comune"] == "L'AQUILA"


def test_comune_with_spaces(client, mock_seismic_service):
    """Test handling of comuni with spaces in name"""
    mock_seismic_service.get_zone_by_comune.return_value = {
        "comune": "SAN GIOVANNI",
        "provincia": "RM",
        "regione": "LAZIO",
        "zona_sismica": 3,
        "accelerazione_ag": 0.15,
        "risk_level": "Media",
        "description": "Zona 3 - Sismicità bassa",
        "normativa": "OPCM 3519/2006",
        "source": "database_match",
        "confidence": 1.0
    }

    response = client.get("/seismic/zone?comune=San Giovanni")

    assert response.status_code == 200
    data = response.json()
    assert "SAN GIOVANNI" in data["comune"]


def test_provincia_code_case_insensitive(client, mock_seismic_service):
    """Test that provincia codes are case-insensitive"""
    mock_seismic_service.get_zone_by_comune.return_value = {
        "comune": "ROMA",
        "provincia": "RM",
        "regione": "LAZIO",
        "zona_sismica": 3,
        "accelerazione_ag": 0.15,
        "risk_level": "Media",
        "description": "Zona 3 - Sismicità bassa",
        "normativa": "OPCM 3519/2006",
        "source": "database_match",
        "confidence": 1.0
    }

    response = client.get("/seismic/zone?comune=Roma&provincia=rm")

    assert response.status_code == 200
    data = response.json()
    assert data["provincia"] == "RM"
