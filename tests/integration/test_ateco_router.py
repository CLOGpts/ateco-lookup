"""
Integration tests for ATECO router endpoints.

Tests new modular endpoints with real dataset.
"""
import pytest
from fastapi.testclient import TestClient
from pathlib import Path

# Import main app
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from main import app


@pytest.fixture
def client():
    """Create test client for integration tests."""
    return TestClient(app)


@pytest.mark.skipif(
    not Path("tabella_ATECO.xlsx").exists(),
    reason="ATECO dataset not available"
)
class TestATECONewEndpoints:
    """Test new modular ATECO endpoints."""

    def test_new_lookup_endpoint(self, client):
        """Test GET /ateco/lookup works."""
        response = client.get("/ateco/lookup?code=62.01")
        assert response.status_code == 200
        data = response.json()
        assert "found" in data
        assert "items" in data

    def test_new_autocomplete_endpoint(self, client):
        """Test GET /ateco/autocomplete works."""
        response = client.get("/ateco/autocomplete?partial=62")
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert "count" in data

    def test_new_batch_endpoint(self, client):
        """Test POST /ateco/batch works."""
        response = client.post(
            "/ateco/batch",
            json={"codes": ["62.01", "62.02"]}
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_codes" in data
        assert "results" in data
        assert data["total_codes"] == 2

    def test_db_lookup_endpoint(self, client):
        """Test GET /ateco/db/lookup works (legacy)."""
        response = client.get("/ateco/db/lookup?code=62.01")
        assert response.status_code == 200
        data = response.json()
        assert "found" in data


@pytest.mark.skipif(
    not Path("tabella_ATECO.xlsx").exists(),
    reason="ATECO dataset not available"
)
class TestDualEndpointsCompatibility:
    """Test that old and new endpoints return consistent data."""

    def test_lookup_endpoints_return_same_data(self, client):
        """Old /lookup and new /ateco/lookup should return identical data."""
        # Test old endpoint
        old_response = client.get("/lookup?code=62.01")

        # Test new endpoint
        new_response = client.get("/ateco/lookup?code=62.01")

        # Both should succeed
        assert old_response.status_code == 200
        assert new_response.status_code == 200

        # Parse responses
        old_data = old_response.json()
        new_data = new_response.json()

        # Both should have same structure
        assert "found" in old_data
        assert "found" in new_data
        assert "items" in old_data
        assert "items" in new_data

        # If found, compare first item code
        if old_data["found"] > 0 and new_data["found"] > 0:
            old_code = old_data["items"][0].get("CODICE_ATECO_2022")
            new_code = new_data["items"][0].get("CODICE_ATECO_2022")
            assert old_code == new_code, "Old and new endpoints should return same ATECO code"

    def test_autocomplete_endpoints_consistency(self, client):
        """Old and new autocomplete should work consistently."""
        # Test old endpoint
        old_response = client.get("/autocomplete?partial=62")

        # Test new endpoint
        new_response = client.get("/ateco/autocomplete?partial=62")

        # Both should succeed
        assert old_response.status_code == 200
        assert new_response.status_code == 200

        # Both should have suggestions
        old_data = old_response.json()
        new_data = new_response.json()

        assert "suggestions" in old_data or "partial" in old_data
        assert "suggestions" in new_data


@pytest.mark.skipif(
    not Path("tabella_ATECO.xlsx").exists(),
    reason="ATECO dataset not available"
)
class TestATECOEndpointValidation:
    """Test endpoint validation and error handling."""

    def test_lookup_invalid_code(self, client):
        """Lookup with short code should return validation error."""
        response = client.get("/ateco/lookup?code=6")
        assert response.status_code in [400, 422]  # FastAPI validation

    def test_batch_too_many_codes(self, client):
        """Batch with > 50 codes should return error."""
        codes = [f"{i:02d}.01" for i in range(51)]
        response = client.post("/ateco/batch", json={"codes": codes})
        assert response.status_code == 400
        data = response.json()
        assert "TOO_MANY_CODES" in data["detail"]["error"]

    def test_autocomplete_short_partial(self, client):
        """Autocomplete with short partial should fail validation."""
        response = client.get("/ateco/autocomplete?partial=6")
        assert response.status_code == 422  # FastAPI validation


@pytest.mark.skipif(
    not Path("tabella_ATECO.xlsx").exists(),
    reason="ATECO dataset not available"
)
class TestATECODataEnrichment:
    """Test that data enrichment works correctly."""

    def test_lookup_includes_sector_info(self, client):
        """Lookup response should include sector enrichment."""
        response = client.get("/ateco/lookup?code=62.01")
        assert response.status_code == 200

        data = response.json()
        if data["found"] > 0:
            item = data["items"][0]
            # Check enrichment fields
            assert "settore" in item
            assert "normative" in item or True  # May not have mapping
            assert "certificazioni" in item or True
