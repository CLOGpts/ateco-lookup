"""
Unit tests for Visura Router

Tests cover the API endpoints for Visura PDF extraction:
- GET /visura/test
- POST /visura/extract
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
import io

from app.routers import visura as visura_router


# ==================== Fixtures ====================

@pytest.fixture
def mock_visura_service():
    """Mock VisuraService for testing"""
    mock = MagicMock()
    return mock


@pytest.fixture
def app(mock_visura_service):
    """Create a test FastAPI app with visura router and mocked service"""
    app = FastAPI()
    # Setup mock dependencies
    visura_router._ateco_df = MagicMock()
    visura_router._search_smart_fn = MagicMock()
    visura_router._normalize_code_fn = MagicMock()
    app.include_router(visura_router.router)
    # Override dependency to use mock
    app.dependency_overrides[visura_router.get_visura_service] = lambda: mock_visura_service
    return app


@pytest.fixture
def client(app):
    """Create a test client"""
    return TestClient(app)


@pytest.fixture
def sample_pdf_file():
    """Create a sample PDF file for testing"""
    # Create a fake PDF in-memory
    pdf_content = b"%PDF-1.4 fake pdf content for testing"
    return ("test_visura.pdf", io.BytesIO(pdf_content), "application/pdf")


# ==================== Test: GET /visura/test ====================

def test_get_visura_test_success(client, mock_visura_service):
    """Test successful test endpoint call"""
    mock_visura_service.get_test_data.return_value = {
        "success": True,
        "message": "API working! VisuraExtractorPower available: True",
        "data": {
            "denominazione": "TEST CELERYA SRL",
            "partita_iva": "12345678901",
            "pec": "test@pec.it",
            "codici_ateco": [
                {"codice": "62.01", "descrizione": "Software production", "principale": True}
            ],
            "sede_legale": {
                "comune": "Torino",
                "provincia": "TO"
            },
            "confidence": 0.99
        }
    }

    response = client.get("/visura/test")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "message" in data
    assert "data" in data
    assert data["data"]["denominazione"] == "TEST CELERYA SRL"
    assert data["data"]["partita_iva"] == "12345678901"
    assert data["data"]["confidence"] == 0.99
    mock_visura_service.get_test_data.assert_called_once()


def test_get_visura_test_service_error(client, mock_visura_service):
    """Test test endpoint handles service errors"""
    mock_visura_service.get_test_data.side_effect = Exception("Service error")

    response = client.get("/visura/test")

    assert response.status_code == 500
    data = response.json()
    assert "error" in data
    assert data["error"] == "Internal server error"


# ==================== Test: POST /visura/extract ====================

def test_post_extract_visura_success(client, mock_visura_service, sample_pdf_file):
    """Test successful Visura extraction"""
    mock_visura_service.extract_from_pdf.return_value = {
        'success': True,
        'data': {
            'partita_iva': '12345678901',
            'codice_ateco': '64.99.1',
            'oggetto_sociale': 'Produzione software e consulenza informatica',
            'codici_ateco': [{
                'codice': '64.99.1',
                'descrizione': '',
                'principale': True
            }],
            'sede_legale': {
                'comune': 'Torino',
                'provincia': 'TO'
            },
            'denominazione': 'CELERYA SRL',
            'forma_giuridica': "SOCIETA' A RESPONSABILITA' LIMITATA",
            'confidence': {
                'score': 100,
                'details': {
                    'partita_iva': 'valid',
                    'ateco': 'valid',
                    'oggetto_sociale': 'valid',
                    'sede_legale': 'valid',
                    'denominazione': 'valid',
                    'forma_giuridica': 'valid'
                }
            }
        },
        'method': 'backend'
    }

    filename, file_obj, content_type = sample_pdf_file
    response = client.post(
        "/visura/extract",
        files={"file": (filename, file_obj, content_type)}
    )

    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True
    assert data['method'] == 'backend'
    assert data['data']['partita_iva'] == '12345678901'
    assert data['data']['codice_ateco'] == '64.99.1'
    assert data['data']['oggetto_sociale'] is not None
    assert data['data']['sede_legale']['comune'] == 'Torino'
    assert data['data']['denominazione'] == 'CELERYA SRL'
    assert data['data']['confidence']['score'] == 100
    mock_visura_service.extract_from_pdf.assert_called_once()


def test_post_extract_visura_partial_data(client, mock_visura_service, sample_pdf_file):
    """Test Visura extraction with partial data (only some fields)"""
    mock_visura_service.extract_from_pdf.return_value = {
        'success': True,
        'data': {
            'partita_iva': '11122233344',
            'codice_ateco': None,
            'oggetto_sociale': None,
            'codici_ateco': [],
            'confidence': {
                'score': 25,
                'details': {
                    'partita_iva': 'valid'
                }
            }
        },
        'method': 'backend'
    }

    filename, file_obj, content_type = sample_pdf_file
    response = client.post(
        "/visura/extract",
        files={"file": (filename, file_obj, content_type)}
    )

    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True
    assert data['data']['partita_iva'] == '11122233344'
    assert data['data']['codice_ateco'] is None
    assert data['data']['confidence']['score'] == 25


def test_post_extract_visura_no_data_found(client, mock_visura_service, sample_pdf_file):
    """Test Visura extraction when no data is found"""
    mock_visura_service.extract_from_pdf.return_value = {
        'success': True,
        'data': {
            'partita_iva': None,
            'codice_ateco': None,
            'oggetto_sociale': None,
            'codici_ateco': [],
            'confidence': {
                'score': 0,
                'details': {}
            }
        },
        'method': 'backend'
    }

    filename, file_obj, content_type = sample_pdf_file
    response = client.post(
        "/visura/extract",
        files={"file": (filename, file_obj, content_type)}
    )

    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True
    assert data['data']['partita_iva'] is None
    assert data['data']['codice_ateco'] is None
    assert data['data']['confidence']['score'] == 0


def test_post_extract_visura_empty_file(client, mock_visura_service):
    """Test Visura extraction with empty file"""
    # Create empty file
    empty_file = ("empty.pdf", io.BytesIO(b""), "application/pdf")
    filename, file_obj, content_type = empty_file

    response = client.post(
        "/visura/extract",
        files={"file": (filename, file_obj, content_type)}
    )

    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True
    assert data['data']['partita_iva'] is None
    assert data['data']['confidence']['score'] == 0
    # Should NOT call service for empty file
    mock_visura_service.extract_from_pdf.assert_not_called()


def test_post_extract_visura_service_exception(client, mock_visura_service, sample_pdf_file):
    """Test Visura extraction handles service exceptions"""
    mock_visura_service.extract_from_pdf.side_effect = Exception("Extraction failed")

    filename, file_obj, content_type = sample_pdf_file
    response = client.post(
        "/visura/extract",
        files={"file": (filename, file_obj, content_type)}
    )

    assert response.status_code == 500
    data = response.json()
    assert data['success'] is False
    assert "error" in data
    assert data["error"] == "Internal server error"
    assert data['data']['confidence']['score'] == 0


def test_post_extract_visura_no_file(client):
    """Test Visura extraction without file parameter"""
    # Missing 'file' parameter
    response = client.post("/visura/extract")

    # FastAPI will return 422 for missing required parameter
    assert response.status_code == 422


def test_post_extract_visura_invalid_file_type(client, mock_visura_service):
    """Test Visura extraction with non-PDF file (should still process)"""
    # Send a text file instead of PDF
    text_file = ("test.txt", io.BytesIO(b"This is not a PDF"), "text/plain")
    filename, file_obj, content_type = text_file

    mock_visura_service.extract_from_pdf.return_value = {
        'success': True,
        'data': {
            'partita_iva': None,
            'codice_ateco': None,
            'oggetto_sociale': None,
            'codici_ateco': [],
            'confidence': {
                'score': 0,
                'details': {}
            }
        },
        'method': 'backend'
    }

    response = client.post(
        "/visura/extract",
        files={"file": (filename, file_obj, content_type)}
    )

    # Should accept but likely extract nothing
    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True


# ==================== Test: set_dependencies ====================

def test_set_dependencies():
    """Test set_dependencies function"""
    import pandas as pd

    mock_df = pd.DataFrame({'test': [1, 2, 3]})
    mock_search = lambda x: x
    mock_normalize = lambda x: x.upper()

    visura_router.set_dependencies(
        ateco_df=mock_df,
        search_smart_fn=mock_search,
        normalize_code_fn=mock_normalize
    )

    assert visura_router._ateco_df is not None
    assert visura_router._search_smart_fn is not None
    assert visura_router._normalize_code_fn is not None
    assert len(visura_router._ateco_df) == 3


# ==================== Test: get_visura_service dependency ====================

def test_get_visura_service_dependency():
    """Test get_visura_service creates VisuraService with dependencies"""
    import pandas as pd

    # Setup dependencies
    mock_df = pd.DataFrame({'test': [1]})
    mock_search = lambda x: x
    mock_normalize = lambda x: x

    visura_router.set_dependencies(
        ateco_df=mock_df,
        search_smart_fn=mock_search,
        normalize_code_fn=mock_normalize
    )

    # Test that get_visura_service returns a VisuraService instance
    service = visura_router.get_visura_service()
    from app.services.visura_service import VisuraService
    assert isinstance(service, VisuraService)
    # Verify dependencies are set
    assert service.ateco_df is not None
    assert service.search_smart_fn is not None
    assert service.normalize_code_fn is not None


# ==================== Test: Integration - Full extraction flow ====================

def test_full_extraction_flow_integration(client, mock_visura_service, sample_pdf_file):
    """Test full extraction flow from upload to response"""
    # Simulate realistic extraction result with all fields
    mock_visura_service.extract_from_pdf.return_value = {
        'success': True,
        'data': {
            'partita_iva': '98765432101',
            'codice_ateco': '62.01.0',
            'oggetto_sociale': 'Produzione di software non connesso all\'edizione, consulenza informatica e gestione dati',
            'codici_ateco': [{
                'codice': '62.01.0',
                'descrizione': '',
                'principale': True
            }],
            'sede_legale': {
                'comune': 'Milano',
                'provincia': 'MI'
            },
            'denominazione': 'TECH SOLUTIONS SPA',
            'forma_giuridica': "SOCIETA' PER AZIONI",
            'confidence': {
                'score': 100,
                'details': {
                    'partita_iva': 'valid',
                    'ateco': 'valid',
                    'oggetto_sociale': 'valid',
                    'sede_legale': 'valid',
                    'denominazione': 'valid',
                    'forma_giuridica': 'valid'
                }
            }
        },
        'method': 'backend'
    }

    filename, file_obj, content_type = sample_pdf_file
    response = client.post(
        "/visura/extract",
        files={"file": (filename, file_obj, content_type)}
    )

    assert response.status_code == 200
    data = response.json()

    # Verify complete structure
    assert data['success'] is True
    assert data['method'] == 'backend'
    assert 'data' in data
    assert 'confidence' in data['data']

    # Verify all extracted fields
    extracted = data['data']
    assert extracted['partita_iva'] == '98765432101'
    assert extracted['codice_ateco'] == '62.01.0'
    assert 'software' in extracted['oggetto_sociale'].lower()
    assert extracted['sede_legale']['comune'] == 'Milano'
    assert extracted['sede_legale']['provincia'] == 'MI'
    assert extracted['denominazione'] == 'TECH SOLUTIONS SPA'
    assert 'AZIONI' in extracted['forma_giuridica']

    # Verify confidence
    assert extracted['confidence']['score'] == 100
    assert len(extracted['confidence']['details']) == 6
    assert all(v == 'valid' for v in extracted['confidence']['details'].values())

    # Verify codici_ateco array format
    assert len(extracted['codici_ateco']) == 1
    assert extracted['codici_ateco'][0]['codice'] == '62.01.0'
    assert extracted['codici_ateco'][0]['principale'] is True
