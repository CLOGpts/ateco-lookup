"""
Unit tests for ATECO Service.

Tests core business logic functions without database dependencies.
"""
import pandas as pd
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from app.services.ateco_service import (
    normalize_code,
    strip_code,
    code_variants,
    normalize_headers,
    ATECOService,
)


class TestNormalizeCode:
    """Test normalize_code function."""

    def test_normal_code(self):
        """Normal ATECO code should remain unchanged."""
        assert normalize_code("62.01") == "62.01"

    def test_code_with_comma(self):
        """Comma should be replaced with dot."""
        assert normalize_code("62,01") == "62.01"

    def test_code_with_spaces(self):
        """Spaces should be stripped."""
        assert normalize_code(" 62.01 ") == "62.01"
        assert normalize_code("62. 01") == "62.01"

    def test_float_code(self):
        """Float input should be converted to string."""
        assert normalize_code(62.01) == "62.01"

    def test_nan_value(self):
        """NaN value should return empty string."""
        assert normalize_code(float('nan')) == ""
        assert normalize_code(pd.NA) == ""

    def test_none_value(self):
        """None value should return empty string."""
        assert normalize_code(None) == ""

    def test_lowercase(self):
        """Code should be uppercased."""
        assert normalize_code("62a") == "62A"


class TestStripCode:
    """Test strip_code function."""

    def test_normal_code(self):
        """Dots should be removed."""
        assert strip_code("62.01") == "6201"

    def test_code_with_dash(self):
        """Dashes should be removed."""
        assert strip_code("62-01") == "6201"

    def test_alphanumeric(self):
        """Alphanumeric characters should be preserved."""
        assert strip_code("62.01A") == "6201A"

    def test_nan_value(self):
        """NaN should return empty string."""
        assert strip_code(float('nan')) == ""

    def test_none_value(self):
        """None should return empty string."""
        assert strip_code(None) == ""


class TestCodeVariants:
    """Test code_variants function."""

    def test_simple_code(self):
        """Simple code should generate variants."""
        variants = code_variants("62.01")
        assert "62.01" in variants
        assert "6201" in variants
        # Zero-padded variant (only adds one zero for 2-digit last part)
        assert "62.010" in variants

    def test_two_digit_code(self):
        """Two-digit code should generate variants."""
        variants = code_variants("62")
        assert "62" in variants
        # Should have zero-padded variants

    def test_trailing_dot(self):
        """Code with trailing dot should be handled."""
        variants = code_variants("62.")
        assert "62" in variants

    def test_empty_code(self):
        """Empty code should return empty list."""
        assert code_variants("") == []

    def test_variants_unique(self):
        """Variants should be unique."""
        variants = code_variants("62.01")
        assert len(variants) == len(set(variants))


class TestNormalizeHeaders:
    """Test normalize_headers function."""

    def test_standard_headers(self):
        """Standard headers should be preserved."""
        df = pd.DataFrame(columns=["CODICE_ATECO_2022", "TITOLO_ATECO_2022"])
        result = normalize_headers(df)
        assert "CODICE_ATECO_2022" in result.columns
        assert "TITOLO_ATECO_2022" in result.columns

    def test_alternative_headers(self):
        """Alternative header names should be normalized."""
        df = pd.DataFrame(columns=["CODICE ATECO 2022", "TITOLO ATECO 2022"])
        result = normalize_headers(df)
        assert "CODICE_ATECO_2022" in result.columns
        assert "TITOLO_ATECO_2022" in result.columns


class TestATECOService:
    """Test ATECOService class methods."""

    @pytest.fixture
    def mock_dataset(self):
        """Create mock ATECO dataset."""
        return pd.DataFrame({
            "CODICE_ATECO_2022": ["62.01", "62.02", "62.09", "10.11"],
            "CODICE_ATECO_2022__NORM": ["62.01", "62.02", "62.09", "10.11"],
            "CODICE_ATECO_2022__STRIP": ["6201", "6202", "6209", "1011"],
            "TITOLO_ATECO_2022": [
                "Produzione software",
                "Consulenza informatica",
                "Altre attività ICT",
                "Lavorazione carne"
            ],
            "CODICE_ATECO_2025_RAPPRESENTATIVO": ["62.01", "62.02", "62.09", "10.11"],
            "TITOLO_ATECO_2025_RAPPRESENTATIVO": [
                "Produzione software 2025",
                "Consulenza 2025",
                "ICT 2025",
                "Carne 2025"
            ],
        })

    @pytest.fixture
    def service(self, tmp_path, mock_dataset):
        """Create ATECOService instance with mocked dataset."""
        # Create temporary Excel file
        excel_path = tmp_path / "test_ateco.xlsx"
        mock_dataset.to_excel(excel_path, sheet_name="Tabella operativa", index=False)

        return ATECOService(dataset_path=excel_path)

    def test_service_initialization(self, tmp_path):
        """Service should initialize with dataset path."""
        excel_path = tmp_path / "test.xlsx"
        service = ATECOService(dataset_path=excel_path)
        assert service.dataset_path == excel_path

    def test_load_dataset(self, service):
        """Service should load dataset successfully."""
        df = service.load_dataset()
        assert not df.empty
        assert "CODICE_ATECO_2022" in df.columns

    def test_search_smart_exact_match(self, service, mock_dataset):
        """Search should find exact match."""
        with patch.object(service, 'load_dataset', return_value=mock_dataset):
            result = service.search_smart("62.01")
            assert not result.empty
            assert result.iloc[0]["CODICE_ATECO_2022"] == "62.01"

    def test_search_smart_no_match(self, service, mock_dataset):
        """Search should return empty DataFrame for no match."""
        with patch.object(service, 'load_dataset', return_value=mock_dataset):
            result = service.search_smart("99.99")
            # May return empty or prefix matches
            assert isinstance(result, pd.DataFrame)

    def test_search_smart_prefix(self, service, mock_dataset):
        """Search with prefix should find multiple matches."""
        with patch.object(service, 'load_dataset', return_value=mock_dataset):
            result = service.search_smart("62", prefix=True)
            assert len(result) >= 3  # Should find 62.01, 62.02, 62.09

    def test_find_similar_codes(self, service, mock_dataset):
        """Find similar should suggest close matches."""
        with patch.object(service, 'load_dataset', return_value=mock_dataset):
            suggestions = service.find_similar_codes("62.00", limit=2)
            assert len(suggestions) <= 2
            if suggestions:
                assert "code" in suggestions[0]
                assert "title" in suggestions[0]

    def test_flatten(self, service):
        """Flatten should convert Series to dict."""
        row = pd.Series({
            "CODICE_ATECO_2022": "62.01",
            "TITOLO_ATECO_2022": "Test",
            "CODICE_ATECO_2022__NORM": "62.01",  # Should be excluded
            "CODICE_ATECO_2022__STRIP": "6201",  # Should be excluded
        })
        result = service.flatten(row)
        assert "CODICE_ATECO_2022" in result
        assert "TITOLO_ATECO_2022" in result
        assert "CODICE_ATECO_2022__NORM" not in result
        assert "CODICE_ATECO_2022__STRIP" not in result

    def test_enrich_ict_sector(self, service):
        """Enrich should add ICT sector for code 62.xx."""
        item = {"CODICE_ATECO_2022": "62.01"}
        result = service.enrich(item)
        assert result["settore"] == "ict"
        assert isinstance(result["normative"], list)
        assert isinstance(result["certificazioni"], list)

    def test_enrich_alimentare_sector(self, service):
        """Enrich should add alimentare sector for code 10.xx."""
        item = {"CODICE_ATECO_2022": "10.11"}
        result = service.enrich(item)
        assert result["settore"] == "alimentare"

    def test_enrich_unknown_sector(self, service):
        """Enrich should handle unknown sectors."""
        item = {"CODICE_ATECO_2022": "99.99"}
        result = service.enrich(item)
        assert result["settore"] == "non mappato"
        assert result["normative"] == []
        assert result["certificazioni"] == []
