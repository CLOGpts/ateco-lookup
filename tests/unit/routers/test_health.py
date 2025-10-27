"""
Unit Tests for Health Router
============================

Tests for app/routers/health.py endpoints.
Story 2.1 - Extract Health Check & Core Services
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI


@pytest.fixture
def app_with_health_router():
    """Create test app with health router"""
    from app.routers import health

    app = FastAPI()
    app.include_router(health.router)
    return app


@pytest.fixture
def client(app_with_health_router):
    """Create test client"""
    return TestClient(app_with_health_router)


class TestHealthEndpoint:
    """Tests for /health endpoint"""

    def test_health_returns_200(self, client):
        """Test health endpoint returns 200 OK"""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_correct_structure(self, client):
        """Test health endpoint returns expected JSON structure"""
        response = client.get("/health")
        data = response.json()

        assert "status" in data
        assert "version" in data
        assert "cache_enabled" in data

    def test_health_status_is_ok(self, client):
        """Test health status is 'ok'"""
        response = client.get("/health")
        data = response.json()

        assert data["status"] == "ok"

    def test_health_version_is_set(self, client):
        """Test version field is present"""
        response = client.get("/health")
        data = response.json()

        assert data["version"] == "2.0"

    def test_health_cache_enabled_is_boolean(self, client):
        """Test cache_enabled is boolean"""
        response = client.get("/health")
        data = response.json()

        assert isinstance(data["cache_enabled"], bool)


class TestHealthDatabaseEndpoint:
    """Tests for /health/database endpoint"""

    def test_database_health_returns_200_or_error(self, client):
        """Test database health endpoint responds (may be OK or error if DB not available)"""
        response = client.get("/health/database")
        assert response.status_code == 200

    def test_database_health_returns_status(self, client):
        """Test database health endpoint returns status field"""
        response = client.get("/health/database")
        data = response.json()

        assert "status" in data
        assert data["status"] in ["ok", "error"]

    def test_database_health_returns_database_type(self, client):
        """Test database health endpoint identifies database type"""
        response = client.get("/health/database")
        data = response.json()

        assert "database" in data
        assert data["database"] == "postgresql"

    def test_database_health_error_has_message(self, client):
        """Test database health error response has message"""
        response = client.get("/health/database")
        data = response.json()

        if data["status"] == "error":
            assert "message" in data

    def test_database_health_success_has_pool_info(self, client):
        """Test database health success response has pool info"""
        response = client.get("/health/database")
        data = response.json()

        # Only check pool if connection succeeded
        if data["status"] == "ok":
            assert "pool" in data
