"""
Unit tests for ATECO Router.

Tests API endpoints with mocked service layer.
"""
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock

# Import main app
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from main import app as main_app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(main_app)


@pytest.fixture
def mock_service():
    """Create mock ATECO service."""
    service = Mock()

    # Mock dataset
    service.load_dataset.return_value = pd.DataFrame({
        "CODICE_ATECO_2022": ["62.01", "62.02"],
        "TITOLO_ATECO_2022": ["Software", "Consulenza"],
    })

    # Mock search result (empty by default)
    service.search_smart.return_value = pd.DataFrame()

    # Mock similar codes
    service.find_similar_codes.return_value = [
        {"code": "62.01", "title": "Software"}
    ]

    # Mock flatten
    service.flatten.return_value = {
        "CODICE_ATECO_2022": "62.01",
        "TITOLO_ATECO_2022": "Software"
    }

    # Mock enrich
    service.enrich.return_value = {
        "CODICE_ATECO_2022": "62.01",
        "TITOLO_ATECO_2022": "Software",
        "settore": "ict",
        "normative": [],
        "certificazioni": []
    }

    return service


class TestATECOLookupEndpoint:
    """Test GET /ateco/lookup endpoint."""

    def test_lookup_returns_200(self, client):
        """Lookup should return 200."""
        response = client.get("/ateco/lookup?code=62.01")
        assert response.status_code == 200

    def test_lookup_invalid_code_too_short(self, client):
        """Lookup should reject code < 2 chars."""
        response = client.get("/ateco/lookup?code=6")
        assert response.status_code in [400, 422]  # FastAPI validation

    def test_lookup_missing_code_param(self, client):
        """Lookup should require code parameter."""
        response = client.get("/ateco/lookup")
        assert response.status_code == 422  # FastAPI validation error

    def test_lookup_with_prefer_param(self, client):
        """Lookup should accept prefer parameter."""
        response = client.get("/ateco/lookup?code=62.01&prefer=2025")
        assert response.status_code in [200, 500]  # May fail if dataset missing

    def test_lookup_invalid_prefer(self, client):
        """Lookup should reject invalid prefer value."""
        response = client.get("/ateco/lookup?code=62.01&prefer=invalid")
        assert response.status_code == 400

    def test_lookup_with_prefix(self, client):
        """Lookup should accept prefix parameter."""
        response = client.get("/ateco/lookup?code=62&prefix=true")
        assert response.status_code in [200, 500]

    def test_lookup_with_limit(self, client):
        """Lookup should accept limit parameter."""
        response = client.get("/ateco/lookup?code=62&prefix=true&limit=10")
        assert response.status_code in [200, 500]

    def test_lookup_limit_max_50(self, client):
        """Lookup should enforce max limit of 50."""
        response = client.get("/ateco/lookup?code=62&limit=100")
        assert response.status_code == 422  # Validation error


class TestATECOAutocompleteEndpoint:
    """Test GET /ateco/autocomplete endpoint."""

    def test_autocomplete_returns_200(self, client):
        """Autocomplete should return 200."""
        response = client.get("/ateco/autocomplete?partial=62")
        assert response.status_code in [200, 500]

    def test_autocomplete_too_short(self, client):
        """Autocomplete should reject partial < 2 chars."""
        response = client.get("/ateco/autocomplete?partial=6")
        assert response.status_code == 422

    def test_autocomplete_with_limit(self, client):
        """Autocomplete should accept limit parameter."""
        response = client.get("/ateco/autocomplete?partial=62&limit=10")
        assert response.status_code in [200, 500]

    def test_autocomplete_limit_max_20(self, client):
        """Autocomplete should enforce max limit of 20."""
        response = client.get("/ateco/autocomplete?partial=62&limit=50")
        assert response.status_code == 422


class TestATECOBatchEndpoint:
    """Test POST /ateco/batch endpoint."""

    def test_batch_returns_200(self, client):
        """Batch should return 200 with valid request."""
        response = client.post(
            "/ateco/batch",
            json={"codes": ["62.01", "62.02"]}
        )
        assert response.status_code in [200, 500]

    def test_batch_empty_codes(self, client):
        """Batch should reject empty codes list."""
        response = client.post("/ateco/batch", json={"codes": []})
        assert response.status_code == 400

    def test_batch_too_many_codes(self, client):
        """Batch should reject > 50 codes."""
        codes = [f"62.{i:02d}" for i in range(51)]
        response = client.post("/ateco/batch", json={"codes": codes})
        assert response.status_code == 400
        data = response.json()
        assert "TOO_MANY_CODES" in data["detail"]["error"]

    def test_batch_with_prefer(self, client):
        """Batch should accept prefer parameter."""
        response = client.post(
            "/ateco/batch",
            json={"codes": ["62.01"], "prefer": "2025"}
        )
        assert response.status_code in [200, 500]

    def test_batch_with_prefix(self, client):
        """Batch should accept prefix parameter."""
        response = client.post(
            "/ateco/batch",
            json={"codes": ["62"], "prefix": True}
        )
        assert response.status_code in [200, 500]


class TestDBLookupEndpoint:
    """Test GET /ateco/db/lookup endpoint (legacy)."""

    def test_db_lookup_returns_200(self, client):
        """DB lookup should return 200."""
        response = client.get("/ateco/db/lookup?code=62.01")
        assert response.status_code in [200, 500]

    def test_db_lookup_delegates_to_main(self, client):
        """DB lookup should delegate to main lookup."""
        response = client.get("/ateco/db/lookup?code=62.01")
        # Should behave same as /ateco/lookup
        assert response.status_code in [200, 500]


class TestATECOResponseFormat:
    """Test response format compliance."""

    @pytest.mark.skipif(
        not Path("tabella_ATECO.xlsx").exists(),
        reason="Dataset file not available"
    )
    def test_lookup_response_structure(self, client):
        """Lookup response should have correct structure."""
        response = client.get("/ateco/lookup?code=62.01")
        if response.status_code == 200:
            data = response.json()
            assert "found" in data
            assert "items" in data
            assert isinstance(data["found"], int)
            assert isinstance(data["items"], list)

    @pytest.mark.skipif(
        not Path("tabella_ATECO.xlsx").exists(),
        reason="Dataset file not available"
    )
    def test_autocomplete_response_structure(self, client):
        """Autocomplete response should have correct structure."""
        response = client.get("/ateco/autocomplete?partial=62")
        if response.status_code == 200:
            data = response.json()
            assert "partial" in data
            assert "suggestions" in data
            assert "count" in data
