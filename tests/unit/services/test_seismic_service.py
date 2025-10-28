"""
Unit tests for SeismicService

Story 2.6: Extract Seismic Zones Service
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from app.services.seismic_service import SeismicService


# Sample test data
SAMPLE_DB = {
    "metadata": {
        "source": "OPCM 3519/2006",
        "total_comuni": 3,
        "ag_reference": {
            "zona_1": 0.35,
            "zona_2": 0.25,
            "zona_3": 0.15,
            "zona_4": 0.05
        }
    },
    "comuni": {
        "ROMA": {
            "provincia": "RM",
            "regione": "LAZIO",
            "zona_sismica": 3,
            "accelerazione_ag": 0.15,
            "risk_level": "Media"
        },
        "MILANO": {
            "provincia": "MI",
            "regione": "LOMBARDIA",
            "zona_sismica": 4,
            "accelerazione_ag": 0.05,
            "risk_level": "Bassa"
        },
        "L'AQUILA": {
            "provincia": "AQ",
            "regione": "ABRUZZO",
            "zona_sismica": 1,
            "accelerazione_ag": 0.35,
            "risk_level": "Molto Alta"
        }
    }
}


@pytest.fixture
def service():
    """Create SeismicService instance with mock db_path."""
    service = SeismicService(db_path=Path("/fake/path/db.json"))
    return service


@pytest.fixture
def service_with_data(service):
    """Service with preloaded mock data."""
    service.db_data = SAMPLE_DB.copy()
    return service


# ============================================================
# Test: Initialization
# ============================================================

def test_service_initialization():
    """Test service initializes with correct defaults."""
    service = SeismicService()
    assert service.db_path.name == "zone_sismiche_comuni.json"
    assert service.db_data is None
    assert len(service.zone_descriptions) == 4


def test_service_initialization_custom_path():
    """Test service accepts custom db_path."""
    custom_path = Path("/custom/path/db.json")
    service = SeismicService(db_path=custom_path)
    assert service.db_path == custom_path


# ============================================================
# Test: load_seismic_database
# ============================================================

def test_load_seismic_database_success(service):
    """Test successful database load."""
    with patch('pathlib.Path.exists', return_value=True):
        with patch('builtins.open', mock_open(read_data=json.dumps(SAMPLE_DB))):
            result = service.load_seismic_database()

    assert result == SAMPLE_DB
    assert service.db_data == SAMPLE_DB


def test_load_seismic_database_cached(service):
    """Test database is cached after first load."""
    service.db_data = SAMPLE_DB.copy()

    # Should return cached data without file access
    result = service.load_seismic_database()
    assert result == SAMPLE_DB


def test_load_seismic_database_file_not_found(service):
    """Test FileNotFoundError when database doesn't exist."""
    with patch('pathlib.Path.exists', return_value=False):
        with pytest.raises(FileNotFoundError):
            service.load_seismic_database()


def test_load_seismic_database_invalid_json(service):
    """Test JSONDecodeError for invalid JSON."""
    with patch('pathlib.Path.exists', return_value=True):
        with patch('builtins.open', mock_open(read_data="invalid json {{")):
            with pytest.raises(json.JSONDecodeError):
                service.load_seismic_database()


# ============================================================
# Test: normalize_comune
# ============================================================

def test_normalize_comune_basic(service):
    """Test basic comune normalization."""
    assert service.normalize_comune("roma") == "ROMA"
    assert service.normalize_comune("  Milano  ") == "MILANO"


def test_normalize_comune_with_accents(service):
    """Test normalization removes accents."""
    assert service.normalize_comune("L'Aquila") == "L'AQUILA"
    assert service.normalize_comune("Città di Castello") == "CITTA DI CASTELLO"


def test_normalize_comune_with_apostrophe(service):
    """Test normalization handles apostrophes."""
    assert service.normalize_comune("Sant'Angelo") == "SANT'ANGELO"


# ============================================================
# Test: get_zone_description
# ============================================================

def test_get_zone_description_valid_zones(service):
    """Test zone descriptions for all valid zones."""
    assert "alta" in service.get_zone_description(1).lower()
    assert "media" in service.get_zone_description(2).lower()
    assert "bassa" in service.get_zone_description(3).lower()
    assert "molto bassa" in service.get_zone_description(4).lower()


def test_get_zone_description_invalid_zone(service):
    """Test description for invalid zone."""
    assert service.get_zone_description(99) == "N/D"


# ============================================================
# Test: calculate_fuzzy_confidence
# ============================================================

def test_calculate_fuzzy_confidence_exact_match(service):
    """Test confidence is 1.0 for exact match."""
    assert service.calculate_fuzzy_confidence("ROMA", "ROMA") == 1.0


def test_calculate_fuzzy_confidence_similar(service):
    """Test confidence for similar strings."""
    confidence = service.calculate_fuzzy_confidence("ROMA", "ROM")  # Missing one char
    assert 0.6 < confidence < 1.0


def test_calculate_fuzzy_confidence_different(service):
    """Test confidence for different strings."""
    confidence = service.calculate_fuzzy_confidence("ROMA", "MILANO")
    assert confidence < 0.5


# ============================================================
# Test: get_zone_by_comune - EXACT MATCH
# ============================================================

def test_get_zone_by_comune_exact_match(service_with_data):
    """Test exact comune match returns correct data."""
    result = service_with_data.get_zone_by_comune("Roma")

    assert result["comune"] == "ROMA"
    assert result["provincia"] == "RM"
    assert result["regione"] == "LAZIO"
    assert result["zona_sismica"] == 3
    assert result["accelerazione_ag"] == 0.15
    assert result["risk_level"] == "Media"
    assert result["source"] == "database_match"
    assert result["confidence"] == 1.0
    assert "normativa" in result
    assert "description" in result


def test_get_zone_by_comune_exact_match_with_provincia(service_with_data):
    """Test exact match with provincia verification."""
    result = service_with_data.get_zone_by_comune("Roma", provincia="RM")

    assert result["comune"] == "ROMA"
    assert result["provincia"] == "RM"
    assert result["confidence"] == 1.0


def test_get_zone_by_comune_exact_match_wrong_provincia(service_with_data):
    """Test exact match fails with wrong provincia."""
    with pytest.raises(ValueError) as exc_info:
        service_with_data.get_zone_by_comune("Roma", provincia="MI")

    assert "comune_provincia_mismatch" in str(exc_info.value)


# ============================================================
# Test: get_zone_by_comune - FUZZY MATCH
# ============================================================

def test_get_zone_by_comune_fuzzy_match(service_with_data):
    """Test fuzzy matching finds similar comune."""
    # "RОМА" with typo should match "ROMA"
    result = service_with_data.get_zone_by_comune("Rma")  # Missing 'o'

    assert result["comune"] == "ROMA"
    assert result["source"] == "fuzzy_match"
    assert 0.0 < result["confidence"] < 1.0
    assert "note" in result


def test_get_zone_by_comune_fuzzy_match_with_provincia_filter(service_with_data):
    """Test fuzzy match filters by provincia."""
    # Add another comune for better test
    service_with_data.db_data["comuni"]["ROMANO"] = {
        "provincia": "BG",
        "regione": "LOMBARDIA",
        "zona_sismica": 4,
        "accelerazione_ag": 0.05,
        "risk_level": "Bassa"
    }

    result = service_with_data.get_zone_by_comune("Rma", provincia="RM")

    assert result["comune"] == "ROMA"
    assert result["provincia"] == "RM"


def test_get_zone_by_comune_fuzzy_no_match_in_provincia(service_with_data):
    """Test fuzzy match fails when no matches in specified provincia."""
    with pytest.raises(ValueError) as exc_info:
        service_with_data.get_zone_by_comune("Rma", provincia="TO")

    assert "no_match_in_provincia" in str(exc_info.value)


# ============================================================
# Test: get_zone_by_comune - PROVINCIA ESTIMATION
# ============================================================

def test_get_zone_by_comune_provincia_estimation(service_with_data):
    """Test provincia-based estimation when no fuzzy matches."""
    # Add more comuni in RM provincia for estimation
    service_with_data.db_data["comuni"]["FIUMICINO"] = {
        "provincia": "RM",
        "regione": "LAZIO",
        "zona_sismica": 3,
        "accelerazione_ag": 0.15,
        "risk_level": "Media"
    }

    result = service_with_data.get_zone_by_comune("NonExistingComune", provincia="RM")

    assert result["comune"] == "NONEXISTINGCOMUNE"
    assert result["provincia"] == "RM"
    assert result["zona_sismica"] == 3  # Most common in RM
    assert result["source"] == "provincia_estimation"
    assert result["confidence"] == 0.5
    assert "stima" in result["note"].lower()


# ============================================================
# Test: get_zone_by_comune - NOT FOUND
# ============================================================

def test_get_zone_by_comune_not_found_no_provincia(service_with_data):
    """Test ValueError when comune not found and no provincia provided."""
    with pytest.raises(ValueError) as exc_info:
        service_with_data.get_zone_by_comune("Xyz")

    assert "comune_not_found" in str(exc_info.value)


def test_get_zone_by_comune_not_found_with_suggestions(service_with_data):
    """Test error includes suggestions when available."""
    with pytest.raises(ValueError) as exc_info:
        service_with_data.get_zone_by_comune("XYZ999")  # No possible match

    error_msg = str(exc_info.value)
    assert "comune_not_found" in error_msg
    # Should have no fuzzy matches for completely different string


# ============================================================
# Test: get_zone_from_db
# ============================================================

def test_get_zone_from_db_success(service):
    """Test database query returns correct data."""
    # Mock database session and result
    mock_result = Mock()
    mock_result.comune = "ROMA"
    mock_result.provincia = "RM"
    mock_result.regione = "LAZIO"
    mock_result.zona_sismica = 3
    mock_result.accelerazione_ag = 0.15
    mock_result.risk_level = "Media"

    mock_session = Mock()
    mock_query = mock_session.query.return_value
    mock_query.filter.return_value.filter.return_value.first.return_value = mock_result
    mock_query.filter.return_value.first.return_value = mock_result

    result = service.get_zone_from_db("Roma", db_session=mock_session)

    assert result["comune"] == "ROMA"
    assert result["provincia"] == "RM"
    assert result["zona_sismica"] == 3
    assert result["source"] == "database_match"
    assert result["confidence"] == 1.0


def test_get_zone_from_db_with_provincia(service):
    """Test database query with provincia filter."""
    mock_result = Mock()
    mock_result.comune = "ROMA"
    mock_result.provincia = "RM"
    mock_result.regione = "LAZIO"
    mock_result.zona_sismica = 3
    mock_result.accelerazione_ag = 0.15
    mock_result.risk_level = "Media"

    mock_session = Mock()
    mock_query = mock_session.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.filter.return_value.first.return_value = mock_result

    result = service.get_zone_from_db("Roma", provincia="RM", db_session=mock_session)

    assert result["comune"] == "ROMA"
    assert result["provincia"] == "RM"


def test_get_zone_from_db_not_found(service):
    """Test ValueError when comune not found in database."""
    mock_session = Mock()
    mock_query = mock_session.query.return_value
    mock_query.filter.return_value.first.return_value = None

    with pytest.raises(ValueError) as exc_info:
        service.get_zone_from_db("NonExisting", db_session=mock_session)

    assert "comune_not_found" in str(exc_info.value)


def test_get_zone_from_db_no_session(service):
    """Test ValueError when db_session not provided."""
    with pytest.raises(ValueError) as exc_info:
        service.get_zone_from_db("Roma")

    assert "db_session is required" in str(exc_info.value)


# ============================================================
# Test: get_suggestions
# ============================================================

def test_get_suggestions_returns_similar_comuni(service_with_data):
    """Test suggestions returns similar comune names."""
    suggestions = service_with_data.get_suggestions("Rma", limit=3)

    assert len(suggestions) > 0
    assert all("comune" in s for s in suggestions)
    assert all("provincia" in s for s in suggestions)
    assert all("zona_sismica" in s for s in suggestions)


def test_get_suggestions_respects_limit(service_with_data):
    """Test suggestions respects limit parameter."""
    suggestions = service_with_data.get_suggestions("Rom", limit=1)

    assert len(suggestions) <= 1


def test_get_suggestions_handles_errors_gracefully(service):
    """Test suggestions returns empty list on error."""
    with patch.object(service, 'load_seismic_database', side_effect=Exception("DB Error")):
        suggestions = service.get_suggestions("Roma")

    assert suggestions == []


# ============================================================
# Test: Edge Cases
# ============================================================

def test_comune_with_special_characters(service_with_data):
    """Test handling of comuni with special characters."""
    service_with_data.db_data["comuni"]["L'AQUILA"] = SAMPLE_DB["comuni"]["L'AQUILA"]

    result = service_with_data.get_zone_by_comune("L'Aquila")

    assert result["comune"] == "L'AQUILA"
    assert result["confidence"] == 1.0


def test_case_insensitive_matching(service_with_data):
    """Test comune matching is case-insensitive."""
    result1 = service_with_data.get_zone_by_comune("ROMA")
    result2 = service_with_data.get_zone_by_comune("roma")
    result3 = service_with_data.get_zone_by_comune("RoMa")

    assert result1["comune"] == result2["comune"] == result3["comune"]


def test_whitespace_trimming(service_with_data):
    """Test whitespace is properly trimmed."""
    result = service_with_data.get_zone_by_comune("  Roma  ")

    assert result["comune"] == "ROMA"


def test_empty_comune_name(service_with_data):
    """Test handling of empty comune name."""
    with pytest.raises(ValueError):
        service_with_data.get_zone_by_comune("")
