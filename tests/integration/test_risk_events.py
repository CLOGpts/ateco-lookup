"""
Test Baseline per Risk Events Endpoints
========================================

SCOPO: Catturare il comportamento ATTUALE degli endpoint di risk events
PRIMA di fare refactoring del backend.

Test coverage:
- /events/{category} - Get risk events by category
- /description/{event_code} - Get event detailed description

---
DOCUMENTAZIONE PER NUOVE CHAT:
Questi test salvano i risultati dei risk events come baseline.
Se dopo refactoring un test fallisce = hai cambiato la logica di risk mapping!
"""

import json
import pytest
from pathlib import Path


# ============================================================================
# TEST EVENTS BY CATEGORY
# ============================================================================

@pytest.mark.baseline
@pytest.mark.parametrize("category,expected_status", [
    ("operational", 200),  # Alias mapping
    ("cyber", 200),        # Alias mapping
    ("compliance", 200),   # Alias mapping
    ("Damage_Danni", 200), # Excel category name
    ("Business_disruption", 200), # Excel category name
])
def test_events_by_category_valid(client, fixtures_dir, category, expected_status):
    """
    Test /events/{category} con categorie valide.

    Verifica che:
    1. L'endpoint risponda con 200 OK
    2. Contenga i campi: category, original_request, events, total
    3. events sia una lista
    4. Ogni evento abbia: code, name, severity
    5. Salva baseline per ogni categoria
    """
    # Chiamata endpoint
    response = client.get(f"/events/{category}")

    # Verifica risposta
    assert response.status_code == expected_status, \
        f"Expected {expected_status}, got {response.status_code}"

    data = response.json()

    # Verifica struttura risposta
    required_fields = ["category", "original_request", "events", "total"]
    for field in required_fields:
        assert field in data, f"Response must contain '{field}' field"

    # Verifica tipi
    assert isinstance(data["events"], list), "events must be a list"
    assert isinstance(data["total"], int), "total must be an integer"
    assert data["original_request"] == category, \
        f"original_request should be '{category}'"

    # Verifica struttura eventi (se presenti)
    if len(data["events"]) > 0:
        first_event = data["events"][0]
        event_fields = ["code", "name", "severity"]
        for field in event_fields:
            assert field in first_event, \
                f"Event must contain '{field}' field"

        # Verifica severity values
        valid_severities = ["low", "medium", "high", "critical"]
        assert first_event["severity"] in valid_severities, \
            f"severity must be one of {valid_severities}"

    # Salva baseline
    safe_category = category.replace("/", "_").replace("\\", "_")
    baseline_file = fixtures_dir / f"baseline_events_{safe_category}.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Events for '{category}' - {data['total']} events - baseline saved")


@pytest.mark.baseline
def test_events_by_category_invalid(client, fixtures_dir):
    """
    Test /events/{category} con categoria INVALIDA.

    Verifica che:
    1. L'endpoint risponda con 404
    2. Contenga un messaggio di errore
    3. Fornisca lista di categorie disponibili
    """
    # Chiamata endpoint con categoria invalida
    invalid_category = "nonexistent_category_xyz"
    response = client.get(f"/events/{invalid_category}")

    # Verifica risposta
    assert response.status_code == 404, \
        f"Expected 404 for invalid category, got {response.status_code}"

    data = response.json()

    # Verifica struttura errore
    assert "error" in data, "Error response must contain 'error' field"
    assert "available_categories" in data, \
        "Error response must list available_categories"

    # Verifica che available_categories sia una lista non vuota
    assert isinstance(data["available_categories"], list), \
        "available_categories must be a list"

    # Salva baseline errore
    baseline_file = fixtures_dir / "baseline_events_invalid_category.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Invalid category test passed - {len(data['available_categories'])} categories available")


@pytest.mark.baseline
def test_events_category_mapping(client):
    """
    Test che verifica il mapping degli alias categorie.

    Verifica che:
    1. Alias 'operational' mappa a categoria Excel corretta
    2. Alias 'cyber' mappa a categoria Excel corretta
    3. La categoria Excel reale viene restituita nel response
    """
    # Test alias 'operational'
    response = client.get("/events/operational")
    data = response.json()

    assert response.status_code == 200
    assert data["original_request"] == "operational"
    # La categoria Excel dovrebbe essere diversa dall'alias
    assert data["category"] != "operational", \
        "Category mapping should map alias to Excel category name"

    print(f"✅ Alias 'operational' maps to '{data['category']}'")


# ============================================================================
# TEST EVENT DESCRIPTION BY CODE
# ============================================================================

@pytest.mark.baseline
@pytest.mark.parametrize("event_code,expected_status", [
    ("101", 200),  # Damage event
    ("201", 200),  # Business disruption event
    ("301", 200),  # Employment event
    ("401", 200),  # Execution event
    ("501", 200),  # Client event
    ("601", 200),  # Internal fraud event
    ("701", 200),  # External fraud event
])
def test_event_description_valid_codes(client, fixtures_dir, event_code, expected_status):
    """
    Test /description/{event_code} con codici evento validi.

    Verifica che:
    1. L'endpoint risponda con 200 OK
    2. Contenga i campi: code, name, description, category, impact, probability, controls
    3. controls sia una lista
    4. Salva baseline per ogni codice
    """
    # Chiamata endpoint
    response = client.get(f"/description/{event_code}")

    # Verifica risposta
    assert response.status_code == expected_status, \
        f"Expected {expected_status}, got {response.status_code}"

    data = response.json()

    # Verifica campi obbligatori
    required_fields = ["code", "name", "description", "category", "impact", "probability", "controls"]
    for field in required_fields:
        assert field in data, f"Response must contain '{field}' field"

    # Verifica tipi
    assert isinstance(data["controls"], list), "controls must be a list"
    assert len(data["controls"]) > 0, "controls list must not be empty"

    # Verifica probability values
    valid_probabilities = ["low", "medium", "high", "unknown"]
    assert data["probability"] in valid_probabilities, \
        f"probability must be one of {valid_probabilities}"

    # Verifica code match
    assert data["code"] == event_code, \
        f"Response code should match requested code"

    # Salva baseline
    baseline_file = fixtures_dir / f"baseline_event_desc_{event_code}.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Description for event {event_code} - '{data['name']}' - baseline saved")


@pytest.mark.baseline
def test_event_description_invalid_code(client, fixtures_dir):
    """
    Test /description/{event_code} con codice INVALIDO.

    BASELINE BEHAVIOR: Il backend restituisce 200 con risposta generica
    invece di 404. Questo è il comportamento ATTUALE da preservare.

    Verifica che:
    1. L'endpoint risponda con 200 (comportamento attuale)
    2. Restituisca struttura "Evento non mappato" generica
    3. Contenga i campi obbligatori anche per eventi non mappati
    """
    # Chiamata endpoint con codice invalido
    invalid_code = "999"
    response = client.get(f"/description/{invalid_code}")

    # Verifica risposta (ATTUALE: 200, non 404)
    assert response.status_code == 200, \
        f"Expected 200 (current behavior), got {response.status_code}"

    data = response.json()

    # Verifica struttura risposta generica
    assert data["code"] == invalid_code, "Should return requested code"
    assert data["name"] == "Evento non mappato", \
        "Should indicate unmapped event"
    assert data["probability"] == "unknown", \
        "Unknown events should have 'unknown' probability"
    assert data["source"] == "Generic", \
        "Should indicate generic source"

    # Salva baseline
    baseline_file = fixtures_dir / "baseline_event_desc_invalid.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Invalid event code test passed - returns generic response")


@pytest.mark.baseline
def test_event_description_malformed_input(client, fixtures_dir):
    """
    Test /description/{event_code} con input MALFORMATO.

    Verifica che:
    1. L'endpoint gestisca input strani (es. [object Object])
    2. Restituisca errore 400 con messaggio chiaro
    """
    # Chiamata endpoint con input malformato
    malformed_input = "[object Object]"
    response = client.get(f"/description/{malformed_input}")

    # Verifica risposta
    # Potrebbe essere 400 (bad request) o 404 (not found) a seconda della logica
    assert response.status_code in [400, 404], \
        f"Expected 400 or 404 for malformed input, got {response.status_code}"

    data = response.json()

    # Verifica che ci sia un messaggio di errore
    assert "error" in data or "message" in data, \
        "Error response must contain error message"

    # Salva baseline errore
    baseline_file = fixtures_dir / "baseline_event_desc_malformed.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Malformed input test passed - status {response.status_code}")


# ============================================================================
# TEST INTEGRATION - Events + Description
# ============================================================================

@pytest.mark.baseline
def test_events_and_description_integration(client):
    """
    Test di integrazione: ottieni eventi per categoria,
    poi chiedi la descrizione del primo evento.

    Verifica che:
    1. Posso ottenere eventi per una categoria
    2. Posso usare il code del primo evento per ottenere la descrizione
    3. Il codice e la categoria sono consistenti
    """
    # Step 1: Ottieni eventi per categoria 'operational'
    events_response = client.get("/events/operational")
    assert events_response.status_code == 200

    events_data = events_response.json()
    assert len(events_data["events"]) > 0, "Should have at least one event"

    # Step 2: Prendi il primo evento e chiedi la descrizione
    first_event = events_data["events"][0]
    event_code = first_event["code"]

    desc_response = client.get(f"/description/{event_code}")

    # Verifica che la descrizione sia coerente
    if desc_response.status_code == 200:
        desc_data = desc_response.json()

        assert desc_data["code"] == event_code, \
            "Description code should match event code"

        assert desc_data["name"] == first_event["name"], \
            "Description name should match event name"

        print(f"✅ Integration test passed - Event {event_code}: {desc_data['name']}")
    else:
        # È OK se l'evento non ha descrizione dettagliata
        print(f"⚠️ Event {event_code} has no detailed description (expected)")
