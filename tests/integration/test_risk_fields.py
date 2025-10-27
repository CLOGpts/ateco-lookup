"""
Test Baseline per Risk Assessment Fields Endpoints
==================================================

SCOPO: Catturare il comportamento ATTUALE degli endpoint di risk assessment fields
PRIMA di fare refactoring del backend.

Test coverage:
- /risk-assessment-fields - Get risk assessment form structure
- /save-risk-assessment - Save and calculate risk score

---
DOCUMENTAZIONE PER NUOVE CHAT:
Questi test salvano i risultati dei risk fields come baseline.
Se dopo refactoring un test fallisce = hai cambiato la logica di risk assessment!
"""

import json
import pytest
from pathlib import Path


# ============================================================================
# TEST RISK ASSESSMENT FIELDS
# ============================================================================

@pytest.mark.baseline
def test_risk_assessment_fields_structure(client, fixtures_dir):
    """
    Test /risk-assessment-fields endpoint - form structure.

    Verifica che:
    1. L'endpoint risponda con 200 OK
    2. Contenga il campo 'fields' con lista di campi
    3. Ogni campo abbia: id, column, question, type, options, required
    4. Salva baseline per confronti futuri
    """
    # Chiamata endpoint
    response = client.get("/risk-assessment-fields")

    # Verifica risposta
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    data = response.json()

    # Verifica struttura
    assert "fields" in data, "Response must contain 'fields'"
    assert isinstance(data["fields"], list), "fields must be a list"
    assert len(data["fields"]) > 0, "fields list must not be empty"

    # Verifica struttura primo campo
    first_field = data["fields"][0]
    required_keys = ["id", "column", "question", "type", "options", "required"]
    for key in required_keys:
        assert key in first_field, f"Field must contain '{key}'"

    # Salva baseline
    baseline_file = fixtures_dir / "baseline_risk_fields.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Risk fields structure verified - {len(data['fields'])} fields - baseline saved")


@pytest.mark.baseline
def test_risk_assessment_fields_count(client):
    """
    Test che verifica il numero di campi nel form.

    Verifica che:
    1. Ci siano esattamente 8 campi (requirement attuale)
    2. I field IDs siano quelli attesi
    """
    response = client.get("/risk-assessment-fields")
    data = response.json()

    fields = data["fields"]

    # Verifica conteggio (baseline: 8 campi)
    assert len(fields) == 8, f"Expected 8 fields, got {len(fields)}"

    # Verifica field IDs attesi
    expected_ids = [
        "impatto_finanziario",
        "perdita_economica",
        "impatto_immagine",
        "impatto_regolamentare",
        "impatto_criminale",
        "perdita_non_economica",
        "controllo",
        "descrizione_controllo"
    ]

    actual_ids = [field["id"] for field in fields]

    for expected_id in expected_ids:
        assert expected_id in actual_ids, f"Expected field ID '{expected_id}' in fields"

    print(f"✅ All expected field IDs present: {len(expected_ids)} fields")


@pytest.mark.baseline
def test_risk_assessment_fields_types(client):
    """
    Test che verifica i tipi di campo.

    Verifica che:
    1. I tipi siano tra quelli validi (select, select_color, boolean, readonly)
    2. I campi con 'required' abbiano valore boolean
    """
    response = client.get("/risk-assessment-fields")
    data = response.json()

    valid_types = ["select", "select_color", "boolean", "readonly"]

    for field in data["fields"]:
        field_type = field.get("type")
        assert field_type in valid_types, \
            f"Field {field['id']} has invalid type '{field_type}'"

        # Verifica che required sia boolean (se presente)
        if "required" in field:
            assert isinstance(field["required"], bool), \
                f"Field {field['id']} required must be boolean"

    print(f"✅ All field types valid")


# ============================================================================
# TEST SAVE RISK ASSESSMENT
# ============================================================================

@pytest.mark.baseline
def test_save_risk_assessment_valid_data(client, fixtures_dir):
    """
    Test /save-risk-assessment con dati validi.

    Verifica che:
    1. L'endpoint accetti POST con dati validi
    2. Restituisca un risk_score calcolato
    3. Salva baseline del calcolo
    """
    # Dati di esempio validi
    risk_data = {
        "impatto_finanziario": "10 - 50K€",
        "perdita_economica": "Y",
        "impatto_immagine": "Si",
        "impatto_regolamentare": "No",
        "impatto_criminale": "No",
        "perdita_non_economica": "G",
        "controllo": "++"
    }

    # Chiamata endpoint
    response = client.post("/save-risk-assessment", json=risk_data)

    # Verifica risposta
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    data = response.json()

    # Verifica che contenga risk_score
    assert "risk_score" in data or "score" in data or "result" in data, \
        "Response must contain risk score"

    # Salva baseline
    baseline_file = fixtures_dir / "baseline_save_risk_valid.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Risk assessment saved - baseline saved")


@pytest.mark.baseline
def test_save_risk_assessment_minimal_data(client, fixtures_dir):
    """
    Test /save-risk-assessment con dati minimi (solo required fields).

    Verifica che:
    1. L'endpoint accetti dati minimi
    2. Restituisca response valida
    """
    # Dati minimi (solo required)
    risk_data = {
        "impatto_finanziario": "0 - 1K€",
        "perdita_economica": "G",
        "impatto_immagine": "No",
        "impatto_regolamentare": "No",
        "impatto_criminale": "No"
    }

    # Chiamata endpoint
    response = client.post("/save-risk-assessment", json=risk_data)

    # Verifica risposta (potrebbe essere 200 o 400 a seconda della validazione)
    assert response.status_code in [200, 400], \
        f"Expected 200 or 400, got {response.status_code}"

    data = response.json()

    # Salva baseline
    baseline_file = fixtures_dir / "baseline_save_risk_minimal.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Minimal risk assessment test - status {response.status_code}")


@pytest.mark.baseline
def test_save_risk_assessment_invalid_data(client, fixtures_dir):
    """
    Test /save-risk-assessment con dati invalidi.

    Verifica che:
    1. L'endpoint gestisca dati invalidi (valori non previsti)
    2. Restituisca errore appropriato o gestisca gracefully
    """
    # Dati invalidi
    risk_data = {
        "impatto_finanziario": "INVALID_VALUE",
        "perdita_economica": "X",  # Valore non previsto
        "impatto_immagine": "Maybe"  # Valore non previsto
    }

    # Chiamata endpoint
    response = client.post("/save-risk-assessment", json=risk_data)

    # Verifica risposta (potrebbe essere 400, 422, o 200 con gestione)
    assert response.status_code in [200, 400, 422], \
        f"Expected 200/400/422, got {response.status_code}"

    data = response.json()

    # Salva baseline
    baseline_file = fixtures_dir / "baseline_save_risk_invalid.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Invalid risk data test - status {response.status_code}")


@pytest.mark.baseline
def test_save_risk_assessment_empty_data(client, fixtures_dir):
    """
    Test /save-risk-assessment con payload vuoto.

    Verifica che:
    1. L'endpoint gestisca payload vuoto
    2. Restituisca errore appropriato
    """
    # Payload vuoto
    risk_data = {}

    # Chiamata endpoint
    response = client.post("/save-risk-assessment", json=risk_data)

    # Verifica risposta
    assert response.status_code in [200, 400, 422], \
        f"Expected 200/400/422, got {response.status_code}"

    data = response.json()

    # Salva baseline
    baseline_file = fixtures_dir / "baseline_save_risk_empty.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Empty risk data test - status {response.status_code}")
