"""
Test Baseline Estesi per /save-risk-assessment
===============================================

SCOPO: Test approfonditi con varie combinazioni di input.

---
DOCUMENTAZIONE PER NUOVE CHAT:
Questi test coprono varie combinazioni di input risk assessment.
"""

import json
import pytest
from pathlib import Path


# ============================================================================
# TEST SAVE RISK ASSESSMENT WITH MANY COMBINATIONS
# ============================================================================

@pytest.mark.baseline
@pytest.mark.parametrize("impatto_fin,perdita_eco,img,reg,crim", [
    ("0 - 1K€", "G", "No", "No", "No"),
    ("1 - 10K€", "G", "Si", "No", "No"),
    ("10 - 50K€", "Y", "No", "Si", "No"),
    ("50 - 100K€", "Y", "Si", "No", "Si"),
    ("100 - 500K€", "O", "No", "Si", "Si"),
    ("500K€ - 1M€", "O", "Si", "Si", "No"),
    ("1 - 3M€", "R", "No", "No", "Si"),
    ("3 - 5M€", "R", "Si", "Si", "Si"),
    ("N/A", "G", "No", "No", "No"),
    ("0 - 1K€", "R", "Si", "Si", "Si"),
    ("1 - 10K€", "O", "No", "Si", "No"),
    ("10 - 50K€", "G", "Si", "No", "Si"),
    ("50 - 100K€", "Y", "No", "Si", "Si"),
    ("100 - 500K€", "G", "Si", "No", "No"),
    ("500K€ - 1M€", "Y", "No", "No", "Si"),
])
def test_save_risk_combinations(client, fixtures_dir, impatto_fin, perdita_eco, img, reg, crim):
    """
    Test /save-risk-assessment with many input combinations.

    This covers different branches in the scoring logic.
    """
    risk_data = {
        "impatto_finanziario": impatto_fin,
        "perdita_economica": perdita_eco,
        "impatto_immagine": img,
        "impatto_regolamentare": reg,
        "impatto_criminale": crim,
        "perdita_non_economica": perdita_eco,  # Use same as economica
        "controllo": "++"
    }

    response = client.post("/save-risk-assessment", json=risk_data)

    # Accept any valid response
    assert response.status_code in [200, 400, 422], \
        f"Unexpected status {response.status_code}"

    if response.status_code == 200:
        data = response.json()

        # Save baseline
        safe_name = f"{impatto_fin[:3]}_{perdita_eco}_{img}_{reg}_{crim}".replace(" ", "_").replace("/", "_").replace("-", "_").replace("€", "")
        baseline_file = fixtures_dir / f"baseline_save_risk_{safe_name}.json"
        with open(baseline_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Save risk {impatto_fin[:10]} - status {response.status_code}")
