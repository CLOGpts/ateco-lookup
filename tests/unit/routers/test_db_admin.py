"""
Unit tests for DB Admin Router

Tests cover the API endpoints for database administration:
- GET /db-admin/setup-database
- GET /db-admin/check-tables
- POST /db-admin/create-tables
- POST /db-admin/migrate-risk-events
- POST /db-admin/migrate-ateco
- POST /db-admin/migrate-seismic-zones
- POST /db-admin/create-feedback-table
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
import pandas as pd

from app.routers import db_admin as db_admin_router


# ==================== Fixtures ====================

@pytest.fixture
def mock_db_admin_service():
    """Mock DBAdminService for testing"""
    return MagicMock()


@pytest.fixture
def app(mock_db_admin_service):
    """Create a test FastAPI app with db_admin router and mocked service"""
    app = FastAPI()
    # Setup mock dependencies
    db_admin_router._ateco_df = pd.DataFrame({'test': [1]})
    app.include_router(db_admin_router.router)
    # Override dependency
    app.dependency_overrides[db_admin_router.get_db_admin_service] = lambda: mock_db_admin_service
    return app


@pytest.fixture
def client(app):
    """Create a test client"""
    return TestClient(app)


# ==================== Test: GET /db-admin/setup-database ====================

def test_setup_database_success(client, mock_db_admin_service):
    """Test successful database setup"""
    mock_db_admin_service.setup_database.return_value = {
        "success": True,
        "message": "🎉 Setup completato con successo!",
        "tables_created": ["user_sessions", "session_events"],
        "steps": []
    }

    response = client.get("/db-admin/setup-database")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "tables_created" in data


def test_setup_database_connection_error(client, mock_db_admin_service):
    """Test setup-database handles connection errors"""
    mock_db_admin_service.setup_database.side_effect = ConnectionError("Cannot connect")

    response = client.get("/db-admin/setup-database")

    assert response.status_code == 500
    data = response.json()
    assert data["success"] is False
    assert "connection_error" in data["error"]


# ==================== Test: GET /db-admin/check-tables ====================

def test_check_tables_success(client, mock_db_admin_service):
    """Test successful table check"""
    mock_db_admin_service.check_tables_status.return_value = {
        "status": "ok",
        "total_tables": 8,
        "tables": {
            "risk_events": {
                "exists": True,
                "row_count": 191,
                "description": "191 eventi rischio"
            }
        },
        "missing_tables": []
    }

    response = client.get("/db-admin/check-tables")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "total_tables" in data


# ==================== Test: POST /db-admin/create-tables ====================

def test_create_tables_success(client, mock_db_admin_service):
    """Test successful table creation"""
    mock_db_admin_service.create_missing_tables.return_value = {
        "success": True,
        "message": "✅ Tabelle create con successo! (6 nuove)",
        "summary": {
            "before": 2,
            "after": 8,
            "created": 6
        },
        "steps": []
    }

    response = client.post("/db-admin/create-tables")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["summary"]["created"] == 6


# ==================== Test: POST /db-admin/migrate-risk-events ====================

def test_migrate_risk_events_success(client, mock_db_admin_service):
    """Test successful risk events migration"""
    mock_db_admin_service.migrate_risk_events.return_value = {
        "success": True,
        "message": "✅ Migrazione completata! (191 inseriti, 0 saltati)",
        "steps": []
    }

    response = client.post("/db-admin/migrate-risk-events")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


def test_migrate_risk_events_file_not_found(client, mock_db_admin_service):
    """Test migrate-risk-events handles file not found"""
    mock_db_admin_service.migrate_risk_events.side_effect = FileNotFoundError("File not found")

    response = client.post("/db-admin/migrate-risk-events")

    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert "file_not_found" in data["error"]


# ==================== Test: POST /db-admin/migrate-ateco ====================

def test_migrate_ateco_success(client, mock_db_admin_service):
    """Test successful ATECO migration"""
    mock_db_admin_service.migrate_ateco_codes.return_value = {
        "success": True,
        "message": "✅ Migrazione ATECO completata! (25123 inseriti, 0 saltati)",
        "steps": []
    }

    response = client.post("/db-admin/migrate-ateco")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


def test_migrate_ateco_dataframe_not_available(client, mock_db_admin_service):
    """Test migrate-ateco handles missing DataFrame"""
    db_admin_router._ateco_df = None

    response = client.post("/db-admin/migrate-ateco")

    assert response.status_code == 500
    data = response.json()
    assert data["success"] is False


# ==================== Test: POST /db-admin/migrate-seismic-zones ====================

def test_migrate_seismic_zones_success(client, mock_db_admin_service):
    """Test successful seismic zones migration"""
    mock_db_admin_service.migrate_seismic_zones.return_value = {
        "success": True,
        "message": "✅ Migrazione zone sismiche completata! (8102 inseriti, 0 saltati)",
        "steps": []
    }

    response = client.post("/db-admin/migrate-seismic-zones")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


# ==================== Test: POST /db-admin/create-feedback-table ====================

def test_create_feedback_table_success(client, mock_db_admin_service):
    """Test successful feedback table creation"""
    mock_db_admin_service.create_feedback_table.return_value = {
        "success": True,
        "message": "Tabella user_feedback creata con successo",
        "steps": ["✅ Tabella user_feedback creata"]
    }

    response = client.post("/db-admin/create-feedback-table")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


# ==================== Test: set_dependencies ====================

def test_set_dependencies():
    """Test set_dependencies function"""
    mock_df = pd.DataFrame({'test': [1, 2, 3]})

    db_admin_router.set_dependencies(ateco_df=mock_df)

    assert db_admin_router._ateco_df is not None
    assert len(db_admin_router._ateco_df) == 3
