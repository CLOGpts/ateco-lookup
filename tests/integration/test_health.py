"""
Test Baseline per Health & System Endpoints
============================================

SCOPO: Catturare il comportamento ATTUALE degli endpoint di health check
PRIMA di fare refactoring del backend.

Test coverage:
- /health - Basic health check
- /health/database - Database connection health
- /team/hello - Multi-agent system info

---
DOCUMENTAZIONE PER NUOVE CHAT:
Questi test salvano i risultati degli health check come baseline.
Se dopo refactoring un test fallisce = hai cambiato la logica di health!
"""

import json
import pytest
from pathlib import Path


# ============================================================================
# TEST BASIC HEALTH ENDPOINT
# ============================================================================

@pytest.mark.baseline
def test_health_basic(client, fixtures_dir):
    """
    Test /health endpoint - basic health check.

    Verifica che:
    1. L'endpoint risponda con 200 OK
    2. Contenga i campi: status, version, cache_enabled
    3. status sia "ok"
    4. Salva baseline per confronti futuri
    """
    # Chiamata endpoint
    response = client.get("/health")

    # Verifica risposta
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    data = response.json()

    # Verifica struttura risposta
    assert "status" in data, "Response must contain 'status' field"
    assert "version" in data, "Response must contain 'version' field"
    assert "cache_enabled" in data, "Response must contain 'cache_enabled' field"

    # Verifica valori
    assert data["status"] == "ok", f"Expected status 'ok', got '{data['status']}'"
    assert isinstance(data["cache_enabled"], bool), "cache_enabled must be boolean"

    # Salva baseline
    baseline_file = fixtures_dir / "baseline_health_basic.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Health check passed - baseline saved to {baseline_file.name}")


# ============================================================================
# TEST DATABASE HEALTH ENDPOINT
# ============================================================================

@pytest.mark.baseline
def test_health_database_response_structure(client, fixtures_dir):
    """
    Test /health/database endpoint - database health check.

    Verifica che:
    1. L'endpoint risponda (status code 200)
    2. Contenga il campo 'status' (ok/error/warning)
    3. Salva baseline indipendentemente dallo stato del DB

    NOTA: Il database potrebbe non essere configurato in test,
    quindi non assertiamo che status sia "ok". Ci interessa
    solo catturare il comportamento ATTUALE.
    """
    # Chiamata endpoint
    response = client.get("/health/database")

    # Verifica risposta
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    data = response.json()

    # Verifica campo obbligatorio
    assert "status" in data, "Response must contain 'status' field"

    # Status può essere: ok, error, warning (tutti validi per baseline)
    valid_statuses = ["ok", "error", "warning"]
    assert data["status"] in valid_statuses, \
        f"status must be one of {valid_statuses}, got '{data['status']}'"

    # Salva baseline
    baseline_file = fixtures_dir / "baseline_health_database.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Database health check passed - status: {data['status']} - baseline saved to {baseline_file.name}")


@pytest.mark.baseline
@pytest.mark.skipif(True, reason="Database health detailed test - requires DB setup")
def test_health_database_with_db_connection(client, fixtures_dir):
    """
    Test /health/database con database effettivamente configurato.

    SKIPPED by default perché richiede setup database.

    Per abilitare: rimuovi @pytest.mark.skipif e configura PostgreSQL.

    Verifica che:
    1. status sia "ok"
    2. Contenga info su database e pool di connessioni
    """
    response = client.get("/health/database")
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "ok"
    assert data["database"] == "postgresql"
    assert data["connection"] == "active"
    assert "pool" in data


# ============================================================================
# TEST TEAM HELLO ENDPOINT (Multi-agent)
# ============================================================================

@pytest.mark.baseline
def test_team_hello_multi_agent(client, fixtures_dir):
    """
    Test /team/hello endpoint - multi-agent system info.

    Verifica che:
    1. L'endpoint risponda con 200 OK
    2. Contenga info agent: agent, message, capabilities, timestamp, status
    3. capabilities sia una lista non vuota
    4. endpoints_available sia una lista
    5. Salva baseline per confronti futuri
    """
    # Chiamata endpoint
    response = client.get("/team/hello")

    # Verifica risposta
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    data = response.json()

    # Verifica campi obbligatori
    required_fields = ["agent", "message", "capabilities", "timestamp", "status", "endpoints_available"]
    for field in required_fields:
        assert field in data, f"Response must contain '{field}' field"

    # Verifica tipi
    assert isinstance(data["capabilities"], list), "capabilities must be a list"
    assert len(data["capabilities"]) > 0, "capabilities list must not be empty"
    assert isinstance(data["endpoints_available"], list), "endpoints_available must be a list"

    # Verifica status operativo
    assert data["status"] == "operational", f"Expected status 'operational', got '{data['status']}'"

    # Verifica che timestamp sia in formato ISO
    assert "T" in data["timestamp"], "timestamp should be in ISO format (contains 'T')"

    # Salva baseline (NOTA: timestamp cambia ogni volta, ma va bene per baseline)
    baseline_file = fixtures_dir / "baseline_team_hello.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Team hello passed - agent: {data['agent']} - baseline saved to {baseline_file.name}")


# ============================================================================
# TEST CAPABILITIES & DOCUMENTATION
# ============================================================================

@pytest.mark.baseline
def test_team_hello_capabilities_coverage(client):
    """
    Test che verifica che /team/hello riporti capabilities reali.

    Verifica che:
    1. La lista capabilities non sia vuota
    2. Includa almeno alcune capabilities note (ATECO, Risk API)
    """
    response = client.get("/team/hello")
    data = response.json()

    capabilities = data.get("capabilities", [])

    # Verifica capabilities note
    expected_capabilities = ["ATECO", "Risk API"]
    for capability in expected_capabilities:
        assert capability in capabilities, \
            f"Expected capability '{capability}' in {capabilities}"

    print(f"✅ Capabilities verified: {capabilities}")


@pytest.mark.baseline
def test_team_hello_endpoints_list(client):
    """
    Test che verifica che /team/hello riporti endpoint disponibili.

    Verifica che:
    1. La lista endpoints_available non sia vuota
    2. Includa almeno alcuni endpoint noti
    """
    response = client.get("/team/hello")
    data = response.json()

    endpoints = data.get("endpoints_available", [])

    # Verifica che ci siano endpoint
    assert len(endpoints) > 0, "endpoints_available must not be empty"

    # Verifica alcuni endpoint noti
    expected_endpoints = ["/lookup", "/autocomplete"]
    for endpoint in expected_endpoints:
        assert endpoint in endpoints, \
            f"Expected endpoint '{endpoint}' in available endpoints"

    print(f"✅ Endpoints list verified: {len(endpoints)} endpoints available")
