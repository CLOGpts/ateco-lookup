"""
Test Baseline per Visura e Admin Endpoints
===========================================

SCOPO: Catturare il comportamento ATTUALE degli endpoint visura e admin
PRIMA di fare refactoring del backend.

Test coverage:
- /api/test-visura - Test Visura extraction
- /api/extract-visura - Extract data from Visura
- /admin/* - Admin endpoints (captured as baseline)

---
DOCUMENTAZIONE PER NUOVE CHAT:
Questi test salvano i risultati degli endpoint Visura/Admin come baseline.
Molti potrebbero fallire se servizi esterni non configurati - È NORMALE!
"""

import json
import pytest
from pathlib import Path


# ============================================================================
# TEST VISURA ENDPOINTS
# ============================================================================

@pytest.mark.baseline
def test_api_test_visura(client, fixtures_dir):
    """
    Test /api/test-visura endpoint.

    NOTA: Potrebbe richiedere API esterna. Cattura comportamento attuale.
    """
    response = client.get("/api/test-visura")

    assert response.status_code in [200, 400, 500, 503], \
        f"Unexpected status {response.status_code}"

    data = response.json()

    baseline_file = fixtures_dir / "baseline_visura_test.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Visura test - status {response.status_code}")


@pytest.mark.baseline
def test_api_extract_visura_no_data(client, fixtures_dir):
    """
    Test /api/extract-visura senza dati.
    """
    response = client.post("/api/extract-visura", json={})

    assert response.status_code in [200, 400, 422, 500], \
        f"Unexpected status {response.status_code}"

    data = response.json()

    baseline_file = fixtures_dir / "baseline_visura_extract_empty.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Visura extract empty - status {response.status_code}")


@pytest.mark.baseline
def test_api_extract_visura_with_text(client, fixtures_dir):
    """
    Test /api/extract-visura con testo di esempio.
    """
    visura_data = {
        "text": "Test visura content here",
        "mode": "strict"
    }

    response = client.post("/api/extract-visura", json=visura_data)

    assert response.status_code in [200, 400, 422, 500], \
        f"Unexpected status {response.status_code}"

    data = response.json()

    baseline_file = fixtures_dir / "baseline_visura_extract_text.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Visura extract text - status {response.status_code}")


# ============================================================================
# TEST ADMIN ENDPOINTS (Baseline capture)
# ============================================================================

@pytest.mark.baseline
def test_admin_setup_database(client, fixtures_dir):
    """
    Test /admin/setup-database endpoint.

    NOTA: Endpoint admin, potrebbe richiedere permessi. Cattura baseline.
    """
    response = client.get("/admin/setup-database")

    assert response.status_code in [200, 403, 500, 503], \
        f"Unexpected status {response.status_code}"

    data = response.json()

    baseline_file = fixtures_dir / "baseline_admin_setup_db.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Admin setup DB - status {response.status_code}")


@pytest.mark.baseline
def test_admin_check_tables(client, fixtures_dir):
    """
    Test /admin/check-tables endpoint.
    """
    response = client.get("/admin/check-tables")

    assert response.status_code in [200, 403, 500, 503], \
        f"Unexpected status {response.status_code}"

    data = response.json()

    baseline_file = fixtures_dir / "baseline_admin_check_tables.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Admin check tables - status {response.status_code}")


@pytest.mark.baseline
def test_admin_create_tables(client, fixtures_dir):
    """
    Test /admin/create-tables endpoint.
    """
    response = client.post("/admin/create-tables", json={})

    assert response.status_code in [200, 403, 500, 503], \
        f"Unexpected status {response.status_code}"

    data = response.json()

    baseline_file = fixtures_dir / "baseline_admin_create_tables.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Admin create tables - status {response.status_code}")


# ============================================================================
# TEST MIGRATION ENDPOINTS
# ============================================================================

@pytest.mark.baseline
def test_admin_migrate_risk_events(client, fixtures_dir):
    """Test /admin/migrate-risk-events endpoint."""
    response = client.post("/admin/migrate-risk-events", json={})

    assert response.status_code in [200, 403, 500, 503], \
        f"Unexpected status {response.status_code}"

    data = response.json()

    baseline_file = fixtures_dir / "baseline_admin_migrate_risk.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Admin migrate risk - status {response.status_code}")


@pytest.mark.baseline
def test_admin_migrate_ateco(client, fixtures_dir):
    """Test /admin/migrate-ateco endpoint."""
    response = client.post("/admin/migrate-ateco", json={})

    assert response.status_code in [200, 403, 500, 503], \
        f"Unexpected status {response.status_code}"

    data = response.json()

    baseline_file = fixtures_dir / "baseline_admin_migrate_ateco.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Admin migrate ATECO - status {response.status_code}")


@pytest.mark.baseline
def test_admin_migrate_seismic_zones(client, fixtures_dir):
    """Test /admin/migrate-seismic-zones endpoint."""
    response = client.post("/admin/migrate-seismic-zones", json={})

    assert response.status_code in [200, 403, 500, 503], \
        f"Unexpected status {response.status_code}"

    data = response.json()

    baseline_file = fixtures_dir / "baseline_admin_migrate_seismic.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Admin migrate seismic - status {response.status_code}")


@pytest.mark.baseline
def test_admin_create_feedback_table(client, fixtures_dir):
    """Test /admin/create-feedback-table endpoint."""
    response = client.post("/admin/create-feedback-table", json={})

    assert response.status_code in [200, 403, 500, 503], \
        f"Unexpected status {response.status_code}"

    data = response.json()

    baseline_file = fixtures_dir / "baseline_admin_create_feedback.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Admin create feedback table - status {response.status_code}")
