"""
Test Baseline per ATECO Lookup Endpoint
========================================

SCOPO: Catturare il comportamento ATTUALE di /lookup
PRIMA di fare refactoring del backend.

Test coverage:
- Lookup singoli codici ATECO (settori diversi)
- Ricerca con varianti (con/senza punti, trailing zeros)
- Ricerca prefix (partial match)
- Batch lookup (multiple codes)

---
DOCUMENTAZIONE PER NUOVE CHAT:
Questi test salvano i risultati ATECO lookup come baseline.
Se dopo refactoring un test fallisce = hai cambiato la logica di ricerca!
"""

import json
import pytest
from pathlib import Path


# ============================================================================
# TEST SINGOLI CODICI ATECO
# ============================================================================

@pytest.mark.baseline
@pytest.mark.parametrize("code,expected_found_min", [
    ("01.11.0", 1),      # Agricoltura - Coltivazione cereali
    ("47.19.1", 1),      # Commercio - Grandi magazzini
    ("62.01.0", 1),      # IT - Produzione software
    ("86.10.1", 1),      # Sanità - Ospedali
    ("01.11", 1),        # Match esatto (non prefix) - 1 result
])
def test_ateco_lookup_single_codes(client, fixtures_dir, code, expected_found_min):
    """
    Test lookup per codici ATECO singoli.

    Verifica che:
    1. L'endpoint risponda correttamente
    2. Trovi almeno N risultati
    3. I risultati abbiano i campi chiave
    4. Salva baseline per confronti futuri
    """
    # Chiamata endpoint
    response = client.get(f"/lookup?code={code}")

    # Verifica risposta
    assert response.status_code == 200, f"Lookup failed for {code}: {response.text}"
    result = response.json()

    # Verifica struttura risposta
    assert 'found' in result, f"Missing 'found' field for code {code}"
    assert 'items' in result, f"Missing 'items' field for code {code}"

    # Verifica numero risultati
    assert result['found'] >= expected_found_min, \
        f"Expected at least {expected_found_min} results for {code}, got {result['found']}"

    # Verifica campi nei risultati
    if result['items']:
        first_item = result['items'][0]
        required_fields = [
            'CODICE_ATECO_2022',
            'TITOLO_ATECO_2022',
            'CODICE_ATECO_2025_RAPPRESENTATIVO',
            'TITOLO_ATECO_2025_RAPPRESENTATIVO'
        ]
        for field in required_fields:
            assert field in first_item, f"Missing required field {field} in ATECO result"

    # Salva baseline
    baseline_filename = f"ateco_baseline_{code.replace('.', '_')}.json"
    baseline_file = fixtures_dir / baseline_filename
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n✅ ATECO {code}: found {result['found']} results")


# ============================================================================
# TEST PREFIX SEARCH
# ============================================================================

@pytest.mark.baseline
def test_ateco_lookup_prefix_search(client, fixtures_dir):
    """
    Test ricerca con prefix (partial match).

    Esempio: cercare "01.11" con prefix=true deve trovare tutti i codici che iniziano con 01.11
    (01.11.0, 01.11.1, 01.11.10, 01.11.20, ecc.)
    """
    code = "01.11"

    # Chiamata con prefix=true
    response = client.get(f"/lookup?code={code}&prefix=true")

    assert response.status_code == 200
    result = response.json()

    # Verifica che trovi almeno 1 risultato (backend attuale trova match esatto + varianti)
    assert result['found'] >= 1, f"Prefix search for {code} should find at least 1 result"

    # Verifica che tutti i risultati inizino effettivamente con il prefix
    for item in result['items']:
        ateco_code = item.get('CODICE_ATECO_2022', '')
        # Normalizza codice (rimuovi punti per confronto)
        normalized_code = ateco_code.replace('.', '').replace(' ', '')
        normalized_prefix = code.replace('.', '').replace(' ', '')

        assert normalized_code.startswith(normalized_prefix), \
            f"Result {ateco_code} doesn't start with prefix {code}"

    # Salva baseline
    baseline_file = fixtures_dir / "ateco_baseline_prefix_01_11.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n✅ ATECO prefix {code}: found {result['found']} matching codes")


# ============================================================================
# TEST BATCH LOOKUP
# ============================================================================

@pytest.mark.baseline
def test_ateco_batch_lookup(client, fixtures_dir):
    """
    Test batch lookup (ricerca multipla codici).

    Invia 3 codici ATECO in una singola richiesta e verifica
    che vengano processati tutti correttamente.
    """
    codes = ["01.11.0", "47.19.1", "62.01.0"]

    # Chiamata batch
    response = client.post("/batch", json={
        "codes": codes,
        "prefer": "2022"
    })

    assert response.status_code == 200
    result = response.json()

    # Verifica struttura risposta batch
    assert 'total_codes' in result
    assert 'results' in result
    assert result['total_codes'] == len(codes)

    # Verifica che tutti i codici abbiano risultati
    assert len(result['results']) == len(codes)

    for i, code_result in enumerate(result['results']):
        assert 'code' in code_result
        assert 'found' in code_result
        assert 'items' in code_result
        assert code_result['found'] >= 1, f"Batch: no results for code {codes[i]}"

    # Salva baseline
    baseline_file = fixtures_dir / "ateco_baseline_batch.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n✅ ATECO batch: processed {result['total_codes']} codes successfully")


# ============================================================================
# TEST AUTOCOMPLETE
# ============================================================================

@pytest.mark.baseline
def test_ateco_autocomplete(client, fixtures_dir):
    """
    Test autocomplete per suggerimenti ATECO.

    Dato un termine di ricerca parziale, verifica che l'endpoint
    ritorni suggerimenti relevanti.
    """
    query = "cereali"

    # Chiamata autocomplete (parametro "partial" non "q")
    response = client.get(f"/autocomplete?partial={query}&limit=10")

    assert response.status_code == 200
    result = response.json()

    # Verifica struttura (dict con count, partial, suggestions)
    assert isinstance(result, dict), "Autocomplete should return a dict"
    assert 'count' in result, "Autocomplete should have 'count' field"
    assert 'suggestions' in result, "Autocomplete should have 'suggestions' field"
    assert isinstance(result['suggestions'], list), "Suggestions should be a list"

    # Verifica suggerimenti (se presenti)
    if result['count'] > 0 and result['suggestions']:
        for suggestion in result['suggestions'][:3]:  # Check first 3
            assert 'code' in suggestion or 'CODICE_ATECO_2022' in suggestion
            assert 'title' in suggestion or 'TITOLO_ATECO_2022' in suggestion

    # Salva baseline
    baseline_file = fixtures_dir / f"ateco_baseline_autocomplete_{query}.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n✅ ATECO autocomplete '{query}': found {len(result)} suggestions")


# ============================================================================
# INFORMAZIONI PER FUTURE CHAT
# ============================================================================
"""
COME ESEGUIRE:
--------------
cd /mnt/c/Users/speci/Desktop/Varie/Celerya_Cyber_Ateco
pytest tests/integration/test_ateco_lookup.py -v

COME INTERPRETARE FALLIMENTI:
------------------------------
Se un test fallisce DOPO refactoring:
1. Confronta il nuovo output con il baseline salvato in tests/fixtures/
2. Verifica se il cambio è intenzionale o un bug
3. Se intenzionale: aggiorna il test con i nuovi valori attesi
4. Se bug: fixa il codice refactorato

BASELINE FILES:
---------------
tests/fixtures/
├── ateco_baseline_01_11_0.json          → Agricoltura
├── ateco_baseline_47_19_1.json          → Commercio
├── ateco_baseline_62_01_0.json          → IT/Software
├── ateco_baseline_86_10_1.json          → Sanità
├── ateco_baseline_prefix_01_11.json     → Prefix search
├── ateco_baseline_batch.json            → Multi-code lookup
└── ateco_baseline_autocomplete_cereali.json  → Suggerimenti
"""
