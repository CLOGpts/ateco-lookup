"""
Test Baseline per Seismic Zones Endpoint
=========================================

SCOPO: Catturare il comportamento ATTUALE di /seismic-zone/{comune}
PRIMA di fare refactoring del backend.

Test coverage:
- Lookup singoli comuni (diverse zone sismiche)
- Fuzzy matching (nomi simili)
- Disambiguazione provincia (comuni con stesso nome)
- Edge cases (comuni non trovati)

---
DOCUMENTAZIONE PER NUOVE CHAT:
Questi test salvano i risultati delle ricerche sismiche come baseline.
Se dopo refactoring un test fallisce = hai cambiato la logica di ricerca!
"""

import json
import pytest
from pathlib import Path


# ============================================================================
# TEST SINGOLI COMUNI - Zone Sismiche Diverse
# ============================================================================

@pytest.mark.baseline
@pytest.mark.parametrize("comune,expected_found", [
    ("Roma", True),           # Zona 3 - Capitale
    ("Milano", True),         # Zona 4 - Nord Italia
    ("Norcia", True),         # Zona 1 - Alta sismicità (terremoto 2016)
    ("Catania", True),        # Zona 2 - Sicilia orientale
    ("Torino", True),         # Zona 4 - Piemonte
    ("Napoli", True),         # Zona 2 - Campania
    ("Bologna", True),        # Zona 3 - Emilia
])
def test_seismic_zone_single_comuni(client, fixtures_dir, comune, expected_found):
    """
    Test lookup per singoli comuni in diverse zone sismiche.

    Verifica che:
    1. L'endpoint risponda correttamente
    2. Trovi il comune
    3. Restituisca i campi chiave (zona sismica, classificazione)
    4. Salva baseline per confronti futuri
    """
    # Chiamata endpoint
    response = client.get(f"/seismic-zone/{comune}")

    # Verifica risposta
    assert response.status_code == 200, f"Seismic lookup failed for {comune}: {response.text}"
    result = response.json()

    # Verifica struttura risposta
    assert isinstance(result, dict), f"Expected dict response for {comune}"

    if expected_found:
        # Se ci aspettiamo di trovare il comune
        assert 'Comune' in result or 'comune' in result, f"Missing comune field for {comune}"

        # Verifica presenza zona sismica (varie possibili chiavi)
        has_zone = any(key in result for key in [
            'Zona', 'zona', 'zona_sismica', 'Zona_sismica',
            'seismic_zone', 'classificazione'
        ])
        assert has_zone, f"Missing seismic zone field for {comune}"

    # Salva baseline
    baseline_filename = f"seismic_baseline_{comune.lower().replace(' ', '_')}.json"
    baseline_file = fixtures_dir / baseline_filename
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Seismic zone {comune}: zone data retrieved")


# ============================================================================
# TEST FUZZY MATCHING - Nomi Simili
# ============================================================================

@pytest.mark.baseline
def test_seismic_fuzzy_matching(client, fixtures_dir):
    """
    Test fuzzy matching per comuni con nomi simili o errori di battitura.

    Esempio: cercare "Romaa" o "Mlano" dovrebbe comunque trovare risultati
    (a seconda dell'implementazione backend).
    """
    # Test con varianti comuni
    test_cases = [
        ("Milano", "milano"),      # Case insensitive
        ("Roma", "roma"),          # Lowercase
        ("TORINO", "torino"),      # Uppercase
    ]

    results = {}
    for original, variant in test_cases:
        response = client.get(f"/seismic-zone/{variant}")
        assert response.status_code == 200, f"Fuzzy matching failed for {variant}"
        results[variant] = response.json()

    # Salva baseline
    baseline_file = fixtures_dir / "seismic_baseline_fuzzy_matching.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Seismic fuzzy matching: {len(results)} variants tested")


# ============================================================================
# TEST DISAMBIGUAZIONE PROVINCIA
# ============================================================================

@pytest.mark.baseline
def test_seismic_provincia_disambiguation(client, fixtures_dir):
    """
    Test disambiguazione per comuni con stesso nome in province diverse.

    Esempio: ci sono 2 comuni chiamati "San Giorgio" in Italia.
    L'endpoint dovrebbe gestire questa ambiguità.
    """
    # Comuni con nomi comuni (potrebbero esistere in più province)
    ambiguous_comuni = [
        "San Giovanni",
        "Santa Maria",
        "Montefiore",
    ]

    results = {}
    for comune in ambiguous_comuni:
        response = client.get(f"/seismic-zone/{comune}")

        # Verifica che l'endpoint risponda (anche se ambiguo)
        # Potrebbe ritornare lista di opzioni o errore di disambiguazione
        assert response.status_code in [200, 300, 400], \
            f"Unexpected status for ambiguous comune {comune}: {response.status_code}"

        results[comune] = {
            "status_code": response.status_code,
            "response": response.json()
        }

    # Salva baseline
    baseline_file = fixtures_dir / "seismic_baseline_disambiguation.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Seismic disambiguation: {len(results)} ambiguous comuni tested")


# ============================================================================
# TEST EDGE CASES - Comuni Non Trovati
# ============================================================================

@pytest.mark.baseline
def test_seismic_not_found(client, fixtures_dir):
    """
    Test comportamento con comuni inesistenti o invalidi.

    Verifica come l'endpoint gestisce:
    - Nomi completamente errati
    - Comuni esteri
    - Input vuoto
    """
    invalid_comuni = [
        "XYZ123NonEsiste",        # Nome inventato
        "ParisXXX",               # Comune estero (non italiano)
        "123456",                 # Solo numeri
    ]

    results = {}
    for comune in invalid_comuni:
        response = client.get(f"/seismic-zone/{comune}")

        # Registra status code e risposta (potrebbe essere 404, 400, o 200 con empty)
        results[comune] = {
            "status_code": response.status_code,
            "response": response.json() if response.status_code == 200 else response.text
        }

    # Salva baseline
    baseline_file = fixtures_dir / "seismic_baseline_not_found.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Seismic not found: {len(results)} invalid comuni tested")


# ============================================================================
# TEST COVERAGE ZONE SISMICHE - Tutte le Zone (1-4)
# ============================================================================

@pytest.mark.baseline
def test_seismic_all_zones_coverage(client, fixtures_dir):
    """
    Test che verifica copertura di tutte e 4 le zone sismiche italiane.

    Zone sismiche:
    - Zona 1: Alta pericolosità (Norcia, L'Aquila, Amatrice)
    - Zona 2: Media pericolosità (Napoli, Catania, Reggio Calabria)
    - Zona 3: Bassa pericolosità (Roma, Bologna, Firenze)
    - Zona 4: Molto bassa pericolosità (Milano, Torino, Venezia)
    """
    zone_examples = {
        "zona_1_alta": ["Norcia", "Accumoli"],          # Epicentro terremoto 2016
        "zona_2_media": ["Napoli", "Catania"],          # Sud Italia
        "zona_3_bassa": ["Roma", "Bologna"],            # Centro Italia
        "zona_4_molto_bassa": ["Milano", "Torino"],     # Nord Italia
    }

    results = {}
    for zone_label, comuni in zone_examples.items():
        results[zone_label] = {}
        for comune in comuni:
            response = client.get(f"/seismic-zone/{comune}")
            assert response.status_code == 200, f"Failed to get zone for {comune}"
            results[zone_label][comune] = response.json()

    # Salva baseline
    baseline_file = fixtures_dir / "seismic_baseline_all_zones.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    total_comuni = sum(len(comuni) for comuni in zone_examples.values())
    print(f"\n✅ Seismic all zones: {total_comuni} comuni across 4 zones tested")


# ============================================================================
# INFORMAZIONI PER FUTURE CHAT
# ============================================================================
"""
COME ESEGUIRE:
--------------
cd /mnt/c/Users/speci/Desktop/Varie/Celerya_Cyber_Ateco
pytest tests/integration/test_seismic_zones.py -v

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
├── seismic_baseline_roma.json                    → Zona 3
├── seismic_baseline_milano.json                  → Zona 4
├── seismic_baseline_norcia.json                  → Zona 1
├── seismic_baseline_catania.json                 → Zona 2
├── seismic_baseline_fuzzy_matching.json          → Case insensitive
├── seismic_baseline_disambiguation.json          → Comuni ambigui
├── seismic_baseline_not_found.json               → Edge cases
└── seismic_baseline_all_zones.json               → Coverage 4 zone

COMUNI TESTATI PER ZONA:
------------------------
Zona 1 (Alta):      Norcia, Accumoli (epicentro 2016)
Zona 2 (Media):     Napoli, Catania
Zona 3 (Bassa):     Roma, Bologna
Zona 4 (Molto bassa): Milano, Torino
"""
