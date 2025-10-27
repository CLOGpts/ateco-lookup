"""
Test Baseline per Risk Calculation Endpoint
============================================

SCOPO: Catturare il comportamento ATTUALE di /calculate-risk-assessment
PRIMA di fare refactoring del backend.

PERCHÉ: Questi test sono la "rete di sicurezza" che ci permette di
refactorare il monolite senza paura di rompere la logica di calcolo.

COME FUNZIONA:
1. Chiamiamo l'endpoint con input specifici
2. Salviamo i risultati in tests/fixtures/ (golden masters)
3. Verifichiamo che l'output sia coerente con la matrice risk

MATRICE RISK (4x4):
- Colonne (A-D): Rischio Inerente (min tra economic e non_economic)
  - A = Low (G+G), B = Medium (G+Y o Y+Y), C = High (Y+O o O+O), D = Critical (O+R o R+R)
- Righe (1-4): Control Level
  - 4 = ++ (Adeguato)
  - 3 = + (Sostanzialmente adeguato)
  - 2 = - (Parzialmente adeguato)
  - 1 = -- (Non adeguato)

LIVELLI RISK:
- Low (verde): A4, A3, B4
- Medium (giallo): A2, B3, C4
- High (arancione): A1, B2, C3, D4
- Critical (rosso): B1, C2, D3, C1, D2, D1

---
DOCUMENTAZIONE PER NUOVE CHAT:
Se stai leggendo questo file in futuro, ecco cosa devi sapere:
- Questi test NON modificano il backend, solo lo testano
- I file baseline in tests/fixtures/ sono i risultati "corretti" (golden masters)
- Se un test fallisce DOPO refactoring = hai rotto qualcosa!
- Esegui con: cd /path/to/backend && pytest tests/integration/test_risk_calculation.py -v
"""

import json
import pytest
from pathlib import Path


# ============================================================================
# TEST SINGOLO - Per capire come funziona
# ============================================================================

@pytest.mark.baseline
def test_risk_calculation_simple_case(client, fixtures_dir):
    """
    Test singolo più semplice: tutto verde (G+G) con controlli adeguati (++)

    Questo test verifica il caso "migliore":
    - Economic loss: Green (basso impatto economico)
    - Non-economic loss: Green (basso impatto non-economico)
    - Control level: ++ (controlli adeguati)

    Risultato atteso:
    - Matrix position: A4 (colonna A = rischio inerente basso, riga 4 = controlli ottimi)
    - Risk level: Low (verde)
    """
    # STEP 1: Prepara input (come farebbe il frontend)
    request_data = {
        'economic_loss': 'G',       # Green = basso
        'non_economic_loss': 'G',   # Green = basso
        'control_level': '++'        # Adeguato = riga 4
    }

    # STEP 2: Chiama l'endpoint (TestClient simula una chiamata HTTP)
    response = client.post("/calculate-risk-assessment", json=request_data)

    # STEP 3: Verifica che la chiamata sia riuscita
    assert response.status_code == 200, f"Endpoint failed: {response.text}"

    # STEP 4: Estrai i dati dalla risposta
    result = response.json()

    # STEP 5: Verifica campi essenziali presenti
    assert 'status' in result, "Missing 'status' field"
    assert 'matrix_position' in result, "Missing 'matrix_position' field"
    assert 'risk_level' in result, "Missing 'risk_level' field"
    assert 'risk_color' in result, "Missing 'risk_color' field"

    # STEP 6: Verifica valori attesi per questo caso specifico
    assert result['status'] == 'success', f"Unexpected status: {result['status']}"
    assert result['matrix_position'] == 'A4', f"Expected A4, got {result['matrix_position']}"
    assert result['risk_level'] == 'Low', f"Expected Low, got {result['risk_level']}"
    assert result['risk_color'] == 'green', f"Expected green, got {result['risk_color']}"

    # STEP 7: Salva baseline (golden master) per confronti futuri
    baseline_file = fixtures_dir / "risk_baseline_G_G_plusplus.json"
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Test passed! Baseline saved to: {baseline_file}")
    print(f"   Matrix Position: {result['matrix_position']}")
    print(f"   Risk Level: {result['risk_level']}")


# ============================================================================
# TEST PARAMETRIZZATI - Casi rappresentativi matrice risk
# ============================================================================

@pytest.mark.baseline
@pytest.mark.parametrize("economic,non_economic,control,expected_position,expected_level,expected_color", [
    # LOW RISK (verde) - 2 casi
    ("G", "G", "++", "A4", "Low", "green"),  # Già testato sopra, ma incluso per completezza
    ("G", "Y", "++", "B4", "Low", "green"),  # Economic basso, non-economic medio, controlli ottimi

    # MEDIUM RISK (giallo) - 3 casi
    ("G", "G", "-", "A2", "Medium", "yellow"),   # Rischio basso MA controlli parziali → Medium
    ("G", "Y", "+", "B3", "Medium", "yellow"),   # Rischio medio, controlli buoni
    ("Y", "O", "++", "C4", "Medium", "yellow"),  # Rischio medio-alto, ma controlli ottimi compensano

    # LOW RISK aggiuntivo (verde) - colonna A è sempre Low
    ("G", "G", "+", "A3", "Low", "green"),       # Rischio basso, controlli buoni → ancora Low

    # HIGH RISK (arancione) - 2 casi
    ("G", "Y", "-", "B2", "High", "orange"),     # Rischio medio, controlli parziali
    ("O", "R", "++", "D4", "High", "orange"),    # Rischio molto alto, controlli ottimi (non bastano)

    # CRITICAL RISK (rosso) - 2 casi
    ("O", "R", "-", "D2", "Critical", "red"),    # Rischio altissimo, controlli parziali
    ("R", "R", "--", "D1", "Critical", "red"),   # Worst case: rischio max, controlli assenti
])
def test_risk_calculation_matrix_cases(client, fixtures_dir, economic, non_economic, control,
                                       expected_position, expected_level, expected_color):
    """
    Test parametrizzato per 10 casi rappresentativi della matrice risk.

    Questo test copre tutti i 4 livelli di rischio (Low/Medium/High/Critical)
    con diverse combinazioni di:
    - Economic loss: G (Green), Y (Yellow), O (Orange), R (Red)
    - Non-economic loss: G, Y, O, R
    - Control level: ++ (Adeguato), + (Sostanzialmente), - (Parziale), -- (Assente)

    Per ogni caso:
    1. Chiama l'endpoint /calculate-risk-assessment
    2. Verifica che il risultato corrisponda alle attese
    3. Salva il baseline in un file JSON dedicato
    """
    # Prepara input
    request_data = {
        'economic_loss': economic,
        'non_economic_loss': non_economic,
        'control_level': control
    }

    # Chiama endpoint
    response = client.post("/calculate-risk-assessment", json=request_data)

    # Verifica risposta OK
    assert response.status_code == 200, f"Endpoint failed: {response.text}"
    result = response.json()

    # Verifica campi presenti
    assert result['status'] == 'success'
    assert 'matrix_position' in result
    assert 'risk_level' in result
    assert 'risk_color' in result

    # Verifica valori attesi
    assert result['matrix_position'] == expected_position, \
        f"Expected {expected_position}, got {result['matrix_position']}"
    assert result['risk_level'] == expected_level, \
        f"Expected {expected_level}, got {result['risk_level']}"
    assert result['risk_color'] == expected_color, \
        f"Expected {expected_color}, got {result['risk_color']}"

    # Salva baseline con nome descrittivo
    baseline_filename = f"risk_baseline_{economic}_{non_economic}_{control.replace('+', 'plus').replace('-', 'minus')}.json"
    baseline_file = fixtures_dir / baseline_filename
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Test passed: {economic}+{non_economic}+{control} → {expected_position} ({expected_level})")


# ============================================================================
# INFORMAZIONI PER CHI LEGGE QUESTO FILE IN FUTURO
# ============================================================================
"""
COME ESEGUIRE QUESTO TEST:
--------------------------
1. Vai nella directory del backend:
   cd /mnt/c/Users/speci/Desktop/Varie/Celerya_Cyber_Ateco

2. Esegui il test singolo:
   pytest tests/integration/test_risk_calculation.py::test_risk_calculation_simple_case -v

3. Esegui tutti i test del file:
   pytest tests/integration/test_risk_calculation.py -v

4. Esegui con output dettagliato:
   pytest tests/integration/test_risk_calculation.py -v -s


COME INTERPRETARE I RISULTATI:
-------------------------------
✅ PASSED (verde) = Test passato, comportamento corretto
❌ FAILED (rosso) = Test fallito, qualcosa è cambiato/rotto
⚠️  SKIPPED (giallo) = Test saltato (se configurato)


COSA FARE SE UN TEST FALLISCE DOPO REFACTORING:
------------------------------------------------
1. Guarda il messaggio di errore (es: "Expected A4, got B3")
2. Controlla quale codice hai modificato
3. Verifica se il cambiamento è intenzionale:
   - Se SÌ: Aggiorna il test con il nuovo comportamento atteso
   - Se NO: Hai introdotto un bug, devi fixare il codice

4. Confronta con il baseline salvato:
   cat tests/fixtures/risk_baseline_G_G_plusplus.json


DOVE TROVARE I BASELINE (golden masters):
------------------------------------------
tests/fixtures/
├── risk_baseline_G_G_plusplus.json    ← Questo test
├── risk_baseline_G_Y_plus.json        ← Test futuri
├── risk_baseline_R_R_minus.json       ← Test futuri
└── risk_matrix_baseline.json          ← Tutti i 36 casi insieme


PROSSIMI STEP:
--------------
Dopo questo test semplice, creeremo:
- 36 test per tutte le combinazioni della matrice
- Test parametrizzati (più compatti)
- Test per edge cases (input invalidi)
"""
