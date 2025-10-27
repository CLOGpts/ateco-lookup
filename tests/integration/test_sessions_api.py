"""
Test Baseline per Sessions and API Endpoints
=============================================

SCOPO: Catturare il comportamento ATTUALE degli endpoint sessions/API
PRIMA di fare refactoring del backend.

Test coverage:
- /api/events - Save risk assessment events
- /api/sessions/{user_id} - Get user session
- /api/sessions/{user_id}/summary - Get session summary
- /api/send-prereport-pdf - Send pre-report PDF
- /api/send-risk-report-pdf - Send risk report PDF
- /api/feedback - Submit feedback

---
DOCUMENTAZIONE PER NUOVE CHAT:
Questi test salvano i risultati degli endpoint API come baseline.
"""

import json
import pytest
from pathlib import Path


# ============================================================================
# TEST API EVENTS ENDPOINT
# ============================================================================

@pytest.mark.baseline
def test_api_events_post_valid(client, fixtures_dir):
    """
    Test /api/events - save risk events.

    NOTA: Endpoint potrebbe richiedere DB. Cattura comportamento attuale.
    """
    events_data = {
        "user_id": "test_user_123",
        "events": [
            {"event_code": "101", "selected": True},
            {"event_code": "201", "selected": False}
        ]
    }

    response = client.post("/api/events", json=events_data)

    # Accetta qualsiasi risposta valida
    assert response.status_code in [200, 201, 400, 500, 503], \
        f"Unexpected status {response.status_code}"

    data = response.json()

    baseline_file = fixtures_dir / "baseline_api_events_post.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ API events post - status {response.status_code}")


@pytest.mark.baseline
def test_api_events_post_empty(client, fixtures_dir):
    """Test /api/events con payload vuoto."""
    response = client.post("/api/events", json={})

    assert response.status_code in [200, 400, 422, 500], \
        f"Unexpected status {response.status_code}"

    data = response.json()

    baseline_file = fixtures_dir / "baseline_api_events_empty.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ API events empty - status {response.status_code}")


# ============================================================================
# TEST SESSIONS ENDPOINTS
# ============================================================================

@pytest.mark.baseline
def test_api_sessions_get(client, fixtures_dir):
    """Test /api/sessions/{user_id}."""
    user_id = "test_user_123"

    response = client.get(f"/api/sessions/{user_id}")

    assert response.status_code in [200, 404, 500], \
        f"Unexpected status {response.status_code}"

    data = response.json()

    baseline_file = fixtures_dir / "baseline_api_sessions_get.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ API sessions get - status {response.status_code}")


@pytest.mark.baseline
def test_api_sessions_summary(client, fixtures_dir):
    """Test /api/sessions/{user_id}/summary."""
    user_id = "test_user_123"

    response = client.get(f"/api/sessions/{user_id}/summary")

    assert response.status_code in [200, 404, 500], \
        f"Unexpected status {response.status_code}"

    data = response.json()

    baseline_file = fixtures_dir / "baseline_api_sessions_summary.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ API sessions summary - status {response.status_code}")


# ============================================================================
# TEST PDF REPORT ENDPOINTS
# ============================================================================

@pytest.mark.baseline
def test_api_send_prereport_pdf(client, fixtures_dir):
    """Test /api/send-prereport-pdf."""
    pdf_data = {
        "email": "test@example.com",
        "user_id": "test_user_123",
        "report_data": {"test": "data"}
    }

    response = client.post("/api/send-prereport-pdf", json=pdf_data)

    assert response.status_code in [200, 400, 500, 503], \
        f"Unexpected status {response.status_code}"

    data = response.json()

    baseline_file = fixtures_dir / "baseline_api_prereport_pdf.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ API pre-report PDF - status {response.status_code}")


@pytest.mark.baseline
def test_api_send_risk_report_pdf(client, fixtures_dir):
    """Test /api/send-risk-report-pdf."""
    pdf_data = {
        "email": "test@example.com",
        "user_id": "test_user_123",
        "assessment_data": {"test": "data"}
    }

    response = client.post("/api/send-risk-report-pdf", json=pdf_data)

    assert response.status_code in [200, 400, 500, 503], \
        f"Unexpected status {response.status_code}"

    data = response.json()

    baseline_file = fixtures_dir / "baseline_api_risk_report_pdf.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ API risk report PDF - status {response.status_code}")


# ============================================================================
# TEST FEEDBACK ENDPOINT
# ============================================================================

@pytest.mark.baseline
def test_api_feedback_post(client, fixtures_dir):
    """Test /api/feedback."""
    feedback_data = {
        "user_id": "test_user_123",
        "rating": 5,
        "comment": "Great tool!",
        "page": "risk-assessment"
    }

    response = client.post("/api/feedback", json=feedback_data)

    assert response.status_code in [200, 201, 400, 500], \
        f"Unexpected status {response.status_code}"

    data = response.json()

    baseline_file = fixtures_dir / "baseline_api_feedback.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ API feedback - status {response.status_code}")
