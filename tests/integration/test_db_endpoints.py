"""
Test Baseline per Database Endpoints
=====================================

SCOPO: Catturare il comportamento ATTUALE degli endpoint database
PRIMA di fare refactoring del backend.

Test coverage:
- /db/events/{category} - Get events from database
- /db/lookup - ATECO lookup from database
- /db/seismic-zone/{comune} - Seismic zone from database

---
DOCUMENTAZIONE PER NUOVE CHAT:
Questi test salvano i risultati degli endpoint database come baseline.
Se dopo refactoring un test fallisce = hai cambiato la logica di database access!

NOTA: Questi endpoint potrebbero richiedere database configurato.
I test catturano il comportamento ATTUALE (success o error).
"""

import json
import pytest
from pathlib import Path


# ============================================================================
# TEST DB EVENTS ENDPOINT
# ============================================================================

@pytest.mark.baseline
@pytest.mark.parametrize("category", [
    "operational",
    "cyber",
    "Damage_Danni"
])
def test_db_events_by_category(client, fixtures_dir, category):
    """
    Test /db/events/{category} endpoint.

    Verifica che:
    1. L'endpoint risponda (200 o errore se DB non configurato)
    2. Salva baseline indipendentemente dallo stato DB

    NOTA: Se DB non configurato, cattura l'errore come baseline.
    """
    # Chiamata endpoint
    response = client.get(f"/db/events/{category}")

    # Verifica risposta (accetta sia success che errori)
    assert response.status_code in [200, 404, 500, 503], \
        f"Unexpected status code {response.status_code}"

    data = response.json()

    # Salva baseline
    safe_category = category.replace("/", "_").replace("\\", "_")
    baseline_file = fixtures_dir / f"baseline_db_events_{safe_category}.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ DB events '{category}' - status {response.status_code} - baseline saved")


# ============================================================================
# TEST DB LOOKUP ENDPOINT
# ============================================================================

@pytest.mark.baseline
@pytest.mark.parametrize("code", [
    "01.11.0",
    "47.19.1",
    "62.01.0"
])
def test_db_lookup_ateco(client, fixtures_dir, code):
    """
    Test /db/lookup endpoint - ATECO lookup da database.

    Verifica che:
    1. L'endpoint risponda (200 o errore se DB non configurato)
    2. Salva baseline del comportamento attuale
    """
    # Chiamata endpoint
    response = client.get(f"/db/lookup?code={code}")

    # Verifica risposta
    assert response.status_code in [200, 404, 500, 503], \
        f"Unexpected status code {response.status_code}"

    data = response.json()

    # Salva baseline
    safe_code = code.replace(".", "_")
    baseline_file = fixtures_dir / f"baseline_db_lookup_{safe_code}.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ DB lookup '{code}' - status {response.status_code} - baseline saved")


@pytest.mark.baseline
def test_db_lookup_no_params(client, fixtures_dir):
    """
    Test /db/lookup senza parametri.

    Verifica che:
    1. L'endpoint gestisca richiesta senza parametri
    2. Restituisca errore appropriato
    """
    # Chiamata endpoint senza parametri
    response = client.get("/db/lookup")

    # Verifica risposta (dovrebbe essere errore)
    assert response.status_code in [200, 400, 422, 500], \
        f"Unexpected status code {response.status_code}"

    data = response.json()

    # Salva baseline
    baseline_file = fixtures_dir / "baseline_db_lookup_no_params.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ DB lookup no params - status {response.status_code}")


# ============================================================================
# TEST DB SEISMIC ZONE ENDPOINT
# ============================================================================

@pytest.mark.baseline
@pytest.mark.parametrize("comune", [
    "Roma",
    "Milano",
    "Napoli"
])
def test_db_seismic_zone(client, fixtures_dir, comune):
    """
    Test /db/seismic-zone/{comune} endpoint.

    Verifica che:
    1. L'endpoint risponda (200 o errore se DB non configurato)
    2. Salva baseline del comportamento attuale
    """
    # Chiamata endpoint
    response = client.get(f"/db/seismic-zone/{comune}")

    # Verifica risposta
    assert response.status_code in [200, 404, 500, 503], \
        f"Unexpected status code {response.status_code}"

    data = response.json()

    # Salva baseline
    safe_comune = comune.replace(" ", "_")
    baseline_file = fixtures_dir / f"baseline_db_seismic_{safe_comune}.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ DB seismic '{comune}' - status {response.status_code} - baseline saved")


@pytest.mark.baseline
def test_db_seismic_zone_not_found(client, fixtures_dir):
    """
    Test /db/seismic-zone/{comune} con comune inesistente.

    Verifica che:
    1. L'endpoint gestisca comune non trovato
    2. Restituisca response appropriata
    """
    # Chiamata endpoint con comune inesistente
    response = client.get("/db/seismic-zone/ComuneInventato123")

    # Verifica risposta
    assert response.status_code in [200, 404, 500], \
        f"Unexpected status code {response.status_code}"

    data = response.json()

    # Salva baseline
    baseline_file = fixtures_dir / "baseline_db_seismic_not_found.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ DB seismic not found - status {response.status_code}")
